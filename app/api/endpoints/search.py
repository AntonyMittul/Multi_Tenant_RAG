from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from app.api import deps
from app.models.tenant import Tenant
from app.services.retrieval import hybrid_search
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/query", response_model=List[Dict[str, Any]])
async def search_documents(
    query: str = Query(..., description="The search query"),
    top_k: int = Query(5, description="Number of results to return"),
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Perform a hybrid search (Dense + Sparse) with Cross-Encoder reranking
    on the tenant's ingested documents.
    """
    try:
        results = hybrid_search(query, current_tenant.id, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Search failed for tenant {current_tenant.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed.")


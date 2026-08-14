from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.api import deps
from app.models.tenant import Tenant
from app.services.evaluation import evaluate_faithfulness, evaluate_answer_relevance
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/run", response_model=Dict[str, float])
async def run_evaluation(
    question: str,
    answer: str,
    context: str,
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Run LLM-as-a-judge evaluation for a specific QA pair.
    (In a real production system, this would run asynchronously over a dataset 
    and log results to Langfuse or MLflow.)
    """
    try:
        faithfulness_score = evaluate_faithfulness(question, context, answer)
        relevance_score = evaluate_answer_relevance(question, answer)
        
        return {
            "faithfulness": faithfulness_score,
            "answer_relevance": relevance_score
        }
    except Exception as e:
        logger.error(f"Evaluation failed for tenant {current_tenant.id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Evaluation failed.")


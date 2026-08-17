from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.api import deps
from app.models.tenant import Tenant
from app.schemas.generation import GenerateRequest, GenerateResponse, SourceDocument
from app.services.retrieval import hybrid_search
from app.services.generation import generate_answer, generate_answer_stream
from app.services.cache import get_cached_response, set_cached_response
from app.services.guardrails import GuardrailManager
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=GenerateResponse)
async def generate_rag_response(
    request: GenerateRequest,
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Perform Retrieval-Augmented Generation.
    1. Check cache.
    2. Retrieve relevant documents.
    3. Generate answer using Gemini.
    4. Return Answer + Sources.
    """
    try:
        # 0. Input Guardrail
        is_valid, reason = GuardrailManager.verify_input(request.query)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        # 1. Check Cache (only for non-streaming)
        if not request.stream:
            cached = get_cached_response(current_tenant.id, request.query)
            if cached:
                return GenerateResponse(**cached)

        # 2. Retrieval
        documents = hybrid_search(request.query, current_tenant.id, top_k=request.top_k, filename=request.filename)
        
        sources = [
            SourceDocument(
                id=doc["id"],
                filename=doc["filename"],
                text=doc["text"],
                score=doc.get("score"),
                rerank_score=doc.get("rerank_score")
            )
            for doc in documents
        ]

        # 3. Generation
        if request.stream:
            async def event_generator():
                sources_data = [s.model_dump() for s in sources]
                yield f"data: {json.dumps({'sources': sources_data})}\n\n"
                
                async for chunk in generate_answer_stream(request.query, documents, request.temperature):
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
                    
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(event_generator(), media_type="text/event-stream")
            
        else:
            # Synchronous generation
            answer = generate_answer(request.query, documents, request.temperature)
            
            # Output Guardrail
            is_valid_out, reason_out = GuardrailManager.verify_output(answer)
            if not is_valid_out:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason_out)
            
            response_data = {
                "answer": answer,
                "sources": [s.model_dump() for s in sources],
                "cached": True # It will be true when fetched from cache next time
            }
            
            # Cache the new response
            set_cached_response(current_tenant.id, request.query, response_data)
            
            # Change cached to False for the immediate return
            response_data["cached"] = False
            return GenerateResponse(**response_data)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Generation failed for tenant {current_tenant.id}: {error_msg}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Generation failed: {error_msg}")


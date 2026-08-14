from app.worker.celery_app import celery_app
from app.services.ingestion import parse_document, chunk_text, generate_embeddings, store_in_qdrant
import os
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="process_document_task")
def process_document_task(file_path: str, tenant_id: str, original_filename: str):
    """
    Background task to process an uploaded document:
    1. Parse text.
    2. Chunk text.
    3. Generate embeddings.
    4. Store in Vector DB.
    """
    try:
        logger.info(f"Starting processing for file: {original_filename} (Tenant: {tenant_id})")
        
        # 1. Parse
        text = parse_document(file_path)
        if not text.strip():
            logger.warning(f"No text could be extracted from {original_filename}")
            return {"status": "failed", "reason": "No text extracted"}
            
        # 2. Chunk
        chunks = chunk_text(text)
        logger.info(f"Extracted {len(chunks)} chunks from {original_filename}")
        
        # 3. Embed
        embeddings = generate_embeddings(chunks)
        
        # 4. Store
        store_in_qdrant(chunks, embeddings, tenant_id, original_filename)
        
        logger.info(f"Successfully processed and stored {original_filename}")
        
        return {"status": "success", "chunks_processed": len(chunks)}
    except Exception as e:
        logger.error(f"Error processing {original_filename}: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")


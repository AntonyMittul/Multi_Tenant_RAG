from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from typing import List
import os
import uuid
import logging
from app.api import deps
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_document_background(text: str, tenant_id: str, original_filename: str):
    """
    Background task to process an uploaded document:
    1. Chunk text.
    2. Generate embeddings.
    3. Store in Vector DB.
    """
    try:
        from app.services.ingestion import chunk_text, generate_embeddings, store_in_qdrant
        logger.info(f"Starting processing for file: {original_filename} (Tenant: {tenant_id})")
        
        chunks = chunk_text(text)
        logger.info(f"Extracted {len(chunks)} chunks from {original_filename}")
        
        embeddings = generate_embeddings(chunks)
        
        store_in_qdrant(chunks, embeddings, tenant_id, original_filename)
        
        logger.info(f"Successfully processed and stored {original_filename}")
    except Exception as e:
        logger.error(f"Error processing {original_filename}: {str(e)}")


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Upload a document for ingestion. Supported formats: PDF, TXT.
    """
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a PDF or TXT file."
        )

    # Parse the document in memory
    content = await file.read()
    text = ""
    
    if file.filename.endswith(".pdf"):
        import io
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    elif file.filename.endswith(".txt"):
        text = content.decode("utf-8")
        
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the document."
        )

    file_id = str(uuid.uuid4())

    # Trigger FastAPI Background Task
    background_tasks.add_task(process_document_background, text, current_tenant.id, file.filename)
    
    return {
        "message": "Document uploaded successfully and queued for processing.",
        "file_id": file_id,
        "task_id": "fastapi-background-task"
    }


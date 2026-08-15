from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from typing import List
import os
import uuid
from app.api import deps
from app.models.tenant import Tenant
from app.worker.tasks import process_document_task

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    current_tenant: Tenant = Depends(deps.get_current_tenant)
):
    """
    Upload a document for ingestion. Supported formats: PDF, TXT.
    Returns a task ID for tracking.
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

    # Trigger a Celery task with the extracted text instead of file path
    task = process_document_task.delay(text, current_tenant.id, file.filename)
    task_id = task.id
    
    return {
        "message": "Document uploaded successfully and queued for processing.",
        "file_id": file_id,
        "task_id": task_id
    }


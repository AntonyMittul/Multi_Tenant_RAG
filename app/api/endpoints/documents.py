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

    # Save the file locally temporarily
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    saved_filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Trigger a Celery task
    task = process_document_task.delay(file_path, current_tenant.id, file.filename)
    task_id = task.id
    
    return {
        "message": "Document uploaded successfully and queued for processing.",
        "file_id": file_id,
        "task_id": task_id
    }


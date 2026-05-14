import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.schemas import APIResponse, APIError

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.getcwd(), "data", "raw_uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=APIResponse[dict])
async def upload_document(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and TXT are allowed."
        )

    # Basic magic byte validation
    header = await file.read(1024)
    await file.seek(0)
    
    if file.content_type == "application/pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Invalid PDF file format. Magic bytes mismatch.")
    elif file.content_type == "text/plain":
        if b'\x00' in header:
            raise HTTPException(status_code=400, detail="Invalid TXT file format. Null bytes detected.")

    # Size validation requires reading chunks
    # We will read chunks, write to disk, and keep track of total size
    # If size exceeds max, we delete the file and raise 413
    
    import re
    safe_filename = os.path.basename(file.filename)
    safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', safe_filename)
    if not safe_filename:
        safe_filename = "unnamed_file"
        
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    total_size = 0
    
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024) # 1MB chunks
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    break
                buffer.write(chunk)
                
        if total_size > MAX_FILE_SIZE:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File too large. Maximum size is 50MB."
            )
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        # Clean up partially written file on generic error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    return APIResponse(
        status="success",
        data={
            "filename": safe_filename,
            "msg": "File securely staged. Ready for telemetry-monitored injection."
        }
    )

@router.get("/process")
async def process_document(filename: str):
    """
    Initiates the heavy lifting while streaming real-time granular logs to frontend client.
    """
    from app.pipelines.indexing_orchestrator import stream_reindex_document
    from fastapi.responses import StreamingResponse
    import os

    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Target staged document vanished or was never uploaded.")

    return StreamingResponse(
        stream_reindex_document(file_path),
        media_type="text/event-stream"
    )

@router.post("/clear", response_model=APIResponse[dict])
async def clear_data():
    """
    Deletes internal vector knowledge and graph vertices.
    """
    from app.pipelines.indexing_orchestrator import clear_all_databases
    try:
        results = await clear_all_databases()
        return APIResponse(
            status="success",
            data=results
        )
    except Exception as e:
        logger.error(f"Data clearance API failure: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"System clearance aborted unexpectedly: {str(e)}"
        )


@router.get("/stats")
async def get_stats():
    # Gather counts from Vector and Graph DBs
    from app.pipelines.basic_rag import collection
    from app.pipelines.graphrag import tg_conn
    from app.pipelines.indexing_orchestrator import get_total_tokens
    
    total_tokens = get_total_tokens()
    
    vector_count = 0
    try:
        if collection:
            vector_count = collection.count()
    except Exception as e:
        logger.error(f"Vector stat err: {e}")

    doc_count = 0
    entity_count = 0
    try:
        if tg_conn:
            doc_count = tg_conn.getVertexCount("Document")
            entity_count = tg_conn.getVertexCount("Entity")
    except Exception as e:
        logger.error(f"TG stat err: {e}")

    return {
        "status": "success",
        "data": {
            "tokens": total_tokens,
            "vectors": vector_count,
            "documents": doc_count,
            "entities": entity_count
        }
    }

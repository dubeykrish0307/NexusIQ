import os
import shutil

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.db_operations import register_document
from app.ingestion import ingest_document
from app.schemas.document import DocumentListResponse, DocumentUploadResponse
from app.vectorstore import add_chunks_to_store, get_store

load_dotenv()

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIRECTORY", "./data/uploads")
MAX_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and ingest a document into the NexusIQ vector store."""
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        os.remove(file_path)
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f}MB). Max: {MAX_SIZE_MB}MB")

    try:
        parsed, chunks = ingest_document(file_path)
        stored_count = add_chunks_to_store(chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    register_document(
        db=db,
        file_name=parsed.file_name,
        file_type=parsed.file_type,
        document_category=parsed.document_category,
        detected_title=parsed.detected_title or "",
        detected_date=parsed.detected_date or "",
        chunks_created=len(chunks),
        char_count=parsed.char_count,
        word_count=parsed.word_count,
    )

    return DocumentUploadResponse(
        message="Document uploaded and ingested successfully.",
        document_name=parsed.file_name,
        document_category=parsed.document_category,
        detected_title=parsed.detected_title,
        detected_date=parsed.detected_date,
        chunks_created=len(chunks),
        chunks_stored=stored_count,
    )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents():
    """Return all documents currently stored in the vector store."""
    stats = get_store().get_stats()
    return DocumentListResponse(
        documents=stats["documents"],
        total_documents=stats["total_documents"],
        total_chunks=stats["total_chunks"],
    )


@router.delete("/{document_name}")
async def delete_document(document_name: str):
    """Remove a document and all its chunks from the vector store."""
    deleted = get_store().delete_document(document_name)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found.")
    return {"message": f"Deleted {deleted} chunks for '{document_name}'."}

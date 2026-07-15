from pydantic import BaseModel
from typing import Optional


class DocumentUploadResponse(BaseModel):
    """Returned after a document is successfully uploaded and ingested."""
    message: str
    document_name: str
    document_category: str
    detected_title: Optional[str]
    detected_date: Optional[str]
    chunks_created: int
    chunks_stored: int


class DocumentListResponse(BaseModel):
    """List of all documents currently in the vector store."""
    documents: list[str]
    total_documents: int
    total_chunks: int
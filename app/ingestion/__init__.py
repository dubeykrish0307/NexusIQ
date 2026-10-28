from app.ingestion.chunker import DocumentChunk, DocumentChunker
from app.ingestion.parser import DocumentParser, ParsedDocument


def ingest_document(file_path: str) -> tuple[ParsedDocument, list[DocumentChunk]]:
    """Parse, clean and chunk a file. Returns the parsed document (for metadata) and its chunks."""
    parsed = DocumentParser().parse(file_path)
    chunks = DocumentChunker(chunk_size=512, chunk_overlap=50).chunk_document(parsed)
    return parsed, chunks

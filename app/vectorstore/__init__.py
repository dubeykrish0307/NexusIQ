from app.ingestion.chunker import DocumentChunk
from app.vectorstore.embeddings import EmbeddingGenerator
from app.vectorstore.store import SearchResult, VectorStore

__all__ = ["EmbeddingGenerator", "SearchResult", "VectorStore", "get_store", "add_chunks_to_store", "search_documents"]

_store = None


def get_store() -> VectorStore:
    # one Chroma client for the whole app instead of reopening it on every call
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def add_chunks_to_store(chunks: list[DocumentChunk]) -> int:
    return get_store().add_chunks(chunks)


def search_documents(query: str, n_results: int = 5, document_filter: str = None) -> list[SearchResult]:
    return get_store().search(query, n_results, document_filter)

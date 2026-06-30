from app.vectorstore.store import VectorStore, SearchResult
from app.vectorstore.embeddings import EmbeddingGenerator
from app.ingestion.chunker import DocumentChunk


_store_instance = None


def get_store() -> VectorStore:
    """
    Return the singleton VectorStore instance.
    We use a singleton so the ChromaDB connection is opened once
    and reused across the entire application — not reopened on
    every function call.
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance


def add_chunks_to_store(chunks: list[DocumentChunk]) -> int:
    """Add document chunks to the vector store."""
    store = get_store()
    return store.add_chunks(chunks)


def search_documents(
    query: str,
    n_results: int = 5,
    document_filter: str = None
) -> list[SearchResult]:
    """Semantic search across all stored documents."""
    store = get_store()
    return store.search(query, n_results, document_filter)
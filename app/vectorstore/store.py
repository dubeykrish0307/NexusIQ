import os
from dataclasses import dataclass
from typing import Optional

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

from app.ingestion.chunker import DocumentChunk
from app.vectorstore.embeddings import EmbeddingGenerator

load_dotenv()


@dataclass
class SearchResult:
    chunk_id: str
    document_name: str
    document_category: str
    text: str
    page_number: Optional[int]
    relevance_score: float
    chunk_index: int
    metadata: dict


def _chunk_metadata(chunk: DocumentChunk) -> dict:
    # Chroma metadata values have to be plain scalars, so everything goes in as a string
    return {
        "document_name": chunk.document_name,
        "document_category": chunk.document_category,
        "page_number": str(chunk.page_number or 0),
        "chunk_index": str(chunk.chunk_index),
        "total_chunks": str(chunk.total_chunks),
        "detected_title": str(chunk.metadata.get("detected_title", "")),
        "detected_date": str(chunk.metadata.get("detected_date", "")),
        "file_type": str(chunk.metadata.get("file_type", "")),
    }


class VectorStore:
    COLLECTION_NAME = "nexusiq_documents"

    def __init__(self):
        persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedder = EmbeddingGenerator()

        print(f"VectorStore ready. Collection '{self.COLLECTION_NAME}' has {self.collection.count()} stored chunks.")

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Embed and store chunks that aren't in the collection yet. Returns how many were added."""
        if not chunks:
            return 0

        try:
            existing = self.collection.get(ids=[c.chunk_id for c in chunks], include=[])
            existing_ids = set(existing["ids"])
        except Exception:
            existing_ids = set()

        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
        if not new_chunks:
            print("  All chunks already stored. Skipping.")
            return 0

        print(f"  Embedding {len(new_chunks)} chunks...")
        texts = [c.text for c in new_chunks]

        self.collection.add(
            ids=[c.chunk_id for c in new_chunks],
            embeddings=self.embedder.embed_batch(texts),
            documents=texts,
            metadatas=[_chunk_metadata(c) for c in new_chunks],
        )

        print(f"  Stored {len(new_chunks)} chunks successfully.")
        return len(new_chunks)

    def search(self, query: str, n_results: int = 5, document_filter: Optional[str] = None) -> list[SearchResult]:
        """Return the n_results chunks closest to the query, best match first."""
        if self.collection.count() == 0:
            return []

        where = {"document_name": {"$eq": document_filter}} if document_filter else None
        results = self.collection.query(
            query_embeddings=[self.embedder.embed_text(query)],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "distances", "metadatas"],
            where=where,
        )

        hits = []
        for chunk_id, distance, text, meta in zip(
            results["ids"][0], results["distances"][0], results["documents"][0], results["metadatas"][0]
        ):
            hits.append(SearchResult(
                chunk_id=chunk_id,
                document_name=meta.get("document_name", ""),
                document_category=meta.get("document_category", ""),
                text=text,
                page_number=int(meta.get("page_number", 0)) or None,
                relevance_score=round(1.0 - distance, 4),  # cosine distance -> similarity
                chunk_index=int(meta.get("chunk_index", 0)),
                metadata=meta,
            ))

        return sorted(hits, key=lambda r: r.relevance_score, reverse=True)

    def delete_document(self, document_name: str) -> int:
        existing = self.collection.get(where={"document_name": {"$eq": document_name}}, include=[])
        if not existing["ids"]:
            return 0

        self.collection.delete(ids=existing["ids"])
        print(f"  Deleted {len(existing['ids'])} chunks for '{document_name}'.")
        return len(existing["ids"])

    def get_document_list(self) -> list[str]:
        if self.collection.count() == 0:
            return []
        metadatas = self.collection.get(include=["metadatas"])["metadatas"]
        return sorted({meta["document_name"] for meta in metadatas if "document_name" in meta})

    def get_stats(self) -> dict:
        documents = self.get_document_list()
        return {
            "total_chunks": self.collection.count(),
            "total_documents": len(documents),
            "documents": documents,
            "collection_name": self.COLLECTION_NAME,
        }

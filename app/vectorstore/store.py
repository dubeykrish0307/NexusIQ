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
    """
    A single result from a vector search.
    Wraps a chunk with its relevance score.
    """
    chunk_id: str
    document_name: str
    document_category: str
    text: str
    page_number: Optional[int]
    relevance_score: float
    chunk_index: int
    metadata: dict

class VectorStore:
    """
    Manages document storage and semantic search using ChromaDB.
    All document chunks are stored here as vector embeddings.
    """

    COLLECTION_NAME = "nexusiq_documents"

    def __init__(self):
        persist_dir = os.getenv(
            "CHROMA_PERSIST_DIRECTORY", "./data/chroma"
        )

        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        self.embedder = EmbeddingGenerator()

        print(f"VectorStore ready. "
              f"Collection '{self.COLLECTION_NAME}' has "
              f"{self.collection.count()} stored chunks.")
        
    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """
        Embed and store a list of document chunks.
        Skips chunks that are already stored (by chunk_id).
        Returns the number of new chunks actually added.
        """
        if not chunks:
            return 0

        existing_ids = set()
        try:
            existing = self.collection.get(
                ids=[c.chunk_id for c in chunks],
                include=[]
            )
            existing_ids = set(existing["ids"])
        except Exception:
            pass

        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

        if not new_chunks:
            print("  All chunks already stored. Skipping.")
            return 0

        print(f"  Embedding {len(new_chunks)} chunks...")
        texts = [chunk.text for chunk in new_chunks]
        embeddings = self.embedder.embed_batch(texts)

        ids = [chunk.chunk_id for chunk in new_chunks]
        documents = [chunk.text for chunk in new_chunks]
        metadatas = [
            {
                "document_name": chunk.document_name,
                "document_category": chunk.document_category,
                "page_number": str(chunk.page_number or 0),
                "chunk_index": str(chunk.chunk_index),
                "total_chunks": str(chunk.total_chunks),
                "detected_title": str(
                    chunk.metadata.get("detected_title", "")
                ),
                "detected_date": str(
                    chunk.metadata.get("detected_date", "")
                ),
                "file_type": str(
                    chunk.metadata.get("file_type", "")
                ),
            }
            for chunk in new_chunks
        ]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        print(f"  Stored {len(new_chunks)} chunks successfully.")
        return len(new_chunks)
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        document_filter: Optional[str] = None
    ) -> list[SearchResult]:
        """
        Semantic search: find the n most relevant chunks for a query.
        
        Args:
            query: Natural language question or search term
            n_results: How many chunks to return
            document_filter: If set, only search within this document
        
        Returns:
            List of SearchResult objects, sorted by relevance (best first)
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.embedder.embed_text(query)

        where_filter = None
        if document_filter:
            where_filter = {"document_name": {"$eq": document_filter}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "distances", "metadatas"],
            where=where_filter
        )

        search_results = []
        ids = results["ids"][0]
        distances = results["distances"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]

        for i in range(len(ids)):
            relevance_score = 1.0 - distances[i]

            search_results.append(SearchResult(
                chunk_id=ids[i],
                document_name=metadatas[i].get("document_name", ""),
                document_category=metadatas[i].get("document_category", ""),
                text=documents[i],
                page_number=int(metadatas[i].get("page_number", 0)) or None,
                relevance_score=round(relevance_score, 4),
                chunk_index=int(metadatas[i].get("chunk_index", 0)),
                metadata=metadatas[i]
            ))

        return sorted(search_results, key=lambda r: r.relevance_score, reverse=True)
    
    def delete_document(self, document_name: str) -> int:
        """
        Remove all chunks belonging to a document from the store.
        Used when a document is re-uploaded with changes.
        Returns the number of chunks deleted.
        """
        existing = self.collection.get(
            where={"document_name": {"$eq": document_name}},
            include=[]
        )

        if not existing["ids"]:
            return 0

        self.collection.delete(ids=existing["ids"])
        deleted_count = len(existing["ids"])
        print(f"  Deleted {deleted_count} chunks for '{document_name}'.")
        return deleted_count

    def get_document_list(self) -> list[str]:
        """
        Return a list of all unique document names in the store.
        """
        if self.collection.count() == 0:
            return []

        all_items = self.collection.get(include=["metadatas"])
        names = set()
        for meta in all_items["metadatas"]:
            if "document_name" in meta:
                names.add(meta["document_name"])

        return sorted(list(names))

    def get_stats(self) -> dict:
        """
        Return basic statistics about the collection.
        Useful for the UI and for debugging.
        """
        total_chunks = self.collection.count()
        documents = self.get_document_list()

        return {
            "total_chunks": total_chunks,
            "total_documents": len(documents),
            "documents": documents,
            "collection_name": self.COLLECTION_NAME,
        }
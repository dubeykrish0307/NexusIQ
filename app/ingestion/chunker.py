from dataclasses import dataclass, field
from typing import Optional

import tiktoken

from app.ingestion.parser import ParsedDocument


@dataclass
class DocumentChunk:
    chunk_id: str
    document_name: str
    document_category: str
    text: str
    token_count: int
    page_number: Optional[int]
    chunk_index: int
    total_chunks: int
    metadata: dict = field(default_factory=dict)


class DocumentChunker:
    """Splits a document into overlapping windows of chunk_size tokens."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, model: str = "gpt-4o"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoder = tiktoken.encoding_for_model(model)

    def chunk_document(self, document: ParsedDocument) -> list[DocumentChunk]:
        tokens = self.encoder.encode(document.raw_text)
        total_tokens = len(tokens)
        if total_tokens == 0:
            return []

        step = self.chunk_size - self.chunk_overlap
        windows = [
            (self.encoder.decode(tokens[start:start + self.chunk_size]), start)
            for start in range(0, total_tokens, step)
        ]

        chunks = []
        for index, (window_text, token_start) in enumerate(windows):
            text = window_text.strip()
            if not text:
                continue

            chunk_id = f"{document.file_name}_chunk_{index:04d}".replace(" ", "_").replace(".", "_")
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                document_name=document.file_name,
                document_category=document.document_category,
                text=text,
                token_count=len(self.encoder.encode(text)),
                page_number=self._estimate_page(token_start, total_tokens, document.page_count),
                chunk_index=index,
                total_chunks=len(windows),
                metadata={
                    "detected_title": document.detected_title,
                    "detected_date": document.detected_date,
                    "file_type": document.file_type,
                },
            ))

        return chunks

    def _estimate_page(self, token_start: int, total_tokens: int, page_count: int) -> Optional[int]:
        # rough: assumes tokens are spread evenly over the pages
        if page_count == 0 or total_tokens == 0:
            return None
        return min(int(token_start / total_tokens * page_count) + 1, page_count)

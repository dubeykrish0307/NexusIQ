from dataclasses import dataclass, field
from typing import Optional
import tiktoken
from app.ingestion.parser import ParsedDocument


@dataclass
class DocumentChunk:
    """
    A single chunk of a document, ready to be embedded and stored.
    Every piece of information the vector store needs is here.
    """
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
    """
    Splits a ParsedDocument into overlapping chunks of controlled token size.
    Uses tiktoken for exact token counting — the same tokenizer OpenAI uses.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model: str = "gpt-4o"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoder = tiktoken.encoding_for_model(model)

    def chunk_document(self, document: ParsedDocument) -> list[DocumentChunk]:
        """
        Main entry point. Takes a ParsedDocument and returns a list of chunks.
        """
        chunks = []
        text = document.raw_text
        tokens = self.encoder.encode(text)
        total_tokens = len(tokens)

        if total_tokens == 0:
            return chunks

        start = 0
        chunk_index = 0
        chunk_texts = []

        while start < total_tokens:
            end = min(start + self.chunk_size, total_tokens)
            chunk_token_ids = tokens[start:end]
            chunk_text = self.encoder.decode(chunk_token_ids)
            chunk_texts.append((chunk_text, start))
            start += self.chunk_size - self.chunk_overlap

        total_chunks = len(chunk_texts)

        for chunk_index, (chunk_text, token_start) in enumerate(chunk_texts):
            cleaned_chunk = chunk_text.strip()

            if not cleaned_chunk:
                continue

            page_number = self._estimate_page(
                token_start, total_tokens, document.page_count
            )

            chunk_id = (
                f"{document.file_name}_chunk_{chunk_index:04d}"
                .replace(" ", "_")
                .replace(".", "_")
            )

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_name=document.file_name,
                document_category=document.document_category,
                text=cleaned_chunk,
                token_count=len(self.encoder.encode(cleaned_chunk)),
                page_number=page_number,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
                metadata={
                    "detected_title": document.detected_title,
                    "detected_date": document.detected_date,
                    "file_type": document.file_type,
                }
            )
            chunks.append(chunk)

        return chunks

    def _estimate_page(
        self,
        token_start: int,
        total_tokens: int,
        page_count: int
    ) -> Optional[int]:
        """
        Estimate which page a chunk came from based on token position.
        This is an approximation — PDFs don't embed exact token-to-page mapping.
        """
        if page_count == 0 or total_tokens == 0:
            return None

        position_ratio = token_start / total_tokens
        estimated_page = int(position_ratio * page_count) + 1
        return min(estimated_page, page_count)
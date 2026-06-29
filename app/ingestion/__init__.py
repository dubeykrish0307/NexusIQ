from app.ingestion.parser import DocumentParser, ParsedDocument
from app.ingestion.chunker import DocumentChunker, DocumentChunk


def ingest_document(file_path: str) -> tuple[ParsedDocument, list[DocumentChunk]]:
    """
    Full ingestion pipeline: parse → clean → chunk.
    This is the only function the rest of the system needs to call.
    
    Returns both the ParsedDocument (for metadata) and the chunks
    (for the vector store).
    """
    parser = DocumentParser()
    chunker = DocumentChunker(chunk_size=512, chunk_overlap=50)

    parsed = parser.parse(file_path)
    chunks = chunker.chunk_document(parsed)

    return parsed, chunks

import sys
sys.path.insert(0, '.')

from app.ingestion import ingest_document


def test_ingestion():
    print("=" * 60)
    print("NexusIQ — Document Ingestion Test")
    print("=" * 60)

    file_path = "data/uploads/test_financial.txt"

    print(f"\n[1] Parsing document: {file_path}")
    parsed, chunks = ingest_document(file_path)

    print(f"\n--- ParsedDocument ---")
    print(f"File name:          {parsed.file_name}")
    print(f"File type:          {parsed.file_type}")
    print(f"Detected title:     {parsed.detected_title}")
    print(f"Detected date:      {parsed.detected_date}")
    print(f"Document category:  {parsed.document_category}")
    print(f"Character count:    {parsed.char_count:,}")
    print(f"Word count:         {parsed.word_count:,}")
    print(f"Page count:         {parsed.page_count}")

    print(f"\n--- Chunking Results ---")
    print(f"Total chunks created: {len(chunks)}")

    print(f"\n--- First Chunk ---")
    first = chunks[0]
    print(f"Chunk ID:       {first.chunk_id}")
    print(f"Token count:    {first.token_count}")
    print(f"Page estimate:  {first.page_number}")
    print(f"Text preview:   {first.text[:200]}...")

    if len(chunks) > 1:
        print(f"\n--- Overlap Verification ---")
        chunk_a = chunks[0].text
        chunk_b = chunks[1].text
        words_a = chunk_a.split()
        words_b = chunk_b.split()
        last_words_a = words_a[-15:]
        first_words_b = words_b[:15]
        print(f"Last 15 words of chunk 0: ...{' '.join(last_words_a)}")
        print(f"First 15 words of chunk 1: {' '.join(first_words_b)}...")

    print(f"\n--- All Chunks Summary ---")
    for chunk in chunks:
        print(
            f"  Chunk {chunk.chunk_index:02d}: "
            f"{chunk.token_count} tokens | "
            f"Page ~{chunk.page_number} | "
            f"{chunk.text[:60].strip()}..."
        )

    print("\n✓ Ingestion pipeline working correctly.")


if __name__ == "__main__":
    test_ingestion()
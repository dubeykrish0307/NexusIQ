import pytest

from app.ingestion import ingest_document

REPORT = "ANNUAL REPORT FOR FISCAL YEAR 2023\nTest Co\n\nFor the year ended December 31, 2023\n\n" + "\n\n".join(
    f"Segment {i} revenue was ${i * 1.5:.1f} million, up {i}% year over year. "
    f"Risk factor {i}: competition and currency exposure remain material."
    for i in range(1, 80)
)


def test_annual_report_metadata_and_chunks(tmp_path):
    path = tmp_path / "test_financial.txt"
    path.write_text(REPORT)

    parsed, chunks = ingest_document(str(path))

    assert parsed.file_name == "test_financial.txt"
    assert parsed.file_type == ".txt"
    assert parsed.document_category == "Annual Report (10-K)"
    assert parsed.detected_date == "December 31, 2023"
    assert parsed.word_count == len(parsed.raw_text.split())

    assert len(chunks) > 1
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.total_chunks == len(chunks) for c in chunks)

    # consecutive chunks share a 50-token overlap
    for a, b in zip(chunks, chunks[1:]):
        assert a.text[-40:] in b.text


def test_contract_is_detected(tmp_path):
    path = tmp_path / "nda.md"
    path.write_text("Service Agreement between A and B\n\nWHEREAS the parties agree to the terms and conditions below.")

    parsed, chunks = ingest_document(str(path))

    assert parsed.document_category == "Legal Contract"
    assert parsed.detected_title == "Service Agreement between A and B"
    assert len(chunks) == 1


def test_rejects_unsupported_and_missing_files(tmp_path):
    csv = tmp_path / "table.csv"
    csv.write_text("a,b\n1,2\n")

    with pytest.raises(ValueError):
        ingest_document(str(csv))
    with pytest.raises(FileNotFoundError):
        ingest_document(str(tmp_path / "missing.pdf"))

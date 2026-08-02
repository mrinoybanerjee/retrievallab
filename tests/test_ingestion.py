from pathlib import Path

import pytest
from retrievallab.ingestion import IngestionError, ingest_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_rejects_non_pdf_bytes() -> None:
    with pytest.raises(IngestionError, match="magic bytes") as error:
        ingest_pdf(b"not really a pdf", "notes.pdf")
    assert error.value.code == "invalid_pdf"


def test_ingests_generated_demo_pdf() -> None:
    path = ROOT / "data" / "demo" / "retrieval-handbook.pdf"
    if not path.exists():
        pytest.skip("Generate the demo PDF before running the integration ingestion test.")
    result = ingest_pdf(path.read_bytes(), path.name)
    assert result.page_count == 12
    assert result.chunk_count >= 12
    assert result.chunks[0].page == 1
    assert result.chunks[0].coordinates is not None

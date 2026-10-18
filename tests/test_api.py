from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_health_and_readiness() -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    readiness = client.get("/readyz").json()
    assert readiness["status"] == "ready"
    assert readiness["chunks"] >= 12


def test_demo_metadata_is_real() -> None:
    payload = client.get("/api/v1/demo").json()
    assert payload["corpus"]["pages"] == 12
    assert payload["corpus"]["chunks"] >= 12
    assert len(payload["suggested_questions"]) == 4


def test_unknown_corpus_returns_404() -> None:
    response = client.post("/api/v1/query", json={"question": "What is hybrid search?", "corpus_id": "missing"})
    assert response.status_code == 404


def test_phase_zero_report_is_explicitly_diagnostic() -> None:
    payload = client.get("/api/v1/research/phase-zero?suite=synthetic").json()

    assert payload["classification"] == "synthetic_diagnostic"
    assert payload["gate"]["status"] == "not_evaluable"
    assert payload["provenance"]["labels_used_in_scoring"] is False


def test_external_report_and_artifact_probe_are_available() -> None:
    report = client.get("/api/v1/research/phase-zero?suite=external").json()

    assert report["classification"] == "external_benchmark_subset"
    assert report["case_count"] == 2299
    assert report["comparison"]["delta"] < 0

    probe = client.post(
        "/api/v1/research/phase-zero/probe",
        json={
            "suite": "external",
            "case_id": "multiconir-books-0000-structured",
            "active_required_ids": ["c1", "c2", "c3"],
        },
    ).json()
    assert probe["active_required_ids"] == ["c1", "c2", "c3"]
    assert probe["classification"] == "interactive_diagnostic"


def test_phase_zero_probe_is_interactive_and_bounded() -> None:
    payload = client.post(
        "/api/v1/research/phase-zero/probe",
        json={
            "case_id": "catalog-security-platform",
            "active_required_ids": ["c1", "c2", "c3"],
            "active_excluded_ids": ["x1"],
        },
    ).json()

    assert payload["active_required_ids"] == ["c1", "c2", "c3"]
    assert payload["classification"] == "interactive_diagnostic"
    assert client.post(
        "/api/v1/research/phase-zero/probe",
        json={"case_id": "missing"},
    ).status_code == 404


def test_upload_size_is_bounded_before_parsing(monkeypatch) -> None:
    from services.api.app import main

    monkeypatch.setattr(main, "MAX_FILE_BYTES", 8)
    corpus = client.post("/api/v1/corpora", data={"name": "Synthetic upload"}).json()
    try:
        response = client.post(
            f"/api/v1/corpora/{corpus['id']}/documents",
            files={"file": ("synthetic.pdf", b"%PDF-" + b"x" * 20, "application/pdf")},
        )
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "file_too_large"
        assert corpus["id"] not in main.ENGINES
        assert main.CORPORA[corpus["id"]]["documents"] == 0
    finally:
        main.CORPORA.pop(corpus["id"], None)


def test_upload_reads_at_most_limit_plus_one(monkeypatch) -> None:
    import asyncio
    from unittest.mock import AsyncMock

    import pytest
    from fastapi import HTTPException

    from services.api.app import main

    monkeypatch.setattr(main, "MAX_FILE_BYTES", 8)
    upload = AsyncMock()
    upload.read.return_value = b"x" * 9
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.upload_document("demo", upload))
    assert error.value.status_code == 413
    upload.read.assert_awaited_once_with(9)

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

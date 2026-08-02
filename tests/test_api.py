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

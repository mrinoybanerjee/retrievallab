from pathlib import Path

import pytest
from retrievallab.models import Preset, TraceEvent
from retrievallab.pipeline import RetrievalEngine
from retrievallab.query import expand_query, rewrite_query

ROOT = Path(__file__).resolve().parents[1]


def engine() -> RetrievalEngine:
    return RetrievalEngine(ROOT / "data" / "demo" / "corpus.json")


def test_advanced_pipeline_finds_hybrid_search_page() -> None:
    result = engine().run(
        "Why does hybrid search outperform dense retrieval alone?",
        Preset.ADVANCED,
    )
    assert result["abstained"] is False
    assert result["hits"][0]["page"] == 2
    assert result["citations"][0]["page"] == 2
    assert "[1]" in result["answer"]


def test_advanced_pipeline_abstains_for_unsupported_question() -> None:
    result = engine().run("Who won the 2026 World Cup?", Preset.ADVANCED)
    assert result["abstained"] is True
    assert result["citations"] == []


def test_cache_is_scoped_by_preset_and_filters() -> None:
    retrieval = engine()
    first = retrieval.run("What does MRR measure?", Preset.BASELINE)
    second = retrieval.run("What does MRR measure?", Preset.BASELINE)
    advanced = retrieval.run("What does MRR measure?", Preset.ADVANCED)
    assert first["cached"] is False
    assert second["cached"] is True
    assert advanced["cached"] is False


def test_rewrite_and_expansion_are_visible_and_bounded() -> None:
    rewritten = rewrite_query("What's RAG and MRR?")
    expansion = expand_query("How does dense search combine results?", max_terms=3)
    assert "retrieval augmented generation" in rewritten
    assert "mean reciprocal rank" in rewritten
    assert len(expansion) <= 3


def test_optional_models_degrade_to_local_with_visible_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("model unavailable")

    monkeypatch.setenv("RETRIEVALLAB_DENSE_MODEL", "example/missing-dense")
    monkeypatch.setenv("RETRIEVALLAB_RERANKER_MODEL", "example/missing-reranker")
    monkeypatch.setattr("retrievallab.pipeline.NeuralDenseIndex", unavailable)
    monkeypatch.setattr("retrievallab.pipeline.neural_cross_rerank", unavailable)
    traces: list[TraceEvent] = []

    result = engine().run(
        "Why does hybrid search outperform dense retrieval alone?",
        Preset.ADVANCED,
        sink=traces.append,
    )

    assert result["hits"][0]["page"] == 2
    dense_trace = next(trace for trace in traces if trace.stage == "dense_retrieval")
    rerank_trace = next(trace for trace in traces if trace.stage == "rerank")
    assert dense_trace.payload["degraded"] is True
    assert rerank_trace.payload["degraded"] is True

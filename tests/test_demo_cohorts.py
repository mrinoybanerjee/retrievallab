import json
from pathlib import Path

import pytest

from scripts.run_demo_cohorts import run_cohorts

ROOT = Path(__file__).resolve().parents[1]


def test_cohorts_separate_retrieval_from_abstention(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVALLAB_DENSE_MODEL", "local")
    monkeypatch.setenv("RETRIEVALLAB_RERANKER_MODEL", "local")
    report = run_cohorts()
    historical = json.loads((ROOT / "data/benchmarks/demo-v1.json").read_text())
    golden = json.loads((ROOT / "data/demo/golden.json").read_text())["cases"]
    answerable_ids = {case["id"] for case in golden if case["relevant_pages"]}
    unsupported_ids = {case["id"] for case in golden if case.get("should_abstain", False)}
    for preset, cohorts in report["reports"].items():
        answerable, unsupported = cohorts["answerable"], cohorts["unsupported"]
        assert answerable["cases"] == 48
        assert unsupported["cases"] == 12
        assert {row["id"] for row in answerable["results"]} == answerable_ids
        assert {row["id"] for row in unsupported["results"]} == unsupported_ids
        # The historical scores credited unsupported abstentions as 1. Recover
        # them from separate cohorts without changing that artifact's contract.
        for metric in ("hit_rate_at_5", "mrr", "ndcg_at_10"):
            combined = (48 * answerable[metric] + 12 * unsupported["abstention_rate"]) / 60
            assert combined == pytest.approx(historical["reports"][preset][metric], abs=0.0001)


def test_offline_cohorts_reject_neural_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVALLAB_DENSE_MODEL", "some-neural-model")
    with pytest.raises(ValueError, match="must be local"):
        run_cohorts()

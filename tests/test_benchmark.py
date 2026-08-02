import json
from pathlib import Path

from services.api.app.main import run_evaluation

ROOT = Path(__file__).resolve().parents[1]
CORRECTNESS_METRICS = ("hit_rate_at_5", "mrr", "ndcg_at_10", "abstention_accuracy")


def test_demo_benchmark_does_not_regress() -> None:
    committed = json.loads((ROOT / "data" / "benchmarks" / "demo-v1.json").read_text(encoding="utf-8"))
    current = run_evaluation()

    assert current["case_count"] == 60
    for preset in ("baseline", "advanced"):
        for metric in CORRECTNESS_METRICS:
            floor = committed["reports"][preset][metric] - 0.02
            assert current["reports"][preset][metric] >= floor, f"{preset} {metric} regressed"

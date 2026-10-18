from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

from retrievallab.evaluation import ndcg_at_k, reciprocal_rank
from retrievallab.models import Preset
from retrievallab.pipeline import RetrievalEngine

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo"


def run_cohorts() -> dict[str, Any]:
    """Separate answerable retrieval from unsupported-query abstention, offline."""
    for variable in ("RETRIEVALLAB_DENSE_MODEL", "RETRIEVALLAB_RERANKER_MODEL"):
        if os.getenv(variable, "local") != "local":
            raise ValueError(f"{variable} must be local for this offline benchmark.")
    source = DATA / "golden.json"
    cases = json.loads(source.read_text(encoding="utf-8"))["cases"]
    engine = RetrievalEngine(DATA / "corpus.json")
    reports = {}
    for preset in (Preset.BASELINE, Preset.ADVANCED):
        answerable = []
        unsupported = []
        for case in cases:
            relevant = set(case["relevant_pages"])
            assert bool(relevant) != case.get("should_abstain", False), case["id"]
            output = engine.run(case["question"], preset, query_id=f"cohorts-{case['id']}")
            if relevant:
                pages = [hit["page"] for hit in output["hits"]]
                answerable.append({
                    "id": case["id"],
                    "hit_at_5": float(bool(relevant & set(pages[:5]))),
                    "reciprocal_rank": reciprocal_rank(pages, relevant),
                    "ndcg_at_10": ndcg_at_k(pages, relevant),
                    "abstained": output["abstained"],
                })
            else:
                unsupported.append({"id": case["id"], "abstained": output["abstained"]})
        reports[preset.value] = {
            "answerable": {
                "cases": len(answerable),
                "hit_rate_at_5": round(mean(row["hit_at_5"] for row in answerable), 4),
                "mrr": round(mean(row["reciprocal_rank"] for row in answerable), 4),
                "ndcg_at_10": round(mean(row["ndcg_at_10"] for row in answerable), 4),
                "false_abstentions": sum(row["abstained"] for row in answerable),
                "results": answerable,
            },
            "unsupported": {
                "cases": len(unsupported),
                "abstention_rate": round(mean(row["abstained"] for row in unsupported), 4),
                "results": unsupported,
            },
        }
    return {
        "suite": "demo-v1-cohorts",
        "classification": "synthetic_demo_regression",
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (source, DATA / "corpus.json")},
        "configuration": {"dense_encoder": "feature-hash-384", "reranker": "local", "web_fallback": False},
        "reports": reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report demo-v1 retrieval and abstention in separate cohorts.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/benchmarks/demo-v1-cohorts.json")
    arguments = parser.parse_args()
    report = run_cohorts()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(f"Wrote offline cohort report to {arguments.output}")


if __name__ == "__main__":
    main()

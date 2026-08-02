from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrievallab.phase0 import run_phase_zero

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "data" / "research" / "phase0-diagnostic-v1.json"
DEFAULT_OUTPUT = ROOT / "data" / "benchmarks" / "phase0-diagnostic-v1.json"
DEFAULT_WEB_OUTPUT = ROOT / "apps" / "web" / "public" / "benchmarks" / "phase0-diagnostic-v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the zero-training complete-before-partial diagnostic benchmark."
    )
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--web-output", type=Path, default=DEFAULT_WEB_OUTPUT)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--bootstrap-samples", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--case-payload-limit", type=int, default=0, help="Zero includes every case payload.")
    arguments = parser.parse_args()

    report = run_phase_zero(
        arguments.suite,
        repeats=arguments.repeats,
        bootstrap_samples=arguments.bootstrap_samples,
        seed=arguments.seed,
        case_payload_limit=arguments.case_payload_limit or None,
    )
    rendered = f"{json.dumps(report, indent=2)}\n"
    for output in {arguments.output, arguments.web_output}:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    summary = {
        "suite": report["suite"],
        "classification": report["classification"],
        "case_count": report["case_count"],
        "comparison": report["comparison"],
        "gate": report["gate"],
        "outputs": [str(arguments.output), str(arguments.web_output)],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

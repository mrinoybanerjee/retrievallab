from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.api.app.main import run_evaluation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "benchmarks" / "demo-v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic RetrievalLab benchmark.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    report = run_evaluation()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(report, indent=2)}\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

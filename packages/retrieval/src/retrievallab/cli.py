from __future__ import annotations

import argparse
import json
from pathlib import Path

from retrievallab.models import Preset
from retrievallab.pipeline import RetrievalEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a transparent RetrievalLab query.")
    parser.add_argument("question")
    parser.add_argument("--preset", choices=[preset.value for preset in Preset], default="advanced")
    parser.add_argument("--corpus", type=Path, default=Path("data/demo/corpus.json"))
    arguments = parser.parse_args()
    result = RetrievalEngine(arguments.corpus).run(arguments.question, Preset(arguments.preset))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

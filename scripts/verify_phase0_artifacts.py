from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_SOURCE = ROOT / "data" / "research" / "phase0-diagnostic-v1.json"
SYNTHETIC_REPORT = ROOT / "data" / "benchmarks" / "phase0-diagnostic-v1.json"
EXTERNAL_REPORT = ROOT / "data" / "benchmarks" / "multiconir-task2-structured-9884fb3e.json"
EXPECTED_MULTICONIR_REVISION = "9884fb3e1e5c06c9e026aa0042a679412dad1425"


def load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Research artifact verification failed: {message}")


def verify_public_copy(report_path: Path) -> None:
    public_path = ROOT / "apps" / "web" / "public" / "benchmarks" / report_path.name
    require(report_path.read_bytes() == public_path.read_bytes(), f"{report_path.name} public copy drifted")


def main() -> None:
    synthetic = load(SYNTHETIC_REPORT)
    external = load(EXTERNAL_REPORT)
    synthetic_source = SYNTHETIC_SOURCE.read_bytes()

    verify_public_copy(SYNTHETIC_REPORT)
    verify_public_copy(EXTERNAL_REPORT)
    require(synthetic["classification"] == "synthetic_diagnostic", "synthetic classification changed")
    require(synthetic["case_count"] == 16, "synthetic case count changed")
    require(synthetic["gate"]["status"] == "not_evaluable", "synthetic gate overclaims evidence")
    require(synthetic["provenance"]["labels_used_in_scoring"] is False, "synthetic scorer uses labels")
    require(
        hashlib.sha256(synthetic_source).hexdigest() == synthetic["provenance"]["source_sha256"],
        "synthetic source receipt does not match",
    )

    source = external["provenance"]["source"]
    require(external["classification"] == "external_benchmark_subset", "external classification changed")
    require(external["case_count"] == 2299, "external case count changed")
    require(source["revision"] == EXPECTED_MULTICONIR_REVISION, "MultiConIR revision changed")
    require(source["selected_row_count"] == 2307, "MultiConIR selected-row count changed")
    require(source["skipped_row_count"] == 8, "MultiConIR exclusion count changed")
    require(external["provenance"]["labels_used_in_scoring"] is False, "external scorer uses labels")
    require(external["gate"]["status"] == "not_evaluable", "external gate overclaims evidence")
    require(external["comparison"]["strongest_control"] == "bm25", "strongest external control changed")
    require(external["comparison"]["delta"] < 0, "rejected candidate no longer records a negative delta")
    require(external["economics"]["pareto_improvement_observed"] is False, "artifact claims a Pareto win")
    require(len(external["cases"]) == 10, "external dashboard example limit changed")
    require(len(external["provenance"]["source_sha256"]) == 64, "external source hash is malformed")
    require((ROOT / "LICENSES" / "Apache-2.0.txt").exists(), "MultiConIR license copy is missing")

    print("Phase 0 artifacts, public copies, source receipts, and claim boundaries verified.")


if __name__ == "__main__":
    main()

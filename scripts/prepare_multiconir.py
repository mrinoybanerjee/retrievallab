from __future__ import annotations

import argparse
import csv
import json
import random
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "external" / "multiconir-task2-probe.json"
DOMAINS = ("Books", "Legal Document", "Medical Case", "Movies", "People")
SEQUENTIAL_CONDITION = re.compile(r"(?<![A-Za-z0-9])(10|[1-9])\s*[.)]")


def _looks_like_list_marker(query: str, match: re.Match[str]) -> bool:
    following = query[match.end() : match.end() + 1]
    if not following.isdigit():
        return True
    prefix = query[: match.start()].rstrip()
    return not prefix or prefix[-1] in ",:;\n"


def extract_conditions(query: str) -> list[str]:
    matches = [match for match in SEQUENTIAL_CONDITION.finditer(query) if _looks_like_list_marker(query, match)]
    best_sequence: list[re.Match[str]] = []
    for start, first in enumerate(matches):
        if int(first.group(1)) != 1:
            continue
        sequence = [first]
        expected = 2
        for match in matches[start + 1 :]:
            if int(match.group(1)) == expected:
                sequence.append(match)
                expected += 1
                if expected == 11:
                    break
        if len(sequence) > len(best_sequence):
            best_sequence = sequence
        conditions = []
        for index, match in enumerate(sequence):
            end = sequence[index + 1].start() if index + 1 < len(sequence) else len(query)
            condition = query[match.end() : end].strip(" \n\t,;:.")
            if not condition:
                break
            conditions.append(condition)
        if len(conditions) == 10:
            return conditions
    bullet_conditions = [
        line.removeprefix("-").removeprefix("•").strip(" \n\t,;:.")
        for line in query.splitlines()
        if line.lstrip().startswith(("-", "•"))
    ]
    if len(bullet_conditions) >= 2 and all(bullet_conditions):
        return bullet_conditions
    if len(best_sequence) >= 2:
        conditions = []
        for index, match in enumerate(best_sequence):
            end = best_sequence[index + 1].start() if index + 1 < len(best_sequence) else len(query)
            condition = query[match.end() : end].strip(" \n\t,;:.")
            if condition:
                conditions.append(condition)
        if len(conditions) == len(best_sequence):
            return conditions
    raise ValueError(f"Could not recover ten ordered conditions from query: {query[:160]!r}")


def repository_revision(source: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_domain_rows(source: Path, domain: str) -> list[dict[str, str]]:
    path = source / "datasets" / "Task2_&_3" / f"{domain}_Task2_&_3.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_case(
    domain: str,
    row_index: int,
    row: dict[str, str],
    *,
    query_format: str,
) -> dict[str, Any]:
    structured_query = row["Query10"]
    conditions = extract_conditions(structured_query)
    query = row["Natural_Query10"] if query_format == "natural" else structured_query
    case_id = f"multiconir-{domain.lower().replace(' ', '-')}-{row_index:04d}-{query_format}"
    documents = [
        {"id": f"{case_id}-positive", "title": "Positive", "passages": [row["Positive"]]},
        *[
            {
                "id": f"{case_id}-hn{index}",
                "title": f"Hard negative {index}",
                "passages": [row[f"HN{index}"]],
            }
            for index in range(1, 11)
        ],
    ]
    return {
        "id": case_id,
        "family": f"multiconir-{domain.lower().replace(' ', '-')}",
        "query": query,
        "required": [
            {"id": f"c{index}", "text": condition, "aliases": []}
            for index, condition in enumerate(conditions, start=1)
        ],
        "excluded": [],
        "documents": documents,
        "complete_document_ids": [f"{case_id}-positive"],
        "partial_document_ids": [f"{case_id}-hn{index}" for index in range(1, 11)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize the official MultiConIR Task 2 data into RetrievalLab's probe schema."
    )
    parser.add_argument("--source", type=Path, required=True, help="Path to an EIT-NLP/MultiConIR checkout.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit-per-domain", type=int, default=0, help="Zero uses every row.")
    parser.add_argument("--query-format", choices=("structured", "natural", "both"), default="structured")
    parser.add_argument("--seed", type=int, default=1729)
    arguments = parser.parse_args()

    source = arguments.source.resolve()
    revision = repository_revision(source)
    generator = random.Random(arguments.seed)
    cases: list[dict[str, Any]] = []
    formats = ("structured", "natural") if arguments.query_format == "both" else (arguments.query_format,)
    available_domain_rows: dict[str, int] = {}
    selected_domain_rows: dict[str, int] = {}
    parse_errors: dict[str, int] = {}
    parse_error_examples: list[dict[str, object]] = []
    for domain in DOMAINS:
        rows = load_domain_rows(source, domain)
        available_domain_rows[domain] = len(rows)
        indexes = list(range(len(rows)))
        if arguments.limit_per_domain:
            indexes = sorted(generator.sample(indexes, min(arguments.limit_per_domain, len(indexes))))
        selected_domain_rows[domain] = len(indexes)
        parse_errors[domain] = 0
        for row_index in indexes:
            try:
                row_cases = [
                    build_case(domain, row_index, rows[row_index], query_format=query_format)
                    for query_format in formats
                ]
            except ValueError as error:
                parse_errors[domain] += 1
                if len(parse_error_examples) < 10:
                    parse_error_examples.append(
                        {"domain": domain, "row_index": row_index, "error": str(error)}
                    )
                continue
            cases.extend(row_cases)

    error_count = sum(parse_errors.values())
    selected_all_rows = arguments.limit_per_domain == 0
    is_full = selected_all_rows and error_count == 0
    if is_full:
        classification = "external_benchmark"
    elif selected_all_rows:
        classification = "external_benchmark_subset"
    else:
        classification = "external_benchmark_sample"
    payload = {
        "schema_version": "retrievallab-probe-v1",
        "suite": f"multiconir-task2-{arguments.query_format}-{revision[:8]}",
        "classification": classification,
        "description": (
            "MultiConIR Task 2 complete-versus-hard-negative ranking. Conditions are recovered from the paired "
            "structured Query10 field; no relevance label is used by a retrieval method."
        ),
        "source": {
            "name": "MultiConIR",
            "repository": "https://github.com/EIT-NLP/MultiConIR",
            "paper": "https://aclanthology.org/2025.findings-emnlp.726/",
            "license": "Apache-2.0",
            "revision": revision,
            "task": "Task2 relevance monotonicity",
            "query_format": arguments.query_format,
            "condition_source": "paired structured Query10",
            "selection": "all_source_rows" if selected_all_rows else "deterministic_sample",
            "available_domain_rows": available_domain_rows,
            "selected_domain_rows": selected_domain_rows,
            "selected_row_count": sum(selected_domain_rows.values()),
            "included_case_count": len(cases),
            "skipped_row_count": error_count,
            "parse_errors": parse_errors,
            "parse_error_examples": parse_error_examples,
            "sample_seed": arguments.seed if arguments.limit_per_domain else None,
        },
        "cases": cases,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(arguments.output),
                "suite": payload["suite"],
                "classification": payload["classification"],
                "case_count": len(cases),
                "revision": revision,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

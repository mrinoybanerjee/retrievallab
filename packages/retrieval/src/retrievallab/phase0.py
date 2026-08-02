from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from retrievallab.constraint import (
    METHOD_IDS,
    AtomicConstraint,
    MethodId,
    ProbeCase,
    ProbeDocument,
    RankingResult,
    SparseConstraintIndex,
)
from retrievallab.text import tokenize

PHASE_ZERO_VERSION = "phase0-diagnostic-v1"
PROBE_SCHEMA_VERSION = "retrievallab-probe-v1"
HEADLINE_METHODS: tuple[MethodId, ...] = ("dense", "hybrid", "coverage_first")
CONTROL_METHODS: tuple[MethodId, ...] = tuple(
    method for method in METHOD_IDS if method != "coverage_first"
)
METHOD_METADATA: dict[MethodId, dict[str, str]] = {
    "dense": {"label": "Naive dense", "family": "monolithic", "status": "control"},
    "bm25": {"label": "Monolithic BM25", "family": "monolithic", "status": "control"},
    "hybrid": {"label": "Hybrid RRF", "family": "production", "status": "control"},
    "bm25_and": {"label": "BM25 AND", "family": "Boolean", "status": "control"},
    "additive": {"label": "Condition additive", "family": "algebraic", "status": "control"},
    "minimum": {"label": "Condition minimum", "family": "algebraic", "status": "control"},
    "product": {"label": "Condition product", "family": "algebraic", "status": "control"},
    "harmonic": {"label": "Condition harmonic", "family": "algebraic", "status": "control"},
    "distinct_support": {
        "label": "Distinct-passage support",
        "family": "assignment",
        "status": "control",
    },
    "coverage_first": {
        "label": "Coverage-first sparse",
        "family": "experimental",
        "status": "unvalidated candidate",
    },
}


@dataclass(frozen=True, slots=True)
class ProbeSuite:
    id: str
    classification: str
    description: str
    source: dict[str, Any]
    cases: tuple[ProbeCase, ...]


def _atomic(payload: dict[str, Any], polarity: str) -> AtomicConstraint:
    if polarity not in {"required", "excluded"}:
        raise ValueError(f"Unsupported constraint polarity: {polarity}")
    return AtomicConstraint(
        id=str(payload["id"]),
        text=str(payload["text"]),
        aliases=tuple(str(alias) for alias in payload.get("aliases", [])),
        polarity=polarity,  # type: ignore[arg-type]
    )


def load_probe_suite(path: Path) -> ProbeSuite:
    payload = json.loads(path.read_text(encoding="utf-8"))
    suite_id = str(payload.get("suite", ""))
    schema_version = payload.get("schema_version")
    if suite_id != PHASE_ZERO_VERSION and schema_version != PROBE_SCHEMA_VERSION:
        raise ValueError(f"Expected schema {PROBE_SCHEMA_VERSION!r}.")
    cases: list[ProbeCase] = []
    seen_case_ids: set[str] = set()
    for item in payload["cases"]:
        case_id = str(item["id"])
        if case_id in seen_case_ids:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen_case_ids.add(case_id)
        documents = tuple(
            ProbeDocument(
                id=str(document["id"]),
                title=str(document["title"]),
                passages=tuple(str(passage) for passage in document["passages"]),
            )
            for document in item["documents"]
        )
        document_ids = {document.id for document in documents}
        complete = frozenset(str(document_id) for document_id in item["complete_document_ids"])
        partial = frozenset(str(document_id) for document_id in item["partial_document_ids"])
        if not complete or not complete <= document_ids:
            raise ValueError(f"Case {case_id} has invalid complete-document labels.")
        if not partial <= document_ids or complete & partial:
            raise ValueError(f"Case {case_id} has invalid partial-document labels.")
        cases.append(
            ProbeCase(
                id=case_id,
                family=str(item["family"]),
                query=str(item["query"]),
                required=tuple(_atomic(constraint, "required") for constraint in item["required"]),
                excluded=tuple(_atomic(constraint, "excluded") for constraint in item.get("excluded", [])),
                documents=documents,
                complete_document_ids=complete,
                partial_document_ids=partial,
            )
        )
    return ProbeSuite(
        id=suite_id,
        classification=str(payload.get("classification", "unclassified")),
        description=str(payload.get("description", "")),
        source=dict(payload.get("source", {})),
        cases=tuple(cases),
    )


def load_phase_zero_cases(path: Path) -> list[ProbeCase]:
    return list(load_probe_suite(path).cases)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[rank]


def _rank_metrics(case: ProbeCase, ranking: RankingResult, *, top_k: int = 10) -> dict[str, float]:
    ranks = {document_id: rank for rank, document_id in enumerate(ranking.ranked_document_ids, start=1)}
    best_complete = min((ranks[document_id] for document_id in case.complete_document_ids), default=len(ranks) + 1)
    best_partial = min((ranks[document_id] for document_id in case.partial_document_ids), default=len(ranks) + 1)
    pair_count = len(case.complete_document_ids) * len(case.partial_document_ids)
    correct_pairs = sum(
        ranks[complete_id] < ranks[partial_id]
        for complete_id in case.complete_document_ids
        for partial_id in case.partial_document_ids
    )
    return {
        "complete_before_partial_at_10": float(best_complete <= top_k and best_complete < best_partial),
        "recall_at_10": float(best_complete <= top_k),
        "logical_violation_at_1": float(ranking.ranked_document_ids[0] not in case.complete_document_ids),
        "pairwise_complete_over_partial": correct_pairs / max(pair_count, 1),
        "first_complete_rank": float(best_complete),
    }


def _paired_bootstrap_delta(
    candidate: list[float],
    control: list[float],
    *,
    samples: int,
    seed: int,
) -> dict[str, float]:
    if len(candidate) != len(control) or not candidate:
        raise ValueError("Paired bootstrap inputs must be non-empty and aligned.")
    generator = random.Random(seed)
    deltas = []
    for _ in range(samples):
        indexes = [generator.randrange(len(candidate)) for _ in candidate]
        deltas.append(mean(candidate[index] - control[index] for index in indexes))
    deltas.sort()
    lower = deltas[max(0, math.floor(0.025 * (len(deltas) - 1)))]
    upper = deltas[min(len(deltas) - 1, math.ceil(0.975 * (len(deltas) - 1)))]
    return {
        "delta": round(mean(candidate) - mean(control), 6),
        "ci95_low": round(lower, 6),
        "ci95_high": round(upper, 6),
        "bootstrap_samples": samples,
    }


def _paired_sign_test(candidate: list[float], control: list[float]) -> float:
    wins = sum(left > right for left, right in zip(candidate, control, strict=True))
    losses = sum(left < right for left, right in zip(candidate, control, strict=True))
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1)) / (2**discordant)
    return float(min(1.0, 2 * tail))


def _holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for index, (method, p_value) in enumerate(ordered):
        running = max(running, min(1.0, (count - index) * p_value))
        adjusted[method] = round(running, 6)
    return adjusted


def _variation(case: ProbeCase, variation: str) -> tuple[tuple[AtomicConstraint, ...], tuple[AtomicConstraint, ...]]:
    required = case.required
    excluded = case.excluded
    if variation == "oracle":
        return required, excluded
    if variation == "reordered":
        return tuple(reversed(required)), tuple(reversed(excluded))
    if variation == "duplicated":
        duplicate = replace(required[0], id=f"{required[0].id}-duplicate")
        return (duplicate, *required), excluded
    if variation == "removed":
        return required[:-1], excluded
    if variation == "parser_noise":
        tokens = tokenize(required[0].text)
        corrupted = replace(required[0], text=tokens[0] if tokens else "unknown", aliases=())
        return (corrupted, *required[1:]), excluded
    raise ValueError(f"Unknown variation: {variation}")


def _case_payload(
    case: ProbeCase,
    rankings: dict[MethodId, RankingResult],
) -> dict[str, Any]:
    candidate = rankings["coverage_first"]
    rank_maps = {
        method: {document_id: rank for rank, document_id in enumerate(result.ranked_document_ids, start=1)}
        for method, result in rankings.items()
    }
    return {
        "id": case.id,
        "family": case.family,
        "query": case.query,
        "required": [
            {"id": constraint.id, "text": constraint.text, "aliases": list(constraint.aliases)}
            for constraint in case.required
        ],
        "excluded": [
            {"id": constraint.id, "text": constraint.text, "aliases": list(constraint.aliases)}
            for constraint in case.excluded
        ],
        "complete_document_ids": sorted(case.complete_document_ids),
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "passages": list(document.passages),
                "truth": "complete" if document.id in case.complete_document_ids else "partial",
                "ranks": {method: rank_maps[method][document.id] for method in HEADLINE_METHODS},
                "candidate_score": candidate.scores[document.id],
                "condition_scores": candidate.condition_scores[document.id],
                "violation_scores": candidate.violation_scores[document.id],
            }
            for document in case.documents
        ],
        "candidate_trace": candidate.trace,
    }


def run_phase_zero(
    suite_path: Path,
    *,
    repeats: int = 5,
    bootstrap_samples: int = 2_000,
    seed: int = 1729,
    case_payload_limit: int | None = None,
) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be at least one")
    suite = load_probe_suite(suite_path)
    cases = list(suite.cases)
    outcomes: dict[MethodId, list[dict[str, float]]] = {method: [] for method in METHOD_IDS}
    latencies: dict[MethodId, list[float]] = {method: [] for method in METHOD_IDS}
    postings: dict[MethodId, list[int]] = {method: [] for method in METHOD_IDS}
    score_updates: dict[MethodId, list[int]] = {method: [] for method in METHOD_IDS}
    documents_scored: dict[MethodId, list[int]] = {method: [] for method in METHOD_IDS}
    case_payloads: list[dict[str, Any]] = []
    build_latencies: list[float] = []
    index_stats: list[dict[str, int]] = []
    perturbations: dict[str, list[float]] = {
        variation: [] for variation in ("oracle", "reordered", "duplicated", "removed", "parser_noise")
    }

    for case in cases:
        build_started = time.perf_counter()
        index = SparseConstraintIndex(case.documents)
        build_latencies.append((time.perf_counter() - build_started) * 1000)
        index_stats.append(index.index_stats)
        rankings: dict[MethodId, RankingResult] = {}
        for method in METHOD_IDS:
            timed_results = [index.rank(case, method) for _ in range(repeats)]
            ranking = timed_results[0]
            rankings[method] = ranking
            outcomes[method].append(_rank_metrics(case, ranking))
            latencies[method].extend(result.elapsed_ms for result in timed_results)
            postings[method].append(ranking.postings_touched)
            score_updates[method].append(ranking.score_updates)
            documents_scored[method].append(ranking.documents_scored)
        if case_payload_limit is None or len(case_payloads) < case_payload_limit:
            case_payloads.append(_case_payload(case, rankings))
        for variation in perturbations:
            required, excluded = _variation(case, variation)
            ranking = index.rank(case, "coverage_first", required=required, excluded=excluded)
            perturbations[variation].append(_rank_metrics(case, ranking)["complete_before_partial_at_10"])

    reports: dict[MethodId, dict[str, Any]] = {}
    success_vectors: dict[MethodId, list[float]] = {}
    for method in METHOD_IDS:
        method_outcomes = outcomes[method]
        successes = [outcome["complete_before_partial_at_10"] for outcome in method_outcomes]
        success_vectors[method] = successes
        success_rate = mean(successes)
        reports[method] = {
            **METHOD_METADATA[method],
            "complete_before_partial_at_10": round(success_rate, 4),
            "recall_at_10": round(mean(outcome["recall_at_10"] for outcome in method_outcomes), 4),
            "logical_violation_at_1": round(
                mean(outcome["logical_violation_at_1"] for outcome in method_outcomes), 4
            ),
            "pairwise_complete_over_partial": round(
                mean(outcome["pairwise_complete_over_partial"] for outcome in method_outcomes), 4
            ),
            "mean_first_complete_rank": round(
                mean(outcome["first_complete_rank"] for outcome in method_outcomes), 4
            ),
            "p50_latency_ms": round(median(latencies[method]), 4),
            "p95_latency_ms": round(_percentile(latencies[method], 0.95), 4),
            "mean_postings_touched": round(mean(postings[method]), 2),
            "mean_score_updates": round(mean(score_updates[method]), 2),
            "mean_documents_scored": round(mean(documents_scored[method]), 2),
            "cpu_ms_per_success": round(median(latencies[method]) / success_rate, 4) if success_rate else None,
        }

    control_priority = {method: index for index, method in enumerate(CONTROL_METHODS)}
    strongest_control = max(
        CONTROL_METHODS,
        key=lambda method: (
            reports[method]["complete_before_partial_at_10"],
            reports[method]["pairwise_complete_over_partial"],
            -control_priority[method],
        ),
    )
    comparison = _paired_bootstrap_delta(
        success_vectors["coverage_first"],
        success_vectors[strongest_control],
        samples=bootstrap_samples,
        seed=seed,
    )
    raw_p_values: dict[str, float] = {
        method: _paired_sign_test(success_vectors["coverage_first"], success_vectors[method])
        for method in CONTROL_METHODS
    }
    adjusted_p_values = _holm_adjust(raw_p_values)
    perturbation_report = {
        variation: {
            "complete_before_partial_at_10": round(mean(values), 4),
            "delta_from_oracle": round(mean(values) - mean(perturbations["oracle"]), 4),
        }
        for variation, values in perturbations.items()
    }

    control_gap = float(comparison["delta"])
    if control_gap < 0:
        diagnostic_decision = "candidate_underperforms_strongest_control"
    elif control_gap < 0.05:
        diagnostic_decision = "simple_control_matches_candidate"
    elif suite.classification == "synthetic_diagnostic":
        diagnostic_decision = "candidate_survives_synthetic_falsification_only"
    else:
        diagnostic_decision = "candidate_gain_requires_second_external_family"
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    external_suite = suite.classification.startswith("external_benchmark")
    external_sample = suite.classification == "external_benchmark_sample"
    control_report = reports[strongest_control]
    candidate_report = reports["coverage_first"]
    candidate_economics = {
        "reference_method": strongest_control,
        "documents_scored_reduction": round(
            1 - candidate_report["mean_documents_scored"] / control_report["mean_documents_scored"],
            6,
        ),
        "postings_touched_ratio": round(
            candidate_report["mean_postings_touched"] / max(control_report["mean_postings_touched"], 1),
            6,
        ),
        "p50_latency_ratio": round(
            candidate_report["p50_latency_ms"] / max(control_report["p50_latency_ms"], 0.0001),
            6,
        ),
        "cpu_ms_per_success_ratio": (
            round(candidate_report["cpu_ms_per_success"] / control_report["cpu_ms_per_success"], 6)
            if candidate_report["cpu_ms_per_success"] is not None
            and control_report["cpu_ms_per_success"] is not None
            else None
        ),
    }
    candidate_economics["pareto_improvement_observed"] = bool(
        control_gap >= 0
        and candidate_economics["postings_touched_ratio"] <= 1
        and candidate_economics["p50_latency_ratio"] <= 1
    )
    source_bytes = suite_path.read_bytes()
    return {
        "suite": suite.id,
        "classification": suite.classification,
        "description": suite.description,
        "case_count": len(cases),
        "family_count": len({case.family for case in cases}),
        "headline_methods": list(HEADLINE_METHODS),
        "reports": reports,
        "comparison": {
            "candidate": "coverage_first",
            "strongest_control": strongest_control,
            **comparison,
            "raw_sign_test_p": round(raw_p_values[strongest_control], 6),
            "holm_adjusted_p": adjusted_p_values[strongest_control],
        },
        "multiple_comparisons": {
            method: {
                "raw_sign_test_p": round(raw_p_values[method], 6),
                "holm_adjusted_p": adjusted_p_values[method],
            }
            for method in CONTROL_METHODS
        },
        "perturbations": perturbation_report,
        "gate": {
            "status": "not_evaluable",
            "diagnostic_decision": diagnostic_decision,
            "reason": (
                (
                    "This is a sample from one external benchmark family. The preregistered publication gate also "
                    "requires a full run, a structurally different external suite, ordinary-retrieval regression, "
                    "and scale economics."
                    if external_sample
                    else
                    "This is one external benchmark family. The preregistered publication gate also requires "
                    "a structurally different external suite, ordinary-retrieval regression, and scale economics."
                )
                if external_suite
                else (
                    "Synthetic fixtures can falsify implementation ideas but cannot satisfy the preregistered "
                    "publication gate. This artifact does not count as external validation; see the pinned "
                    "MultiConIR report for the current out-of-fixture evidence."
                )
            ),
            "criteria": [
                {"id": "two_external_families", "status": "one_measured" if external_suite else "pending"},
                {
                    "id": "five_point_gain_vs_strongest_control",
                    "status": (
                        "pass_one_suite"
                        if external_suite and control_gap >= 0.05
                        else "failed_one_suite"
                        if external_suite
                        else "diagnostic_only"
                    ),
                },
                {
                    "id": "parser_and_order_robustness",
                    "status": "oracle_structure_only" if external_suite else "diagnostic_only",
                },
                {"id": "beir_regression_under_one_point", "status": "pending"},
                {
                    "id": "latency_or_cost_pareto_gain",
                    "status": "microbenchmark_not_pareto" if external_suite else "pending_scale_test",
                },
                {
                    "id": "paired_statistics_and_multiplicity",
                    "status": "implemented_one_suite" if external_suite else "implemented_diagnostic",
                },
            ],
        },
        "economics": candidate_economics,
        "systems": {
            "index_build_p50_ms": round(median(build_latencies), 4),
            "index_build_p95_ms": round(_percentile(build_latencies, 0.95), 4),
            "mean_vocabulary_terms": round(mean(stat["vocabulary_terms"] for stat in index_stats), 2),
            "mean_posting_entries": round(mean(stat["posting_entries"] for stat in index_stats), 2),
            "mean_estimated_index_bytes": round(
                mean(stat["estimated_serialized_bytes"] for stat in index_stats), 2
            ),
        },
        "required_baselines": {
            "implemented": list(METHOD_IDS),
            "pending_external": [
                "SPLADE",
                "Set-Comp LSR",
                "current dense retriever",
                "cross-encoder reranker",
                "NSFL",
                "CoveR",
            ],
        },
        "provenance": {
            "generated_at": generated_at,
            "source_fixture": suite_path.name,
            "source_bytes": len(source_bytes),
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "source": suite.source,
            "seed": seed,
            "repeats_per_case": repeats,
            "bootstrap_samples": bootstrap_samples,
            "case_payload_limit": case_payload_limit,
            "case_payload_count": len(case_payloads),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "latency_scope": "warm in-process CPU wall time; machine-specific and informational",
            "labels_used_in_scoring": False,
            "claims_allowed": (
                "results on the pinned external benchmark snapshot only"
                if external_suite
                else "implementation validation and synthetic diagnostic behavior only"
            ),
            "claims_not_allowed": (
                "state of the art, scientific validation, publication readiness, or production economics"
            ),
        },
        "cases": case_payloads,
    }


def run_case_probe(
    suite_path: Path,
    case_id: str,
    *,
    active_required_ids: set[str] | None = None,
    active_excluded_ids: set[str] | None = None,
) -> dict[str, Any]:
    cases = load_phase_zero_cases(suite_path)
    case = next((candidate for candidate in cases if candidate.id == case_id), None)
    if case is None:
        raise KeyError(case_id)
    return _run_case_probe(
        case,
        active_required_ids=active_required_ids,
        active_excluded_ids=active_excluded_ids,
    )


def run_artifact_case_probe(
    report_path: Path,
    case_id: str,
    *,
    active_required_ids: set[str] | None = None,
    active_excluded_ids: set[str] | None = None,
) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    item = next((candidate for candidate in report.get("cases", []) if candidate["id"] == case_id), None)
    if item is None:
        raise KeyError(case_id)
    documents = tuple(
        ProbeDocument(
            id=str(document["id"]),
            title=str(document["title"]),
            passages=tuple(str(passage) for passage in document["passages"]),
        )
        for document in item["documents"]
    )
    case = ProbeCase(
        id=str(item["id"]),
        family=str(item["family"]),
        query=str(item["query"]),
        required=tuple(_atomic(constraint, "required") for constraint in item["required"]),
        excluded=tuple(_atomic(constraint, "excluded") for constraint in item.get("excluded", [])),
        documents=documents,
        complete_document_ids=frozenset(str(value) for value in item["complete_document_ids"]),
        partial_document_ids=frozenset(
            str(document["id"]) for document in item["documents"] if document["truth"] == "partial"
        ),
    )
    return _run_case_probe(
        case,
        active_required_ids=active_required_ids,
        active_excluded_ids=active_excluded_ids,
    )


def _run_case_probe(
    case: ProbeCase,
    *,
    active_required_ids: set[str] | None,
    active_excluded_ids: set[str] | None,
) -> dict[str, Any]:
    required = tuple(
        constraint
        for constraint in case.required
        if active_required_ids is None or constraint.id in active_required_ids
    )
    excluded = tuple(
        constraint
        for constraint in case.excluded
        if active_excluded_ids is None or constraint.id in active_excluded_ids
    )
    if not required:
        raise ValueError("At least one required condition must remain active.")
    index = SparseConstraintIndex(case.documents)
    rankings = {
        method: index.rank(case, method, required=required, excluded=excluded)
        for method in METHOD_IDS
    }
    payload = _case_payload(case, rankings)
    payload["active_required_ids"] = [constraint.id for constraint in required]
    payload["active_excluded_ids"] = [constraint.id for constraint in excluded]
    payload["method_runs"] = {
        method: {
            "ranked_document_ids": list(result.ranked_document_ids),
            "elapsed_ms": round(result.elapsed_ms, 4),
            "postings_touched": result.postings_touched,
            "score_updates": result.score_updates,
            "documents_scored": result.documents_scored,
            "trace": result.trace,
        }
        for method, result in rankings.items()
    }
    payload["index"] = index.index_stats
    payload["classification"] = "interactive_diagnostic"
    return payload

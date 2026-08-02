from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean
from typing import Any


def reciprocal_rank(retrieved_pages: list[int], relevant_pages: set[int]) -> float:
    for rank, page in enumerate(retrieved_pages, start=1):
        if page in relevant_pages:
            return 1 / rank
    return 0.0


def ndcg_at_k(retrieved_pages: list[int], relevant_pages: set[int], k: int = 10) -> float:
    gains = [1.0 if page in relevant_pages else 0.0 for page in retrieved_pages[:k]]
    dcg = sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))
    ideal_count = min(len(relevant_pages), k)
    ideal = sum(1 / math.log2(index + 2) for index in range(ideal_count))
    return dcg / ideal if ideal else 0.0


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    question: str
    relevant_pages: frozenset[int]
    should_abstain: bool = False


def aggregate(case_results: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "hit_rate_at_5": round(mean(result["hit_at_5"] for result in case_results), 4),
        "mrr": round(mean(result["reciprocal_rank"] for result in case_results), 4),
        "ndcg_at_10": round(mean(result["ndcg_at_10"] for result in case_results), 4),
        "abstention_accuracy": round(mean(result["abstention_correct"] for result in case_results), 4),
    }

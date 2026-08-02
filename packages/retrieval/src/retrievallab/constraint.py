from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import permutations
from typing import Any, Literal

from retrievallab.text import STOPWORDS, cosine, expanded_tokens, hashed_vector, tokenize

ConstraintPolarity = Literal["required", "excluded"]
MethodId = Literal[
    "dense",
    "bm25",
    "hybrid",
    "bm25_and",
    "additive",
    "minimum",
    "product",
    "harmonic",
    "distinct_support",
    "coverage_first",
]

METHOD_IDS: tuple[MethodId, ...] = (
    "dense",
    "bm25",
    "hybrid",
    "bm25_and",
    "additive",
    "minimum",
    "product",
    "harmonic",
    "distinct_support",
    "coverage_first",
)

EVIDENCE_THRESHOLD = 0.35


@dataclass(frozen=True, slots=True)
class AtomicConstraint:
    id: str
    text: str
    aliases: tuple[str, ...] = ()
    polarity: ConstraintPolarity = "required"

    @property
    def variants(self) -> tuple[str, ...]:
        return (self.text, *self.aliases)


@dataclass(frozen=True, slots=True)
class ProbeDocument:
    id: str
    title: str
    passages: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.passages)


@dataclass(frozen=True, slots=True)
class ProbeCase:
    id: str
    family: str
    query: str
    required: tuple[AtomicConstraint, ...]
    excluded: tuple[AtomicConstraint, ...]
    documents: tuple[ProbeDocument, ...]
    complete_document_ids: frozenset[str]
    partial_document_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class SparseWork:
    postings_touched: int
    score_updates: int

    def __add__(self, other: SparseWork) -> SparseWork:
        return SparseWork(
            postings_touched=self.postings_touched + other.postings_touched,
            score_updates=self.score_updates + other.score_updates,
        )


@dataclass(frozen=True, slots=True)
class RankingResult:
    method: MethodId
    ranked_document_ids: tuple[str, ...]
    scores: dict[str, float]
    condition_scores: dict[str, dict[str, float]]
    violation_scores: dict[str, dict[str, float]]
    elapsed_ms: float
    postings_touched: int
    score_updates: int
    documents_scored: int
    trace: dict[str, Any]


class _BM25PostingIndex:
    def __init__(self, texts: list[str], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.frequencies = [Counter(tokenize(text)) for text in texts]
        self.lengths = [sum(frequencies.values()) for frequencies in self.frequencies]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for item_index, frequencies in enumerate(self.frequencies):
            for token, frequency in frequencies.items():
                self.postings[token].append((item_index, frequency))
        count = len(texts)
        self.idf = {
            token: math.log(1 + (count - len(postings) + 0.5) / (len(postings) + 0.5))
            for token, postings in self.postings.items()
        }

    def score(self, query: str) -> tuple[list[float], SparseWork]:
        query_tokens = tuple(
            dict.fromkeys(token for token in expanded_tokens(query) if token not in STOPWORDS)
        )
        scores = [0.0] * len(self.frequencies)
        postings_touched = 0
        score_updates = 0
        for token in query_tokens:
            postings = self.postings.get(token, ())
            postings_touched += len(postings)
            for item_index, frequency in postings:
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * self.lengths[item_index] / max(self.average_length, 1)
                )
                scores[item_index] += self.idf.get(token, 0.0) * frequency * (self.k1 + 1) / denominator
                score_updates += 1
        return scores, SparseWork(postings_touched=postings_touched, score_updates=score_updates)

    @property
    def estimated_serialized_bytes(self) -> int:
        token_bytes = sum(len(token.encode("utf-8")) + 4 for token in self.postings)
        posting_bytes = sum(len(postings) * 8 for postings in self.postings.values())
        return token_bytes + posting_bytes


def _normalize(values: list[float]) -> list[float]:
    maximum = max(values, default=0.0)
    if maximum <= 0:
        return [0.0 for _ in values]
    return [value / maximum for value in values]


def _harmonic(values: list[float]) -> float:
    if not values or any(value <= 0 for value in values):
        return 0.0
    return len(values) / sum(1 / value for value in values)


def _distinct_support(matrix: list[list[float]]) -> float:
    """Return the strongest bottleneck score under a one-condition-per-passage assignment."""

    if not matrix:
        return 0.0
    passage_count = len(matrix[0])
    if passage_count == 0:
        return 0.0
    condition_count = len(matrix)
    if passage_count < condition_count:
        return min(max(row, default=0.0) for row in matrix)
    return max(
        (min(matrix[condition_index][passage_index] for condition_index, passage_index in enumerate(order))
         for order in permutations(range(passage_count), condition_count)),
        default=0.0,
    )


class SparseConstraintIndex:
    """Frozen zero-training index used to falsify constraint-aware retrieval ideas.

    Labels are never passed to this class. Every method sees the same document text,
    tokenization, condition decomposition, and sparse index.
    """

    def __init__(self, documents: tuple[ProbeDocument, ...]) -> None:
        self.documents = documents
        self.document_ids = tuple(document.id for document in documents)
        self._document_index = _BM25PostingIndex([document.text for document in documents])
        self._passages: list[str] = []
        self._passage_document_indexes: list[int] = []
        self._document_passage_indexes: list[list[int]] = [[] for _ in documents]
        for document_index, document in enumerate(documents):
            for passage in document.passages:
                passage_index = len(self._passages)
                self._passages.append(passage)
                self._passage_document_indexes.append(document_index)
                self._document_passage_indexes[document_index].append(passage_index)
        self._passage_index = _BM25PostingIndex(self._passages)
        self._dense_vectors = [hashed_vector(document.text) for document in documents]

    @property
    def index_stats(self) -> dict[str, int]:
        return {
            "documents": len(self.documents),
            "passages": len(self._passages),
            "vocabulary_terms": len(self._document_index.postings),
            "posting_entries": sum(len(postings) for postings in self._document_index.postings.values()),
            "estimated_serialized_bytes": self._document_index.estimated_serialized_bytes,
        }

    def _atomic_scores(
        self,
        constraint: AtomicConstraint,
        *,
        passages: bool = False,
    ) -> tuple[list[float], SparseWork]:
        index = self._passage_index if passages else self._document_index
        best = [0.0] * (len(self._passages) if passages else len(self.documents))
        work = SparseWork(postings_touched=0, score_updates=0)
        for variant in constraint.variants:
            scores, variant_work = index.score(variant)
            best = [max(current, candidate) for current, candidate in zip(best, scores, strict=True)]
            work += variant_work
        return _normalize(best), work

    def _condition_matrix(
        self,
        constraints: tuple[AtomicConstraint, ...],
        *,
        passages: bool = False,
    ) -> tuple[list[list[float]], SparseWork]:
        matrix: list[list[float]] = []
        work = SparseWork(postings_touched=0, score_updates=0)
        for constraint in constraints:
            scores, condition_work = self._atomic_scores(constraint, passages=passages)
            matrix.append(scores)
            work += condition_work
        return matrix, work

    def rank(
        self,
        case: ProbeCase,
        method: MethodId,
        *,
        required: tuple[AtomicConstraint, ...] | None = None,
        excluded: tuple[AtomicConstraint, ...] | None = None,
    ) -> RankingResult:
        started = time.perf_counter()
        required_constraints = required if required is not None else case.required
        excluded_constraints = excluded if excluded is not None else case.excluded
        if method == "coverage_first":
            required_constraints = tuple(
                {
                    (constraint.text.casefold().strip(), constraint.polarity): constraint
                    for constraint in required_constraints
                }.values()
            )

        required_matrix: list[list[float]] = []
        excluded_matrix: list[list[float]] = []
        condition_scores: dict[str, dict[str, float]] = {}
        violation_scores: dict[str, dict[str, float]] = {}
        sparse_work = SparseWork(postings_touched=0, score_updates=0)
        monolithic = [0.0] * len(self.documents)
        monolithic_work = SparseWork(postings_touched=0, score_updates=0)
        if method != "dense":
            monolithic, monolithic_work = self._document_index.score(case.query)
            monolithic = _normalize(monolithic)
        if method not in {"dense", "bm25", "hybrid"}:
            required_matrix, required_work = self._condition_matrix(required_constraints)
            excluded_matrix, excluded_work = self._condition_matrix(excluded_constraints)
            sparse_work = required_work + excluded_work + monolithic_work
            condition_scores = {
                document.id: {
                    constraint.id: round(required_matrix[condition_index][document_index], 6)
                    for condition_index, constraint in enumerate(required_constraints)
                }
                for document_index, document in enumerate(self.documents)
            }
            violation_scores = {
                document.id: {
                    constraint.id: round(excluded_matrix[condition_index][document_index], 6)
                    for condition_index, constraint in enumerate(excluded_constraints)
                }
                for document_index, document in enumerate(self.documents)
            }
        scores = [0.0] * len(self.documents)
        sort_keys: list[tuple[float, ...]] = []
        trace: dict[str, Any] = {
            "evidence_threshold": EVIDENCE_THRESHOLD,
            "condition_count": len(required_constraints),
            "excluded_condition_count": len(excluded_constraints),
            "labels_used_in_scoring": False,
        }
        documents_scored = len(self.documents)

        if method == "dense":
            query_vector = hashed_vector(case.query)
            scores = [max(cosine(query_vector, vector), 0.0) for vector in self._dense_vectors]
            sort_keys = [(score,) for score in scores]
            sparse_work = SparseWork(postings_touched=0, score_updates=0)
            trace["vector_dimensions"] = len(query_vector)
        elif method == "bm25":
            scores = monolithic
            sort_keys = [(score,) for score in scores]
            sparse_work = monolithic_work
        elif method == "hybrid":
            query_vector = hashed_vector(case.query)
            dense_scores = [max(cosine(query_vector, vector), 0.0) for vector in self._dense_vectors]
            dense_order = sorted(
                range(len(self.documents)),
                key=lambda index: (-dense_scores[index], self.document_ids[index]),
            )
            sparse_order = sorted(
                range(len(self.documents)),
                key=lambda index: (-monolithic[index], self.document_ids[index]),
            )
            dense_rank = {document_index: rank for rank, document_index in enumerate(dense_order, start=1)}
            sparse_rank = {document_index: rank for rank, document_index in enumerate(sparse_order, start=1)}
            scores = [
                1 / (60 + dense_rank[document_index]) + 1 / (60 + sparse_rank[document_index])
                for document_index in range(len(self.documents))
            ]
            sort_keys = [(score,) for score in scores]
            sparse_work = monolithic_work
            trace["rank_constant"] = 60
        else:
            candidate_indexes: set[int] = set(range(len(self.documents)))
            if method == "coverage_first" and required_matrix:
                matching_sets = [
                    {index for index, score in enumerate(row) if score >= EVIDENCE_THRESHOLD}
                    for row in required_matrix
                ]
                anchor_index = min(range(len(matching_sets)), key=lambda index: (len(matching_sets[index]), index))
                candidate_indexes = matching_sets[anchor_index]
                documents_scored = len(candidate_indexes)
                trace.update(
                    {
                        "execution": "rarest_condition_first",
                        "anchor_condition": required_constraints[anchor_index].id,
                        "anchor_candidates": len(candidate_indexes),
                        "ranking": "lexicographic_complete_then_coverage_then_weakest",
                        "documents_scored_definition": "condition tuples assembled after anchor traversal",
                    }
                )
            sort_keys = [
                (0.0, -1.0, 0.0, 0.0, 0.0, monolithic[document_index])
                for document_index in range(len(self.documents))
            ]
            for document_index in sorted(candidate_indexes):
                evidence = [row[document_index] for row in required_matrix]
                violations = [row[document_index] for row in excluded_matrix]
                coverage = sum(value >= EVIDENCE_THRESHOLD for value in evidence)
                violation_count = sum(value >= EVIDENCE_THRESHOLD for value in violations)
                coverage_ratio = coverage / max(len(evidence), 1)
                weakest = min(evidence, default=0.0)
                mean_evidence = sum(evidence) / max(len(evidence), 1)
                maximum_violation = max(violations, default=0.0)
                clean = violation_count == 0
                key: tuple[float, ...]

                if method == "bm25_and":
                    complete = coverage == len(evidence) and clean
                    score = float(complete) + 0.001 * mean_evidence
                    key = (
                        float(complete),
                        coverage_ratio,
                        -maximum_violation,
                        mean_evidence,
                        monolithic[document_index],
                    )
                elif method == "additive":
                    score = mean_evidence - 0.5 * maximum_violation
                    key = (score, monolithic[document_index])
                elif method == "minimum":
                    score = weakest * (1 - maximum_violation)
                    key = (score, mean_evidence, monolithic[document_index])
                elif method == "product":
                    score = math.prod(evidence) * (1 - maximum_violation)
                    key = (score, mean_evidence, monolithic[document_index])
                elif method == "harmonic":
                    score = _harmonic(evidence) * (1 - maximum_violation)
                    key = (score, mean_evidence, monolithic[document_index])
                elif method == "distinct_support":
                    score = 0.0
                    key = (0.0, mean_evidence, monolithic[document_index])
                else:
                    complete = coverage == len(evidence) and clean
                    score = 4 * float(complete) + coverage_ratio + 0.1 * weakest + 0.01 * mean_evidence
                    key = (
                        float(complete),
                        coverage_ratio - violation_count,
                        weakest,
                        -maximum_violation,
                        mean_evidence,
                        monolithic[document_index],
                    )
                scores[document_index] = score
                sort_keys[document_index] = key

            if method == "distinct_support":
                passage_matrix, passage_work = self._condition_matrix(required_constraints, passages=True)
                excluded_passages, excluded_passage_work = self._condition_matrix(excluded_constraints, passages=True)
                sparse_work += passage_work + excluded_passage_work
                for document_index, passage_indexes in enumerate(self._document_passage_indexes):
                    local_matrix = [
                        [row[passage_index] for passage_index in passage_indexes]
                        for row in passage_matrix
                    ]
                    support = _distinct_support(local_matrix)
                    violation = max(
                        (
                            excluded_passages[condition_index][passage_index]
                            for condition_index in range(len(excluded_passages))
                            for passage_index in passage_indexes
                        ),
                        default=0.0,
                    )
                    score = support * (1 - violation)
                    scores[document_index] = score
                    sort_keys[document_index] = (score, monolithic[document_index])
                trace["assignment"] = "exact_maximin_distinct_passage"

        ranked_indexes = sorted(
            range(len(self.documents)),
            key=lambda index: (tuple(-value for value in sort_keys[index]), self.document_ids[index]),
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return RankingResult(
            method=method,
            ranked_document_ids=tuple(self.document_ids[index] for index in ranked_indexes),
            scores={self.document_ids[index]: round(scores[index], 8) for index in range(len(self.documents))},
            condition_scores=condition_scores,
            violation_scores=violation_scores,
            elapsed_ms=elapsed_ms,
            postings_touched=sparse_work.postings_touched,
            score_updates=sparse_work.score_updates,
            documents_scored=documents_scored,
            trace=trace,
        )

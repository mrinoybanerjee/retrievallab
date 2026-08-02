from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

from retrievallab.models import Chunk, ScoredChunk
from retrievallab.text import SYNONYMS, content_tokens, cosine, expanded_tokens, hashed_vector, tokenize


class BM25Index:
    def __init__(self, chunks: list[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.documents = [tokenize(chunk.text) for chunk in chunks]
        self.lengths = [len(document) for document in self.documents]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.frequencies = [Counter(document) for document in self.documents]
        document_frequency: Counter[str] = Counter()
        for document in self.documents:
            document_frequency.update(set(document))
        count = len(chunks)
        self.idf = {
            token: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 12) -> list[tuple[int, float]]:
        query_tokens = expanded_tokens(query)
        scores: list[tuple[int, float]] = []
        for index, frequencies in enumerate(self.frequencies):
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * self.lengths[index] / max(self.average_length, 1)
                )
                score += self.idf.get(token, 0.0) * frequency * (self.k1 + 1) / denominator
            scores.append((index, score))
        return sorted(scores, key=lambda item: item[1], reverse=True)[:top_k]


class DenseIndex:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.vectors = [hashed_vector(chunk.text) for chunk in chunks]

    def search(self, query: str, top_k: int = 12) -> list[tuple[int, float]]:
        query_vector = hashed_vector(query)
        scores = [(index, max(cosine(query_vector, vector), 0.0)) for index, vector in enumerate(self.vectors)]
        return sorted(scores, key=lambda item: item[1], reverse=True)[:top_k]


def reciprocal_rank_fusion(
    chunks: list[Chunk],
    dense: Iterable[tuple[int, float]],
    sparse: Iterable[tuple[int, float]],
    *,
    rank_constant: int = 60,
) -> list[ScoredChunk]:
    by_index: dict[int, ScoredChunk] = {}
    for rank, (index, score) in enumerate(dense, start=1):
        item = by_index.setdefault(index, ScoredChunk(chunk=chunks[index]))
        item.dense_score = score
        item.fusion_score += 1 / (rank_constant + rank)
    for rank, (index, score) in enumerate(sparse, start=1):
        item = by_index.setdefault(index, ScoredChunk(chunk=chunks[index]))
        item.sparse_score = score
        item.fusion_score += 1 / (rank_constant + rank)
    return sorted(by_index.values(), key=lambda item: item.fusion_score, reverse=True)


def lexical_cross_rerank(query: str, candidates: list[ScoredChunk]) -> list[ScoredChunk]:
    """Transparent local reranker used when the optional neural model is unavailable."""

    query_tokens = content_tokens(query)
    query_set = set(query_tokens)
    query_bigrams = set(zip(query_tokens, query_tokens[1:], strict=False))
    for item in candidates:
        document_tokens = content_tokens(item.chunk.text)
        document_set = set(document_tokens)
        overlap = len(query_set & document_set) / max(len(query_set), 1)
        bigrams = set(zip(document_tokens, document_tokens[1:], strict=False))
        phrase = len(query_bigrams & bigrams) / max(len(query_bigrams), 1)
        numeric_query = {token for token in query_set if token.isdigit()}
        numeric_match = 1.0 if numeric_query and numeric_query <= document_set else 0.0
        item.rerank_score = 0.65 * overlap + 0.25 * phrase + 0.10 * numeric_match
        normalized_fusion = min(item.fusion_score / (2 / 61), 1.0)
        item.final_score = 0.20 * normalized_fusion + 0.80 * item.rerank_score
    return sorted(candidates, key=lambda item: item.final_score, reverse=True)


def late_interaction_score(query: str, text: str) -> float:
    """Transparent MaxSim surrogate for the default zero-download pipeline.

    Each query token keeps its own representation and selects the strongest document-token
    match. The optional model preset remains the neural upgrade path; this local scorer uses
    exact, synonym, and conservative stem similarity so its behavior is easy to explain.
    """

    query_tokens = content_tokens(query)
    document_tokens = content_tokens(text)[:180]
    if not query_tokens or not document_tokens:
        return 0.0

    def similarity(query_token: str, document_token: str) -> float:
        if query_token == document_token:
            return 1.0
        if document_token in SYNONYMS.get(query_token, ()) or query_token in SYNONYMS.get(document_token, ()):
            return 0.72
        if min(len(query_token), len(document_token)) >= 5 and (
            query_token.startswith(document_token) or document_token.startswith(query_token)
        ):
            return 0.58
        return 0.0

    return sum(
        max(similarity(query_token, document_token) for document_token in document_tokens)
        for query_token in query_tokens
    ) / len(query_tokens)


def apply_late_interaction(candidates: list[ScoredChunk], query: str, top_n: int = 6) -> list[ScoredChunk]:
    for item in candidates[:top_n]:
        item.late_score = late_interaction_score(query, item.chunk.text)
        item.final_score = 0.78 * item.final_score + 0.22 * item.late_score
    return sorted(candidates, key=lambda item: item.final_score, reverse=True)


def metadata_filter(chunks: list[Chunk], filters: dict[str, str]) -> list[Chunk]:
    if not filters:
        return chunks
    return [chunk for chunk in chunks if all(chunk.metadata.get(key) == value for key, value in filters.items())]

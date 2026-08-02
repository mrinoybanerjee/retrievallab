from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from retrievallab.models import Chunk, ScoredChunk

DEFAULT_DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=2)
def _dense_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    return SentenceTransformer(model_name)


@lru_cache(maxsize=2)
def _cross_encoder(model_name: str) -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


class NeuralDenseIndex:
    def __init__(self, chunks: list[Chunk], model_name: str = DEFAULT_DENSE_MODEL) -> None:
        self.chunks = chunks
        self.model_name = model_name
        self.model = _dense_model(model_name)
        self.vectors = self.model.encode([chunk.text for chunk in chunks], normalize_embeddings=True)

    def search(self, query: str, top_k: int = 12) -> list[tuple[int, float]]:
        query_vector = self.model.encode([query], normalize_embeddings=True)[0]
        scores = [(index, max(float(vector @ query_vector), 0.0)) for index, vector in enumerate(self.vectors)]
        return sorted(scores, key=lambda item: item[1], reverse=True)[:top_k]


def neural_cross_rerank(
    query: str,
    candidates: list[ScoredChunk],
    model_name: str = DEFAULT_RERANKER_MODEL,
) -> list[ScoredChunk]:
    model = _cross_encoder(model_name)
    scores = model.predict([(query, item.chunk.text) for item in candidates])
    for item, raw_score in zip(candidates, scores, strict=True):
        item.rerank_score = 1 / (1 + math.exp(-float(raw_score)))
        item.final_score = 0.35 * item.fusion_score * 60 + 0.65 * item.rerank_score
    return sorted(candidates, key=lambda item: item.final_score, reverse=True)

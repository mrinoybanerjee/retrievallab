from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.IGNORECASE)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}

SYNONYMS: dict[str, tuple[str, ...]] = {
    "accurate": ("relevant", "precision", "quality"),
    "cache": ("latency", "memoization", "reuse"),
    "cite": ("citation", "source", "grounding"),
    "chunk": ("segment", "passage", "window"),
    "combine": ("fusion", "hybrid", "merge"),
    "confident": ("confidence", "threshold", "abstain"),
    "dense": ("semantic", "embedding", "vector"),
    "evaluate": ("benchmark", "metric", "golden"),
    "fast": ("latency", "cache", "performance"),
    "filter": ("metadata", "scope", "constraint"),
    "hallucination": ("grounding", "unsupported", "citation"),
    "page": ("citation", "source", "document"),
    "rank": ("rerank", "ordering", "relevance"),
    "rewrite": ("expansion", "ambiguity", "query"),
    "sparse": ("lexical", "bm25", "keyword"),
}


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def content_tokens(text: str) -> list[str]:
    """Return retrieval-bearing tokens, excluding common question scaffolding."""

    return [token for token in tokenize(text) if token not in STOPWORDS]


def token_windows(text: str, size: int, overlap: int) -> list[tuple[str, int, int]]:
    """Split by token count while preserving the original punctuation and casing."""

    matches = list(TOKEN_RE.finditer(text))
    windows: list[tuple[str, int, int]] = []
    cursor = 0
    while cursor < len(matches):
        end = min(cursor + size, len(matches))
        excerpt = text[matches[cursor].start() : matches[end - 1].end()].strip()
        windows.append((excerpt, cursor, end))
        if end == len(matches):
            break
        cursor += size - overlap
    return windows


def expanded_tokens(text: str) -> list[str]:
    tokens = tokenize(text)
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, ()))
    return expanded


def hashed_vector(text: str, dimensions: int = 384, *, token_level: bool = False) -> list[float]:
    """Create a deterministic dense feature vector for the zero-download demo preset.

    This is deliberately labelled as a feature-hashing encoder in the UI. The optional
    transformer preset replaces it with a neural SentenceTransformer model.
    """

    tokens = expanded_tokens(text)
    features = list(tokens)
    if not token_level:
        features.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False))
    vector = [0.0] * dimensions
    for feature, count in Counter(features).items():
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % dimensions
        sign = 1.0 if digest[0] & 1 else -1.0
        vector[index] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def sentence_candidates(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]

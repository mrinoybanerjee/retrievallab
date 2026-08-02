from __future__ import annotations

from retrievallab.text import SYNONYMS, tokenize


def rewrite_query(question: str) -> str:
    cleaned = " ".join(question.strip().split())
    replacements = {
        "how do i": "how to",
        "what's": "what is",
        "rag": "retrieval augmented generation",
        "rrf": "reciprocal rank fusion",
        "mrr": "mean reciprocal rank",
        "ndcg": "normalized discounted cumulative gain",
    }
    lowered = cleaned.lower()
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    return lowered


def expand_query(question: str, max_terms: int = 5) -> list[str]:
    additions: list[str] = []
    for token in tokenize(question):
        for synonym in SYNONYMS.get(token, ()):
            if synonym not in additions:
                additions.append(synonym)
            if len(additions) == max_terms:
                return additions
    return additions

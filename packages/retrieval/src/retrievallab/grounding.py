from __future__ import annotations

from collections import Counter
from typing import Any

from retrievallab.models import ScoredChunk
from retrievallab.text import content_tokens, sentence_candidates, tokenize


def synthesize_answer(
    question: str, results: list[ScoredChunk], max_sentences: int = 3
) -> tuple[str, list[dict[str, Any]]]:
    query_terms = set(tokenize(question))
    ranked_sentences: list[tuple[float, str, ScoredChunk]] = []
    for result in results[:5]:
        for sentence in sentence_candidates(result.chunk.text):
            terms = set(tokenize(sentence))
            overlap = len(query_terms & terms) / max(len(query_terms), 1)
            ranked_sentences.append((0.7 * overlap + 0.3 * result.final_score, sentence, result))
    ranked_sentences.sort(key=lambda item: item[0], reverse=True)

    selected: list[tuple[str, ScoredChunk]] = []
    seen: set[str] = set()
    for _, sentence, result in ranked_sentences:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        selected.append((sentence, result))
        if len(selected) == max_sentences:
            break

    answer_parts: list[str] = []
    citations: list[dict[str, Any]] = []
    for number, (sentence, result) in enumerate(selected, start=1):
        answer_parts.append(f"{sentence} [{number}]")
        citations.append(
            {
                "id": number,
                "source": result.chunk.source,
                "page": result.chunk.page,
                "section": result.chunk.section,
                "quote": sentence,
                "score": round(result.final_score, 4),
                "coordinates": result.chunk.coordinates,
            }
        )
    return " ".join(answer_parts), citations


def confidence_score(question: str, results: list[ScoredChunk], citations: list[dict[str, Any]]) -> float:
    if not results or not citations:
        return 0.0
    query_terms = set(content_tokens(question))
    if not query_terms:
        return 0.0
    numeric_terms = {term for term in query_terms if term.isdigit()}
    top_passages = results[:3]
    if numeric_terms and not any(numeric_terms <= set(tokenize(item.chunk.text)) for item in top_passages):
        return 0.0
    coverage_counter: Counter[str] = Counter()
    for citation in citations:
        coverage_counter.update(query_terms & set(tokenize(citation["quote"])))
    coverage = len(coverage_counter) / max(len(query_terms), 1)
    passage_coverage = max(
        len(query_terms & set(tokenize(item.chunk.text))) / len(query_terms) for item in top_passages
    )
    agreement = sum(
        len(query_terms & set(tokenize(item.chunk.text))) / len(query_terms) >= 0.35 for item in top_passages
    ) / len(top_passages)
    retrieval_strength = min(max(results[0].final_score, 0.0), 1.0)
    return round(0.35 * coverage + 0.25 * passage_coverage + 0.15 * agreement + 0.25 * retrieval_strength, 4)

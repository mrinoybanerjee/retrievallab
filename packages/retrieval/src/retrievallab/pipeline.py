from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from retrievallab.corpus import load_demo_corpus
from retrievallab.grounding import confidence_score, synthesize_answer
from retrievallab.models import Chunk, Preset, ScoredChunk, TraceEvent
from retrievallab.neural import DEFAULT_DENSE_MODEL, DEFAULT_RERANKER_MODEL, NeuralDenseIndex, neural_cross_rerank
from retrievallab.query import expand_query, rewrite_query
from retrievallab.retrieval import (
    BM25Index,
    DenseIndex,
    apply_late_interaction,
    lexical_cross_rerank,
    metadata_filter,
    reciprocal_rank_fusion,
)
from retrievallab.web_fallback import wikipedia_search

EventSink = Callable[[TraceEvent], None]


class RetrievalEngine:
    def __init__(self, corpus_path: Path | None = None, *, chunks: list[Chunk] | None = None) -> None:
        if chunks is None and corpus_path is None:
            raise ValueError("Provide either corpus_path or chunks.")
        self.all_chunks = chunks if chunks is not None else load_demo_corpus(corpus_path)  # type: ignore[arg-type]
        self._cache: dict[str, dict[str, Any]] = {}

    def _event(
        self,
        sink: EventSink | None,
        *,
        query_id: str,
        pipeline: Preset,
        sequence: int,
        stage: str,
        start: float,
        message: str,
        payload: dict[str, Any] | None = None,
        status: str = "completed",
    ) -> None:
        if sink:
            sink(
                TraceEvent(
                    query_id=query_id,
                    pipeline=pipeline,
                    sequence=sequence,
                    stage=stage,
                    status=status,
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                    message=message,
                    payload=payload or {},
                )
            )

    def run(
        self,
        question: str,
        preset: Preset,
        *,
        query_id: str = "local",
        metadata: dict[str, str] | None = None,
        sink: EventSink | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        filters = metadata or {}
        cache_key = f"{preset}:{question.lower().strip()}:{sorted(filters.items())}"
        if cache_key in self._cache:
            cached = {**self._cache[cache_key], "cached": True}
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=1,
                stage="cache",
                start=started,
                message="Reused a complete local result.",
                payload={"hit": True},
            )
            return cached

        chunks = metadata_filter(self.all_chunks, filters)
        self._event(
            sink,
            query_id=query_id,
            pipeline=preset,
            sequence=1,
            stage="scope",
            start=started,
            message=f"Scoped the corpus to {len(chunks)} child chunks.",
            payload={"candidate_count": len(chunks), "filters": filters},
        )
        if not chunks:
            return {
                "pipeline": preset,
                "answer": "No indexed passages match the selected metadata filters.",
                "abstained": True,
                "confidence": 0.0,
                "citations": [],
                "hits": [],
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "cached": False,
            }

        dense_model = os.getenv("RETRIEVALLAB_DENSE_MODEL", "local")
        dense_degraded = False
        dense_index: NeuralDenseIndex | DenseIndex
        if dense_model != "local":
            try:
                dense_index = NeuralDenseIndex(chunks, dense_model)
            except Exception:  # optional dependency/model boundary
                dense_index = DenseIndex(chunks)
                dense_degraded = True
        else:
            dense_index = DenseIndex(chunks)
        sequence = 2
        retrieval_question = question
        grounding_question = question
        expansions: list[str] = []
        if preset == Preset.ADVANCED:
            grounding_question = rewrite_query(question)
            expansions = expand_query(grounding_question)
            retrieval_question = f"{grounding_question} {' '.join(expansions)}".strip()
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=sequence,
                stage="rewrite",
                start=started,
                message="Rewrote ambiguity and added bounded expansion terms.",
                payload={"rewritten_query": retrieval_question, "expansions": expansions},
            )
            sequence += 1

        dense = dense_index.search(retrieval_question, top_k=12)
        self._event(
            sink,
            query_id=query_id,
            pipeline=preset,
            sequence=sequence,
            stage="dense_retrieval",
            start=started,
            message=(
                "The neural dense model was unavailable; ranked with the local encoder."
                if dense_degraded
                else "Encoded the query and ranked dense candidates."
            ),
            payload={
                "top_k": 12,
                "encoder": dense_model if dense_model != "local" and not dense_degraded else "feature-hash-384",
                "neural_default": DEFAULT_DENSE_MODEL,
                "degraded": dense_degraded,
            },
        )
        sequence += 1

        if preset == Preset.BASELINE:
            results = [
                ScoredChunk(chunk=chunks[index], dense_score=score, final_score=score) for index, score in dense[:6]
            ]
        else:
            sparse = BM25Index(chunks).search(retrieval_question, top_k=12)
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=sequence,
                stage="sparse_retrieval",
                start=started,
                message="Ranked exact and rare-term matches with BM25.",
                payload={"top_k": 12, "k1": 1.5, "b": 0.75},
            )
            sequence += 1
            results = reciprocal_rank_fusion(chunks, dense, sparse)[:10]
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=sequence,
                stage="fusion",
                start=started,
                message="Fused both ranked lists with reciprocal-rank fusion.",
                payload={"candidate_count": len(results), "rank_constant": 60},
            )
            sequence += 1
            reranker_model = os.getenv("RETRIEVALLAB_RERANKER_MODEL", "local")
            reranker_degraded = False
            if reranker_model != "local":
                try:
                    results = neural_cross_rerank(grounding_question, results, reranker_model)
                except Exception:  # optional dependency/model boundary
                    results = lexical_cross_rerank(grounding_question, results)
                    reranker_degraded = True
            else:
                results = lexical_cross_rerank(grounding_question, results)
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=sequence,
                stage="rerank",
                start=started,
                message=(
                    "The neural reranker was unavailable; used the local cross-feature scorer."
                    if reranker_degraded
                    else "Reranked the fused top 10."
                ),
                payload={
                    "model": (
                        reranker_model
                        if reranker_model != "local" and not reranker_degraded
                        else "local-cross-feature-v1"
                    ),
                    "neural_default": DEFAULT_RERANKER_MODEL,
                    "degraded": reranker_degraded,
                },
            )
            sequence += 1
            results = apply_late_interaction(results, grounding_question)
            self._event(
                sink,
                query_id=query_id,
                pipeline=preset,
                sequence=sequence,
                stage="late_interaction",
                start=started,
                message="Applied token-level MaxSim to the highest-ranked passages.",
                payload={"algorithm": "maxsim", "top_n": 6},
            )
            sequence += 1

        answer, citations = synthesize_answer(grounding_question, results)
        confidence = confidence_score(grounding_question, results, citations)
        threshold = 0.31 if preset == Preset.ADVANCED else 0.26
        abstained = confidence < threshold
        if abstained:
            answer = (
                "I could not find enough grounded evidence in this corpus to answer safely. "
                "Try a broader query or enable web fallback."
            )
            citations = []
        self._event(
            sink,
            query_id=query_id,
            pipeline=preset,
            sequence=sequence,
            stage="grounding",
            start=started,
            message="Validated citation coverage and applied the abstention policy.",
            payload={"confidence": confidence, "threshold": threshold, "abstained": abstained},
        )

        result = {
            "pipeline": preset,
            "answer": answer,
            "abstained": abstained,
            "confidence": confidence,
            "citations": citations,
            "hits": [item.as_dict(rank) for rank, item in enumerate(results[:6], start=1)],
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "cached": False,
            "query": {"original": question, "effective": retrieval_question, "expansions": expansions},
        }
        self._cache[cache_key] = result
        return result

    async def compare_stream(
        self,
        question: str,
        *,
        query_id: str,
        metadata: dict[str, str] | None = None,
        include_web_fallback: bool = False,
    ) -> AsyncIterator[TraceEvent | dict[str, Any]]:
        events: asyncio.Queue[TraceEvent] = asyncio.Queue()

        def sink(event: TraceEvent) -> None:
            events.put_nowait(event)

        async def run_pipeline(preset: Preset) -> dict[str, Any]:
            await asyncio.sleep(0)
            return await asyncio.to_thread(
                self.run,
                question,
                preset,
                query_id=query_id,
                metadata=metadata,
                sink=sink,
            )

        baseline_task = asyncio.create_task(run_pipeline(Preset.BASELINE))
        advanced_task = asyncio.create_task(run_pipeline(Preset.ADVANCED))
        while not (baseline_task.done() and advanced_task.done() and events.empty()):
            try:
                yield await asyncio.wait_for(events.get(), timeout=0.05)
            except TimeoutError:
                await asyncio.sleep(0)
        baseline, advanced = await asyncio.gather(baseline_task, advanced_task)
        if include_web_fallback and advanced["abstained"]:
            fallback_started = time.perf_counter()
            try:
                advanced["web_fallback"] = await wikipedia_search(rewrite_query(question))
                yield TraceEvent(
                    query_id=query_id,
                    pipeline=Preset.ADVANCED,
                    sequence=9,
                    stage="web_fallback",
                    status="completed",
                    elapsed_ms=round((time.perf_counter() - fallback_started) * 1000, 2),
                    message="Local confidence was low; searched Wikipedia using only the rewritten query.",
                    payload={"result_count": len(advanced["web_fallback"]), "egress": "query_only"},
                )
            except Exception as error:
                advanced["web_fallback"] = []
                yield TraceEvent(
                    query_id=query_id,
                    pipeline=Preset.ADVANCED,
                    sequence=9,
                    stage="web_fallback",
                    status="degraded",
                    elapsed_ms=round((time.perf_counter() - fallback_started) * 1000, 2),
                    message="Web fallback was unavailable; the local abstention remains in force.",
                    payload={"error": type(error).__name__},
                )
        yield {"type": "result", "query_id": query_id, "baseline": baseline, "advanced": advanced}

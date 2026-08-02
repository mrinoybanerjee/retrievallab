from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from retrievallab.evaluation import EvalCase, aggregate, ndcg_at_k, reciprocal_rank
from retrievallab.ingestion import IngestionError, ingest_pdf
from retrievallab.models import JobStatus, QueryAccepted, QueryRequest, TraceEvent
from retrievallab.pipeline import RetrievalEngine

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "demo"
ENGINE = RetrievalEngine(DATA / "corpus.json")
ENGINES: dict[str, RetrievalEngine] = {"demo": ENGINE}
CORPORA: dict[str, dict[str, Any]] = {
    "demo": {"id": "demo", "name": "RAG field guide", "documents": 1, "status": "indexed"}
}
QUERY_QUEUES: dict[str, asyncio.Queue[TraceEvent | dict[str, Any] | None]] = {}
QUERY_TASKS: dict[str, asyncio.Task[None]] = {}
MAX_ACTIVE_QUERIES = 4
QUERY_SEMAPHORE = asyncio.Semaphore(MAX_ACTIVE_QUERIES)

app = FastAPI(
    title="RetrievalLab API",
    version="0.1.0",
    description="Observable baseline-versus-advanced retrieval experiments.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in os.getenv("RETRIEVALLAB_CORS_ORIGINS", "http://localhost:3000").split(",")
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


def sse(data: dict[str, Any], *, event: str = "message", event_id: str | None = None) -> str:
    identifier = f"id: {event_id}\n" if event_id else ""
    return f"{identifier}event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


async def execute_query(query_id: str, request: QueryRequest) -> None:
    queue = QUERY_QUEUES[query_id]
    try:
        async with QUERY_SEMAPHORE:
            engine = ENGINES[request.corpus_id]
            async for event in engine.compare_stream(
                request.question,
                query_id=query_id,
                metadata=request.metadata,
                include_web_fallback=request.include_web_fallback,
            ):
                await queue.put(event)
    except asyncio.CancelledError:
        await queue.put({"type": "cancelled", "query_id": query_id})
        raise
    except Exception as error:  # pragma: no cover - last-resort API boundary
        await queue.put(
            {
                "type": "error",
                "query_id": query_id,
                "error": {
                    "code": "query_failed",
                    "message": "The retrieval experiment could not complete.",
                    "cause": str(error),
                    "fix": "Retry the query. If it repeats, check the API logs and corpus status.",
                },
            }
        )
    finally:
        await queue.put(None)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/readyz")
def readiness() -> dict[str, Any]:
    return {
        "status": "ready",
        "corpus": "demo",
        "chunks": len(ENGINE.all_chunks),
        "active_queries": sum(not task.done() for task in QUERY_TASKS.values()),
        "capacity": MAX_ACTIVE_QUERIES,
    }


@app.get("/api/v1/demo")
def demo() -> dict[str, Any]:
    corpus = json.loads((DATA / "corpus.json").read_text(encoding="utf-8"))
    return {
        "corpus": {
            "id": "demo",
            "title": corpus["title"],
            "description": corpus["description"],
            "documents": 1,
            "pages": len(corpus["pages"]),
            "chunks": len(ENGINE.all_chunks),
            "status": "indexed",
        },
        "suggested_questions": [
            "Why does hybrid search outperform dense retrieval alone?",
            "How should a RAG system decide when to abstain?",
            "What do MRR and NDCG measure?",
            "How does parent document retrieval preserve context?",
        ],
        "presets": {
            "baseline": ["384d local dense encoder", "top-6 retrieval", "extractive answer"],
            "advanced": [
                "query rewrite + expansion",
                "dense + BM25",
                "RRF fusion",
                "cross-feature rerank",
                "MaxSim late interaction",
                "grounding + abstention",
            ],
        },
    }


@app.post("/api/v1/query", response_model=QueryAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_query(request: QueryRequest) -> QueryAccepted:
    if request.corpus_id not in ENGINES:
        raise HTTPException(status_code=404, detail="Unknown corpus id.")
    query_id = uuid.uuid4().hex[:16]
    QUERY_QUEUES[query_id] = asyncio.Queue(maxsize=128)
    QUERY_TASKS[query_id] = asyncio.create_task(execute_query(query_id, request))
    return QueryAccepted(query_id=query_id, events_url=f"/api/v1/query/{query_id}/events")


@app.post("/api/v1/corpora", status_code=status.HTTP_201_CREATED)
def create_corpus(name: str = Form(min_length=1, max_length=80)) -> dict[str, Any]:
    corpus_id = uuid.uuid4().hex[:12]
    corpus = {"id": corpus_id, "name": name, "documents": 0, "status": "empty"}
    CORPORA[corpus_id] = corpus
    return corpus


@app.post("/api/v1/corpora/{corpus_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(corpus_id: str, file: UploadFile = File()) -> dict[str, Any]:
    corpus = CORPORA.get(corpus_id)
    if corpus is None:
        raise HTTPException(status_code=404, detail="Unknown corpus id.")
    payload = await file.read()
    try:
        ingested = ingest_pdf(payload, file.filename or "document.pdf")
    except IngestionError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": error.message, "fix": error.fix},
        ) from error
    existing = ENGINES[corpus_id].all_chunks if corpus_id in ENGINES else []
    ENGINES[corpus_id] = RetrievalEngine(chunks=[*existing, *ingested.chunks])
    corpus.update({"documents": corpus["documents"] + 1, "status": "indexed"})
    return {
        "corpus_id": corpus_id,
        "document_id": ingested.document_id,
        "filename": ingested.filename,
        "pages": ingested.page_count,
        "chunks": ingested.chunk_count,
        "status": "indexed",
    }


@app.get("/api/v1/query/{query_id}/events")
async def query_events(query_id: str, request: Request) -> StreamingResponse:
    queue = QUERY_QUEUES.get(query_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Unknown or expired query id.")

    async def stream() -> AsyncIterator[str]:
        while True:
            if await request.is_disconnected():
                break
            item = await queue.get()
            if item is None:
                yield sse({"query_id": query_id, "status": JobStatus.COMPLETED}, event="complete")
                break
            if isinstance(item, TraceEvent):
                yield sse(item.model_dump(mode="json"), event="trace", event_id=str(item.sequence))
            else:
                yield sse(item, event=item.get("type", "result"))

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/v1/query/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_query(query_id: str) -> None:
    task = QUERY_TASKS.get(query_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Unknown or expired query id.")
    if not task.done():
        task.cancel()


def load_eval_cases() -> list[EvalCase]:
    raw = json.loads((DATA / "golden.json").read_text(encoding="utf-8"))
    return [
        EvalCase(
            id=case["id"],
            question=case["question"],
            relevant_pages=frozenset(case["relevant_pages"]),
            should_abstain=case.get("should_abstain", False),
        )
        for case in raw["cases"]
    ]


@app.post("/api/v1/evaluations")
def run_evaluation() -> dict[str, Any]:
    cases = load_eval_cases()
    reports: dict[str, Any] = {}
    for preset in ("baseline", "advanced"):
        results = []
        latencies = []
        for case in cases:
            from retrievallab.models import Preset

            output = ENGINE.run(case.question, Preset(preset), query_id=f"eval-{case.id}")
            pages = [hit["page"] for hit in output["hits"]]
            relevant = set(case.relevant_pages)
            hit = bool(relevant & set(pages[:5])) if relevant else output["abstained"]
            results.append(
                {
                    "id": case.id,
                    "hit_at_5": float(hit),
                    "reciprocal_rank": reciprocal_rank(pages, relevant) if relevant else float(output["abstained"]),
                    "ndcg_at_10": ndcg_at_k(pages, relevant) if relevant else float(output["abstained"]),
                    "abstention_correct": float(output["abstained"] == case.should_abstain),
                }
            )
            latencies.append(output["latency_ms"])
        reports[preset] = {
            **aggregate(results),
            "cases": len(cases),
            "p50_latency_ms": round(sorted(latencies)[len(latencies) // 2], 2),
            "failures": [result["id"] for result in results if not result["hit_at_5"]][:8],
        }
    return {"suite": "demo-v1", "case_count": len(cases), "reports": reports}


@app.get("/api/v1/documents/demo/pages/{page}")
def document_page(page: int) -> dict[str, Any]:
    corpus = json.loads((DATA / "corpus.json").read_text(encoding="utf-8"))
    match = next((item for item in corpus["pages"] if item["page"] == page), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return match


@app.get("/api/v1/documents/demo.pdf")
def demo_pdf() -> FileResponse:
    pdf_path = DATA / "retrieval-handbook.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Demo PDF has not been generated. Run `uv run python scripts/build_demo_pdf.py`.",
        )
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)

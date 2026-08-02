from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Preset(StrEnum):
    BASELINE = "baseline"
    ADVANCED = "advanced"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    corpus_id: str = "demo"
    metadata: dict[str, str] = Field(default_factory=dict)
    include_web_fallback: bool = False


class QueryAccepted(BaseModel):
    query_id: str
    status: JobStatus = JobStatus.QUEUED
    events_url: str


class TraceEvent(BaseModel):
    schema_version: str = "1.0"
    query_id: str
    pipeline: Preset
    sequence: int
    stage: str
    status: str
    elapsed_ms: float
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    parent_id: str
    source: str
    page: int
    section: str
    text: str
    token_start: int
    token_end: int
    metadata: dict[str, str] = field(default_factory=dict)
    coordinates: tuple[float, float, float, float] | None = None


@dataclass(slots=True)
class ScoredChunk:
    chunk: Chunk
    dense_score: float = 0.0
    sparse_score: float = 0.0
    fusion_score: float = 0.0
    rerank_score: float = 0.0
    late_score: float = 0.0
    final_score: float = 0.0

    def as_dict(self, rank: int) -> dict[str, Any]:
        return {
            "rank": rank,
            "chunk_id": self.chunk.id,
            "parent_id": self.chunk.parent_id,
            "source": self.chunk.source,
            "page": self.chunk.page,
            "section": self.chunk.section,
            "text": self.chunk.text,
            "scores": {
                "dense": round(self.dense_score, 4),
                "sparse": round(self.sparse_score, 4),
                "fusion": round(self.fusion_score, 4),
                "rerank": round(self.rerank_score, 4),
                "late_interaction": round(self.late_score, 4),
                "final": round(self.final_score, 4),
            },
        }

# Architecture

```mermaid
flowchart LR
  UI[Next.js workbench] -->|POST query| API[FastAPI]
  API -->|SSE trace| UI
  API --> C[Page-aware chunks]
  C --> D[Dense index]
  C --> B[BM25 index]
  D --> R[Reciprocal-rank fusion]
  B --> R
  R --> X[Cross-feature or neural reranker]
  X --> M[MaxSim late interaction]
  M --> G[Grounding and confidence policy]
  G -->|supported| A[Answer + page citations]
  G -->|low confidence| W[Optional query-only web fallback]
  E[60-case evaluation suite] --> API
```

## Why this structure

The retrieval package has no dependency on FastAPI or React. It can be tested through direct function calls, exposed through the CLI, or used by the API. The API owns concurrency, job state, input boundaries, and event delivery. The dashboard consumes typed public contracts and includes an explicitly labelled replay mode so it remains presentable when the API is offline.

The first release uses direct in-memory repositories. There is no speculative vector database or queue abstraction; a second backend should exist before an interface is extracted.

## Observability boundary

Every pipeline stage emits a structured event after it completes. The elapsed time is measured from the pipeline start, so the frontend can render a truthful waterfall. Cache hits are explicit events. Errors are terminal unless the failure policy identifies a safe degraded path.

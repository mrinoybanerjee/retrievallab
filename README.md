<div align="center">

# RetrievalLab

**One question. Two RAG pipelines. Every retrieval decision exposed.**

[![CI](https://github.com/mrinoybanerjee/retrievallab/actions/workflows/ci.yml/badge.svg)](https://github.com/mrinoybanerjee/retrievallab/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-c9f36a.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-11120f.svg)](pyproject.toml)
[![Next.js](https://img.shields.io/badge/Next.js-16-11120f.svg)](apps/web)

</div>

![RetrievalLab experiment dashboard](docs/assets/dashboard.png)

RetrievalLab is a local-first workbench for understanding and evaluating retrieval-augmented generation. Upload a PDF or use the included corpus, ask a question, then watch a naive dense baseline and an advanced hybrid pipeline execute side by side.

This is not a chat UI wrapped around a vector database. It makes query rewriting, dense and sparse retrieval, rank fusion, reranking, token-level late interaction, grounding, abstention, caching, latency, and page citations inspectable.

## What you can explore

- Page-aware PDF extraction and citations with coordinate metadata.
- Dense + BM25 hybrid search with reciprocal-rank fusion.
- A real optional SentenceTransformers bi-encoder and CrossEncoder path.
- Zero-download deterministic models for a fast, reproducible demo.
- Query rewriting, bounded expansion, and hard metadata filters.
- Parent-page retrieval and token-level MaxSim late interaction.
- Citation grounding, confidence policy, adversarial abstention, and query-only web fallback.
- Sixty golden cases with hit rate, MRR, NDCG@10, abstention accuracy, and latency.
- A live SSE pipeline trace and evidence drawer built for explanation, not decoration.

## Quick start

### Docker

```bash
git clone https://github.com/mrinoybanerjee/retrievallab.git
cd retrievallab
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). The API and OpenAPI docs run at [http://localhost:8000/docs](http://localhost:8000/docs).

### Native development

```bash
uv sync --extra dev
uv run python scripts/build_demo_pdf.py
uv run uvicorn services.api.app.main:app --reload
```

In a second terminal:

```bash
cd apps/web
pnpm install --ignore-scripts
pnpm dev
```

No API key is required. If the API is not running, the interface clearly switches to a bundled trace replay rather than pretending to execute a live query.

## Turn on neural models

The default preset uses an inspectable 384-dimensional feature-hash encoder and cross-feature reranker so interviewers can run it immediately. The neural path is implemented but lazy-loaded:

```bash
uv sync --extra models
export RETRIEVALLAB_DENSE_MODEL=sentence-transformers/all-MiniLM-L6-v2
export RETRIEVALLAB_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

The first run downloads model weights. RetrievalLab exposes the active model name in trace payloads so benchmark reports cannot confuse local and neural presets.

## Pipeline

```text
question
  ├─ baseline: dense top-12 ───────────────────────────┐
  └─ advanced: rewrite → dense + BM25 → RRF → rerank  │
                    → MaxSim → parent context ─────────┤
                                                       ↓
                                    grounding → answer or abstain
                                                       ↓
                                           page-level citations
```

Read the [architecture](docs/ARCHITECTURE.md), [implementation contract](docs/IMPLEMENTATION_SPEC.md), and [evaluation protocol](docs/EVALUATION.md).

## Honest benchmark

`demo-v1` is small enough to run on every pull request and difficult enough to expose retrieval and abstention failures. It contains 48 answerable variants and 12 unsupported questions. Run it through the dashboard or API:

```bash
curl -X POST http://localhost:8000/api/v1/evaluations | jq
uv run python scripts/run_benchmark.py
```

The repository includes generated benchmark output under `data/benchmarks/`. Latency from shared CI runners is informational; correctness metrics are the regression gate.

| Metric | Naive dense | Advanced | Delta |
|---|---:|---:|---:|
| Hit rate @5 | 88.3% | **96.7%** | +8.3 pts |
| MRR | 73.9% | **94.3%** | +20.4 pts |
| NDCG @10 | 78.0% | **94.9%** | +16.9 pts |
| Abstention accuracy | 90.0% | **98.3%** | +8.3 pts |
| Local p50 latency | 2.94 ms | 4.75 ms | +1.81 ms |

These results are from the committed deterministic local preset and 12-page demo corpus. They demonstrate the evaluation machinery, not a general claim about every RAG workload. Two advanced cases remain in the failure report for inspection.

## Engineering choices worth discussing in an interview

1. **Why RRF instead of score normalization?** Dense cosine and BM25 scores are not naturally comparable; rank fusion stays stable without corpus-specific calibration.
2. **Why a deterministic default?** Reproducibility and five-minute setup are more useful for reviewers than silently downloading a model. The neural upgrade remains a first-class implementation.
3. **Why SSE instead of WebSockets?** Query progress is server-to-client, ordered, and short-lived. SSE provides the necessary semantics through ordinary HTTP infrastructure.
4. **Why abstain?** A RAG system that always answers turns retrieval misses into plausible hallucinations. Twelve adversarial cases measure the refusal boundary explicitly.
5. **Why no vector database?** The demo corpus does not need one. The project keeps the algorithm visible and adds infrastructure only when scale measurements justify it.

## Project layout

```text
apps/web/                    Next.js dashboard
services/api/                FastAPI job and SSE boundary
packages/retrieval/          retrieval, grounding, ingestion, evaluation
data/demo/                   original corpus and 60 golden cases
docs/                        architecture and methodology
tests/                       unit and API integration tests
```

## Privacy

Local PDF text stays in process memory. Remote providers are off by default. When web fallback is explicitly enabled, only the rewritten query is sent to Wikipedia; uploaded text and retrieved passages are never included. See [SECURITY.md](SECURITY.md) for limits and reporting.

## Contributing

Issues and focused pull requests are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the labelled good-first-issue ideas. Retrieval changes should include a golden case or explain why evaluation is unaffected.

Built by [Mrinoy Banerjee](https://github.com/mrinoybanerjee) as an open, inspectable study of retrieval quality.

# RetrievalLab v0.1 Implementation Contract

This document turns the reviewed product design into testable engineering constraints.

## Reference environment and budgets

- Reference environment: commodity laptop CPU, zero-download local preset.
- Upload limit: 20 MB, 200 pages, PDF text layer required.
- Child chunks: 500 tokens with 50-token overlap for uploaded documents.
- Demo corpus: page-aware 500-token child cap with 50-token overlap; each short demo page produces one child.
- Dense retrieval: top 12; sparse retrieval: top 12; RRF constant: 60.
- Reranking: fused top 10; late-interaction MaxSim: top 6.
- Context: top 3 grounded sentences with page citations.
- Active query jobs: 4; event queue: 128 entries per query.
- Warm local preset target: p95 query under 750 ms on the reference laptop.
- Cold neural preset target: model download and load progress is informational, not part of the warm-query SLO.

## Presets

| Stage | Baseline | Advanced |
|---|---|---|
| Query rewrite/expansion | Off | Bounded heuristic expansion |
| Dense | 384d feature-hash encoder | Same by default; optional MiniLM neural encoder |
| Sparse | Off | BM25, k1 1.5, b 0.75 |
| Fusion | Off | Reciprocal-rank fusion, k 60 |
| Rerank | Off | Local cross-feature scorer; optional MS MARCO MiniLM CrossEncoder |
| Late interaction | Off | Transparent token-level MaxSim over top 6 |
| Grounding | Extractive | Extractive + citation coverage |
| Abstention | Threshold 0.26 | Threshold 0.31 |

The UI always names the active model. It must never label the zero-download cross-feature scorer as a neural cross-encoder.

## Query state machine

```text
queued -> running -> completed
                   -> failed
                   -> cancelled
```

`POST /api/v1/query` is not idempotent and returns `202` plus a generated query ID. `DELETE` is idempotent after a known query is terminal. Event streams are ordered within each pipeline by `sequence`; the final `result` event contains both completed pipeline outputs, followed by terminal `complete`.

## Trace envelope

Every trace contains schema version, query ID, pipeline ID, monotonic stage sequence, stage name, status, elapsed milliseconds, human-readable message, and a safe structured payload. Payloads never contain credentials or complete uploaded documents.

## Failure policy

| Failure | Policy | User-visible result |
|---|---|---|
| Invalid, encrypted, scanned, oversized PDF | Reject | Problem, cause, and corrective action |
| Metadata removes all chunks | Abstain | Explain that scope produced zero candidates |
| Optional neural dense model fails | Degrade | Use the local dense encoder and mark the trace payload |
| Optional reranker fails | Degrade | Use the local cross-feature order and mark the trace payload |
| Web fallback fails | Degrade | Preserve local abstention |
| Client disconnects | Cancel stream only | Query may finish and expire in memory |

## Data lifecycle and trust boundaries

- Demo data is committed and immutable.
- Uploaded bytes are parsed in memory in v0.1; only generated chunk objects remain for the process lifetime.
- Restarting the API deletes uploaded corpora and query state.
- Only an explicitly enabled remote dense/reranker model may download model files.
- Remote generation is not enabled in v0.1.
- Wikipedia fallback receives only the rewritten query, never uploaded text or retrieved passages.
- CORS defaults to `http://localhost:3000` and does not allow credentials.

## Verification matrix

| Flow | Unit | Integration | Browser/E2E | Evaluation |
|---|---:|---:|---:|---:|
| PDF validation and page metadata | Yes | Yes | Upload state | N/A |
| Dense, BM25, RRF, rerank, MaxSim | Yes | Yes | Live trace | 48 positive cases |
| Citation page correctness | Yes | Yes | Evidence drawer | 48 positive cases |
| Abstention | Yes | Yes | Empty evidence state | 12 adversarial cases |
| Cache isolation | Yes | N/A | Cache label | N/A |
| SSE ordering and terminal result | N/A | Yes | Live update | N/A |
| Keyboard, contrast, reduced motion | N/A | N/A | Playwright + accessibility inspection | N/A |
| Baseline vs advanced metrics | Yes | Yes | Evaluation studio | 60 cases |

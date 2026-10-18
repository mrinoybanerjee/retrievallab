# Evaluation Protocol

RetrievalLab has two separate evaluation contracts. `demo-v1` guards the product
workbench. Phase 0 tests a research hypothesis. Their metrics and claims must not be
mixed.

The `demo-v1` suite contains exactly 60 versioned cases:

- 48 answerable questions, four for each source page.
- 12 plausible but unsupported questions that should abstain.

The corpus, configurations, metric code, and cases are committed to the repository. The local preset is deterministic and uses no random seed. Optional neural presets must record the full model identifier and revision in exported reports.

## Metrics

The historical `demo-v1.json` aggregates all 60 cases. For unsupported cases,
correct abstention contributes 1 to hit rate, MRR, and NDCG; an incorrect answer
contributes 0. These fields are mixed suite scores. The retrieval definitions
below apply to answerable cases.

- **Hit rate @5:** `1` when any relevant page appears in the first five results.
- **MRR:** reciprocal rank of the first relevant page, or zero.
- **NDCG @10:** binary relevance gain discounted by rank and normalized by the ideal ordering.
- **Abstention accuracy:** answer/refusal matches the golden `should_abstain` label.
- **Latency:** p50 shown for local exploration only. Shared CI latency is informational and not a regression gate.

Correctness regression gate: no metric may fall by more than 0.02 from the committed `data/benchmarks/demo-v1.json`. CI executes this comparison. A new model or corpus requires a new suite version rather than silently replacing results.

## Historical mixed-suite result

| Pipeline | Hit @5 | MRR | NDCG @10 | Abstention accuracy | p50 |
|---|---:|---:|---:|---:|---:|
| Naive dense | 88.3% | 73.9% | 78.0% | 90.0% | 2.94 ms |
| Advanced | 96.7% | 94.3% | 94.9% | 98.3% | 4.75 ms |

Two advanced cases remain visible as failures: `citation-1` and `ops-4`. The project deliberately commits those misses instead of tuning the golden set around the implementation.

## Separate retrieval and abstention cohorts

`data/benchmarks/demo-v1-cohorts.json` reports the same local pipeline with separate
denominators. It includes every case result, corpus and golden-set SHA-256 receipts,
and the local encoder/reranker configuration. It does not replace the historical
artifact or change the API, dashboard, or existing regression gate.

| Cohort metric | Naive dense | Advanced |
|---|---:|---:|
| Hit @5, 48 answerable cases | 85.42% | 95.83% |
| MRR, 48 answerable cases | 67.43% | 92.88% |
| NDCG @10, 48 answerable cases | 72.53% | 93.61% |
| False abstentions, 48 answerable cases | 6 | 1 |
| Correct abstentions, 12 unsupported cases | 12/12 | 12/12 |

Retrieval metrics use ranked pages even if the answer stage abstains. The separate
false-abstention count shows that answer behavior. These are synthetic regression
measurements, not answer-quality judgments or evidence of real-user outcomes.

Reproduce with the native environment from the README:

```bash
uv run python scripts/run_demo_cohorts.py --output /tmp/demo-v1-cohorts.json
```

The script rejects nonlocal model settings. It makes no web-fallback requests and
reports no latency, avoiding comparisons between unlike machines.

## Phase 0 complete-before-partial protocol

The research suite asks whether a known complete document ranks before every known
partial document within the first ten results. The headline metric is binary per
case and is paired across methods. Reports also include recall@10, top-1 logical
violations, pairwise complete-over-partial accuracy, first-complete rank, p50/p95
CPU wall time, postings touched, score updates, tuple assembly, index bytes, and CPU
milliseconds per success.

Controls are monolithic BM25, feature-hash dense, hybrid RRF, BM25-AND, additive,
minimum, product, harmonic, and exact distinct-passage support. Labels are used only
after ranking. The candidate uses a fixed 0.35 evidence threshold; it was not tuned
on MultiConIR.

Statistical reports use paired bootstrap intervals and exact paired sign tests with
Holm correction across controls. Machine-specific micro-latency is descriptive,
not a scale or cloud-cost claim.

### Pinned external result

| Method | Complete before partial @10 | Top-1 violation | p50 CPU | Mean postings |
|---|---:|---:|---:|---:|
| Feature-hash dense | 36.93% | 63.07% | 0.379 ms | 0 |
| Hybrid RRF | 44.19% | 55.81% | 0.503 ms | 346.61 |
| Monolithic BM25 | **68.81%** | **31.19%** | **0.150 ms** | **346.61** |
| Coverage-first | 60.46% | 39.54% | 0.390 ms | 770.07 |

The external source is MultiConIR Task 2 at commit
`9884fb3e1e5c06c9e026aa0042a679412dad1425`. The adapter uses paired structured
`Query10` conditions as oracle decomposition. It covers 2,299 of 2,307 rows and
records all eight skips. The committed artifact contains ten example cases plus
full aggregate metrics; raw source data is not vendored.

The candidate's paired delta against BM25 is −8.35 points, 95% bootstrap CI
[−9.83, −6.83], with 5,000 resamples. The candidate is rejected. Synthetic success
cannot override this external result.

### Claim boundary

Allowed: results on the exact committed synthetic artifact or pinned MultiConIR
subset, with their provenance. Not allowed: state of the art, production economics,
publication readiness, generalization, or a first-ever claim. The full gate in the
[research plan](FRONTIER_RETRIEVAL_RESEARCH_PLAN.md) requires a second external
family, parser robustness, ordinary-retrieval regression, and scale economics.

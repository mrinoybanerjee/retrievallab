# Evaluation Protocol

The `demo-v1` suite contains exactly 60 versioned cases:

- 48 answerable questions, four for each source page.
- 12 plausible but unsupported questions that should abstain.

The corpus, configurations, metric code, and cases are committed to the repository. The local preset is deterministic and uses no random seed. Optional neural presets must record the full model identifier and revision in exported reports.

## Metrics

- **Hit rate @5:** `1` when any relevant page appears in the first five results.
- **MRR:** reciprocal rank of the first relevant page, or zero.
- **NDCG @10:** binary relevance gain discounted by rank and normalized by the ideal ordering.
- **Abstention accuracy:** answer/refusal matches the golden `should_abstain` label.
- **Latency:** p50 shown for local exploration only. Shared CI latency is informational and not a regression gate.

Correctness regression gate: no metric may fall by more than 0.02 from the committed `data/benchmarks/demo-v1.json`. CI executes this comparison. A new model or corpus requires a new suite version rather than silently replacing results.

## Committed local result

| Pipeline | Hit @5 | MRR | NDCG @10 | Abstention accuracy | p50 |
|---|---:|---:|---:|---:|---:|
| Naive dense | 88.3% | 73.9% | 78.0% | 90.0% | 2.94 ms |
| Advanced | 96.7% | 94.3% | 94.9% | 98.3% | 4.75 ms |

Two advanced cases remain visible as failures: `citation-1` and `ops-4`. The project deliberately commits those misses instead of tuning the golden set around the implementation.

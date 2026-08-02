# Frontier Retrieval Research Plan

Status: Phase 0 implemented; first candidate rejected on external evidence; execution-layer research remains open.

## Phase 0 result — 2026-08-02

The zero-training falsification harness is now implemented with ten methods, paired
statistics, perturbations, sparse work counters, an interactive dashboard, and a
pinned MultiConIR adapter.

- Synthetic diagnostic: coverage-first reaches 100% complete-before-partial, but
  an additive control also reaches 100%. The scoring formula is not a contribution.
- External MultiConIR Task 2 subset: 2,299 of 2,307 source rows are evaluated using
  benchmark-provided `Query10` structure. BM25 reaches 68.81%; coverage-first
  reaches 60.46%.
- Candidate delta: −8.35 points, paired-bootstrap 95% CI [−9.83, −6.83], 5,000
  resamples. The candidate is rejected.
- Economics: the anchor assembles 1.93 condition tuples, but the implementation
  touches 2.22x BM25 postings and takes 2.60x BM25 p50 CPU time. No Pareto
  improvement is observed.

The result follows the stop rule below. Phase 1 model training is **not authorized
by the evidence**. The remaining research question is whether coordinated sparse
traversal can avoid materializing every condition list while preserving BM25's
quality—not whether another score aggregation formula can win.

## Decision

RetrievalLab will not treat Counterweight or Counterweight-Compile as its research
headline. The strongest current research target is:

> **Scalable first-stage retrieval that ranks complete evidence ahead of topically
> similar partial matches for multi-condition queries, while retaining ordinary
> retrieval quality and CPU-grade serving economics.**

This locks one problem, not an architecture. The proposed method family will be
abandoned if a simple lexical or algebraic baseline solves the problem at the same
cost.

The evidence and collision audit supporting this decision are in
[`FINAL_RESEARCH_AUDIT_2026-08-02.md`](./FINAL_RESEARCH_AUDIT_2026-08-02.md).

## Why this problem

Modern retrieval optimizes a scalar similarity score. For a query requiring
conditions `A AND B AND NOT C`, strong support for `A` can compensate for missing
`B` or violating `C`. A reranker cannot repair the failure if the complete document
never enters its candidate set.

Recent independent results localize this failure:

- [LIMIT+](https://arxiv.org/abs/2605.03824) reports that the strongest QUEST
  neural method falls from roughly 0.42 Recall@100 to below 0.02 on a controlled
  constraint benchmark, while lexical retrieval is much more stable.
- [MultiConIR](https://aclanthology.org/2025.findings-emnlp.726/) finds degradation,
  non-monotonic rankings, and sensitivity to condition order across five domains.
- [CrossPage / n-Clue](https://arxiv.org/abs/2607.24165) finds that its strongest
  displayed hybrid retrieves a complete long document for 81.1% of queries but
  ranks one before known partial matches for only 35.8%.
- [SSRB](https://papers.nips.cc/paper_files/paper/2025/hash/631bbd89466337712564872840a401be-Abstract-Datasets_and_Benchmarks_Track.html)
  exposes the same exact-plus-semantic constraint problem over 14 million
  semi-structured objects and 99 schemas.

These results make first-stage condition coverage a real bottleneck. They do not
prove that the method below will solve it.

## What is already occupied

The project must not claim novelty for any of these ideas alone:

- Counterfactual query controls or requirement-violating negatives:
  [CF-RAG](https://openreview.net/forum?id=9U51rOnGko) and
  [CausalNeg](https://arxiv.org/abs/2606.01304).
- Sparse AND/OR/NOT composition, signed sparse weights, or conjunction
  pseudo-features: [Set-Comp LSR](https://arxiv.org/abs/2501.07679).
- Logic-aware contrastive learning or fuzzy operators over dense embeddings:
  [LogiCoL](https://aclanthology.org/2025.emnlp-main.608/) and
  [NSFL](https://arxiv.org/abs/2604.10604).
- Generic coverage-aware representation learning:
  [CoveR](https://arxiv.org/abs/2605.28522).
- Query decomposition by itself:
  [stage-aware decomposition](https://arxiv.org/abs/2606.08577) and the
  condition-wise controls in CrossPage.
- A new sparse architecture without a constraint-specific contribution:
  [LACONIC](https://arxiv.org/abs/2601.01684),
  [LightRetriever](https://arxiv.org/abs/2505.12260), and
  [ColBERTSaR](https://arxiv.org/abs/2606.05568).

## Open research question

The candidate question is narrower than all of the above:

> Can a sparse index execute a structured, non-compensatory multi-condition query
> as one coordinated first-stage retrieval plan, with complete-before-partial
> quality approaching expensive verification systems but latency and cost close to
> ordinary inverted-index search?

The potential contribution is the conjunction of four requirements:

1. Natural-language conditions remain separately addressable through retrieval.
2. Missing a required condition cannot be hidden by a very strong topical match.
3. Candidate generation is performed directly over a sparse index, not by an
   expensive reranker over a large pool.
4. The full online path is measured on CPU, including parsing, list traversal, and
   result assembly.

No claim of first-of-its-kind work is justified until a deeper scholarly and patent
review covers the final algorithm, not merely this problem statement.

## Phase 0: cheapest decisive test

Do not train a new model first. Reuse frozen public representations and benchmark-
provided condition decompositions to test whether a new method is necessary.

1. Produce monolithic BM25 and SPLADE runs.
2. Produce one ranked list per atomic condition using the same index.
3. Compare additive fusion, Boolean AND, Set-Comp algebra, min, product, harmonic
   mean, and distinct-support assignment.
4. Add shuffled-operator, shuffled-condition, duplicate-condition, and removed-
   condition controls.
5. Evaluate oracle decomposition, deterministic parser output, and deliberately
   corrupted parses separately.
6. Measure query encoding, postings touched, documents scored, p50/p95/p99 latency,
   peak memory, and index bytes—not just ranking metrics.
7. Run the same analysis on at least two structurally different constraint suites
   and an ordinary retrieval suite.

This experiment distinguishes three possibilities:

- Simple lexical structure is sufficient: ship the benchmark and stop inventing a
  model.
- Non-compensatory scoring helps but is too slow: investigate a new pruning/index
  algorithm.
- A reliable residual remains after strong controls: only then train a sparse
  coverage-aware student.

## Evaluation suites

The first gate uses public, versioned artifacts where licenses permit:

- Controlled set logic: LIMIT+ and QUEST.
- Natural multi-condition ranking: MultiConIR.
- Long-document complete-before-partial retrieval: CrossPage / n-Clue when its
  released artifacts are available and license-compatible.
- Mixed exact and semantic constraints at scale: an SSRB subset, followed by the
  full benchmark only after the small gate passes.
- Ordinary retrieval regression: a preregistered BEIR subset.
- Negation stress tests: NevIR and the negation taxonomy's released suites.

Synthetic and LLM-generated datasets are diagnostic instruments, not sole evidence
of generalization. A positive paper result requires transfer to natural or human-
judged queries.

## Required baselines

1. BM25-OR and BM25-AND.
2. Monolithic SPLADE and Set-Comp LSR.
3. A strong current single-vector dense retriever.
4. Condition-wise dense retrieval with min, product, and harmonic aggregation.
5. Dense plus BM25 fusion.
6. A public cross-encoder and an instruction-tuned pointwise reranker.
7. NSFL where its public implementation and task format permit faithful use.
8. CoveR on coverage-oriented tasks.
9. A cost-aware cascade as the strongest production-style comparator.
10. Randomized structure and matched-compute ablations.

The current RetrievalLab demo systems are product smoke tests, not scientific
baselines.

## Metrics

### Capability

- Complete-before-partial success at 10 and 100.
- Recall@10 and Recall@100 for all-condition golds.
- Logical violation rate and pairwise gold-versus-subset accuracy.
- Relevance monotonicity as conditions are added or removed.
- Robustness to paraphrase, condition order, and compositional depth.
- Ordinary BEIR NDCG@10 regression.

### Systems and economics

- End-to-end cold and warm p50/p95/p99 latency.
- Throughput at concurrency 1, 4, and 16.
- CPU time, accelerator time, peak RSS, and accelerator memory.
- Postings touched, candidates scored, and retrieval/reranker/LLM calls.
- Index bytes per document, build time, and incremental update cost.
- Measured energy where available and timestamped modeled cloud cost.
- Cost per successful complete-before-partial retrieval.
- Quality/cost and quality/p95-latency Pareto frontiers.

Offline parsing, teacher calls, training, and indexing are amortized and reported.

## Preregistered Phase 0 gate

Proceed to a new learned sparse model or index only if a structure-aware candidate
generator satisfies every condition below on held-out data:

1. At least +5 absolute complete-before-partial points over the strongest matched-
   compute monolithic or algebraic sparse baseline on two distinct benchmark
   families.
2. The result remains positive under paraphrase, condition reordering, and parser
   noise; oracle decomposition is not the only winning condition.
3. No more than 1 aggregate NDCG@10 point of ordinary-suite regression.
4. At least 5x lower p95 latency than a matched hybrid-plus-cross-encoder pipeline,
   or at least 30% lower modeled serving cost at matched complete-before-partial
   quality within 1 point.
5. The online default uses no hosted LLM and no full-corpus dense fan-out per
   condition.
6. Paired bootstrap intervals and multiplicity-corrected tests support the headline
   comparisons.

Stop or reframe if BM25-AND, Set-Comp, or a basic multi-list aggregation matches the
gain; the result appears only on explicit templates; parsing destroys it; index
growth erases cost savings; or a new paper/patent covers the final mechanism.

## Phase 1 candidate method family

Only after Phase 0 passes, investigate a **constraint-preserving sparse candidate
generator** with three separable components:

1. A query compiler that emits atomic conditions and AND/OR/NOT structure.
2. Sparse page or passage evidence features that preserve semantic matching while
   remaining indexable.
3. A coordinated top-k traversal with safe or measured approximate bounds for a
   non-compensatory coverage score.

Possible training signals include partial-match ladders, relevance monotonicity,
truth-table consistency, and CausalNeg-style requirement violations. They are
baselines or ingredients, not novelty claims. Parser, representation, scoring, and
execution improvements must be ablated independently.

## Dashboard and open-source outcome

The public dashboard should show evidence, not a predetermined win:

- Three synchronized systems: naive dense, strong production-style hybrid, and the
  research candidate.
- A condition editor and live partial-match failure visualization.
- A corpus-size/distractor slider backed only by measured nested artifacts.
- Complete-before-partial quality, p95 latency, throughput, memory, index size, and
  cost above the fold.
- Query-plan, postings, and weakest-condition traces.
- Pareto charts and cost waterfalls separating offline and online work.
- Measured, estimated, reproduced, and unavailable badges.
- Reproducible manifests, raw runs, confidence intervals, failure cases, and
  negative results.

The third system enters the polished dashboard only after its artifacts pass the
gate. Until then, the dashboard labels it as an experiment.

## Publication standard

A credible paper needs all four contributions below:

1. A clearly isolated failure not captured by ordinary recall alone.
2. A method or execution algorithm that is not explained by existing Boolean,
   algebraic, fuzzy-logic, or coverage-training baselines.
3. Transfer across controlled and natural benchmarks at realistic corpus scale.
4. A reproducible Pareto improvement in quality, latency, and total cost.

This plan creates a path to a strong retrieval paper. It does not guarantee a
breakthrough, state of the art, acceptance, or publication.

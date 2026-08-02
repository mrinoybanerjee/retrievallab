import type { ComparisonResult, EvaluationResult, PipelineResult, TraceEvent } from "./types";

export const DEMO = {
  corpus: { chunks: 12 },
  suggested_questions: [
    "Why does hybrid search outperform dense retrieval alone?",
    "How should a RAG system decide when to abstain?",
    "What do MRR and NDCG measure?",
    "How does parent document retrieval preserve context?",
  ],
};

const baseline: PipelineResult = {
  pipeline: "baseline",
  answer: "Dense retrieval encodes queries and passages into vectors and ranks them by geometric similarity. [1] Neither signal dominates every query. [2]",
  abstained: false,
  confidence: 0.58,
  latency_ms: 42.8,
  cached: false,
  citations: [
    { id: 1, source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", quote: "Dense retrieval encodes queries and passages into vectors and ranks them by geometric similarity.", score: 0.58 },
    { id: 2, source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", quote: "Neither signal dominates every query.", score: 0.51 },
  ],
  hits: [
    { rank: 1, chunk_id: "p2-c0", parent_id: "p2", source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", text: "Dense retrieval encodes queries and passages into vectors and ranks them by geometric similarity. Sparse retrieval such as BM25 rewards exact terms, rare words, identifiers, and numbers.", scores: { dense: 0.58, sparse: 0, fusion: 0, rerank: 0, late_interaction: 0, final: 0.58 } },
    { rank: 2, chunk_id: "p10-c0", parent_id: "p10", source: "The Observable RAG Field Guide", page: 10, section: "Late interaction", text: "Late-interaction retrieval stores token-level document representations instead of compressing an entire passage into one vector.", scores: { dense: 0.41, sparse: 0, fusion: 0, rerank: 0, late_interaction: 0, final: 0.41 } },
  ],
};

const advanced: PipelineResult = {
  pipeline: "advanced",
  answer: "Dense retrieval connects paraphrases, while sparse BM25 protects exact terms, identifiers, and numbers. [1] Reciprocal rank fusion combines both ranked lists without assuming their raw scores are comparable. [2] That makes hybrid retrieval stronger across mixed query types rather than universally favoring one signal. [3]",
  abstained: false,
  confidence: 0.91,
  latency_ms: 86.4,
  cached: false,
  query: { original: DEMO.suggested_questions[0], effective: "why does hybrid search outperform dense semantic embedding vector retrieval alone fusion sparse lexical bm25", expansions: ["semantic", "embedding", "vector", "fusion", "sparse"] },
  citations: [
    { id: 1, source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", quote: "Dense retrieval can connect paraphrases and concepts that do not share exact words. Sparse retrieval such as BM25 rewards exact terms, rare words, identifiers, and numbers.", score: 0.93 },
    { id: 2, source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", quote: "Reciprocal rank fusion is a practical method because it depends on rank positions instead of incomparable raw scores.", score: 0.89 },
    { id: 3, source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", quote: "Neither signal dominates every query. Hybrid search retrieves from both indexes and combines ranked lists.", score: 0.86 },
  ],
  hits: [
    { rank: 1, chunk_id: "p2-c0", parent_id: "p2", source: "The Observable RAG Field Guide", page: 2, section: "Dense and sparse retrieval", text: "Dense retrieval encodes queries and passages into vectors and ranks them by geometric similarity. Sparse retrieval such as BM25 rewards exact terms, rare words, identifiers, and numbers. Neither signal dominates every query.", scores: { dense: 0.61, sparse: 4.18, fusion: 0.0328, rerank: 0.91, late_interaction: 0.88, final: 0.93 } },
    { rank: 2, chunk_id: "p4-c0", parent_id: "p4", source: "The Observable RAG Field Guide", page: 4, section: "Retrieve then rerank", text: "First-stage retrieval must be fast enough to examine the full corpus. A reranker examines only the best candidates.", scores: { dense: 0.45, sparse: 1.72, fusion: 0.0315, rerank: 0.62, late_interaction: 0.67, final: 0.69 } },
    { rank: 3, chunk_id: "p9-c0", parent_id: "p9", source: "The Observable RAG Field Guide", page: 9, section: "Query rewriting and expansion", text: "Query rewriting converts shorthand or ambiguous language into an explicit retrieval query.", scores: { dense: 0.38, sparse: 1.31, fusion: 0.0298, rerank: 0.48, late_interaction: 0.55, final: 0.57 } },
  ],
};

export const FALLBACK_COMPARISON: ComparisonResult = { mode: "replay", query_id: "demo-replay", baseline, advanced };

export const FALLBACK_TRACES: TraceEvent[] = [
  { schema_version: "1.0", query_id: "demo", pipeline: "baseline", sequence: 1, stage: "scope", status: "completed", elapsed_ms: 2.1, message: "Scoped the corpus to 12 page-aware chunks.", payload: {} },
  { schema_version: "1.0", query_id: "demo", pipeline: "baseline", sequence: 2, stage: "dense_retrieval", status: "completed", elapsed_ms: 22.4, message: "Encoded the query and ranked dense candidates.", payload: {} },
  { schema_version: "1.0", query_id: "demo", pipeline: "advanced", sequence: 2, stage: "rewrite", status: "completed", elapsed_ms: 4.2, message: "Rewrote ambiguity and added bounded expansion terms.", payload: {} },
  { schema_version: "1.0", query_id: "demo", pipeline: "advanced", sequence: 5, stage: "fusion", status: "completed", elapsed_ms: 38.7, message: "Fused both ranked lists with reciprocal-rank fusion.", payload: {} },
  { schema_version: "1.0", query_id: "demo", pipeline: "advanced", sequence: 6, stage: "rerank", status: "completed", elapsed_ms: 61.9, message: "Reranked the fused top 10.", payload: {} },
  { schema_version: "1.0", query_id: "demo", pipeline: "advanced", sequence: 8, stage: "grounding", status: "completed", elapsed_ms: 86.4, message: "Validated citation coverage and applied the abstention policy.", payload: {} },
];

export const FALLBACK_EVALUATION: EvaluationResult = {
  mode: "replay",
  suite: "demo-v1",
  case_count: 60,
  reports: {
    baseline: { hit_rate_at_5: 0.8833, mrr: 0.7394, ndcg_at_10: 0.7802, abstention_accuracy: 0.9, cases: 60, p50_latency_ms: 2.94, failures: ["chunking-4", "citation-1", "eval-3", "abstain-2", "cache-4", "rewrite-3", "ops-4"] },
    advanced: { hit_rate_at_5: 0.9667, mrr: 0.9431, ndcg_at_10: 0.9488, abstention_accuracy: 0.9833, cases: 60, p50_latency_ms: 4.75, failures: ["citation-1", "ops-4"] },
  },
};

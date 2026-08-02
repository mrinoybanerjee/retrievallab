export type Pipeline = "baseline" | "advanced";

export interface ActiveCorpus {
  id: string;
  name: string;
  pages: number;
  chunks: number;
}

export interface TraceEvent {
  schema_version: string;
  query_id: string;
  pipeline: Pipeline;
  sequence: number;
  stage: string;
  status: string;
  elapsed_ms: number;
  message: string;
  payload: Record<string, unknown>;
}

export interface Citation {
  id: number;
  source: string;
  page: number;
  section: string;
  quote: string;
  score: number;
  coordinates?: [number, number, number, number] | null;
}

export interface RetrievalHit {
  rank: number;
  chunk_id: string;
  parent_id: string;
  source: string;
  page: number;
  section: string;
  text: string;
  scores: {
    dense: number;
    sparse: number;
    fusion: number;
    rerank: number;
    late_interaction: number;
    final: number;
  };
}

export interface PipelineResult {
  pipeline: Pipeline;
  answer: string;
  abstained: boolean;
  confidence: number;
  citations: Citation[];
  hits: RetrievalHit[];
  latency_ms: number;
  cached: boolean;
  query?: { original: string; effective: string; expansions: string[] };
}

export interface ComparisonResult {
  mode: "live" | "replay";
  query_id: string;
  baseline: PipelineResult;
  advanced: PipelineResult;
}

export interface EvaluationMetrics {
  hit_rate_at_5: number;
  mrr: number;
  ndcg_at_10: number;
  abstention_accuracy: number;
  cases: number;
  p50_latency_ms: number;
  failures: string[];
}

export interface EvaluationResult {
  mode: "live" | "replay";
  suite: string;
  case_count: number;
  reports: { baseline: EvaluationMetrics; advanced: EvaluationMetrics };
}

export type PhaseZeroMethod =
  | "dense"
  | "bm25"
  | "hybrid"
  | "bm25_and"
  | "additive"
  | "minimum"
  | "product"
  | "harmonic"
  | "distinct_support"
  | "coverage_first";

export type PhaseZeroHeadlineMethod = "dense" | "hybrid" | "coverage_first";
export type PhaseZeroSource = "external" | "synthetic";

export interface PhaseZeroMethodReport {
  label: string;
  family: string;
  status: string;
  complete_before_partial_at_10: number;
  recall_at_10: number;
  logical_violation_at_1: number;
  pairwise_complete_over_partial: number;
  mean_first_complete_rank: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  mean_postings_touched: number;
  mean_score_updates: number;
  mean_documents_scored: number;
  cpu_ms_per_success: number | null;
}

export interface PhaseZeroConstraint {
  id: string;
  text: string;
  aliases: string[];
}

export interface PhaseZeroDocument {
  id: string;
  title: string;
  passages: string[];
  truth: "complete" | "partial";
  ranks: Record<PhaseZeroHeadlineMethod, number>;
  candidate_score: number;
  condition_scores: Record<string, number>;
  violation_scores: Record<string, number>;
}

export interface PhaseZeroCase {
  id: string;
  family: string;
  query: string;
  required: PhaseZeroConstraint[];
  excluded: PhaseZeroConstraint[];
  complete_document_ids: string[];
  documents: PhaseZeroDocument[];
  candidate_trace: {
    labels_used_in_scoring: boolean;
    anchor_condition?: string;
    anchor_candidates?: number;
    execution?: string;
    ranking?: string;
  };
}

export interface PhaseZeroReport {
  suite: string;
  classification:
    | "synthetic_diagnostic"
    | "external_benchmark"
    | "external_benchmark_sample"
    | "external_benchmark_subset";
  case_count: number;
  family_count: number;
  headline_methods: PhaseZeroHeadlineMethod[];
  reports: Record<PhaseZeroMethod, PhaseZeroMethodReport>;
  comparison: {
    candidate: PhaseZeroMethod;
    strongest_control: PhaseZeroMethod;
    delta: number;
    ci95_low: number;
    ci95_high: number;
    bootstrap_samples: number;
    raw_sign_test_p: number;
    holm_adjusted_p: number;
  };
  perturbations: Record<string, { complete_before_partial_at_10: number; delta_from_oracle: number }>;
  gate: {
    status: "not_evaluable" | "pass" | "fail";
    diagnostic_decision: string;
    reason: string;
    criteria: { id: string; status: string }[];
  };
  systems: {
    index_build_p50_ms: number;
    index_build_p95_ms: number;
    mean_vocabulary_terms: number;
    mean_posting_entries: number;
    mean_estimated_index_bytes: number;
  };
  economics: {
    reference_method: PhaseZeroMethod;
    documents_scored_reduction: number;
    postings_touched_ratio: number;
    p50_latency_ratio: number;
    cpu_ms_per_success_ratio: number | null;
    pareto_improvement_observed: boolean;
  };
  required_baselines: { implemented: PhaseZeroMethod[]; pending_external: string[] };
  provenance: {
    generated_at: string;
    source_fixture: string;
    source_bytes: number;
    source_sha256: string;
    source: Record<string, unknown>;
    seed: number;
    repeats_per_case: number;
    bootstrap_samples: number;
    case_payload_limit: number | null;
    case_payload_count: number;
    python: string;
    platform: string;
    latency_scope: string;
    labels_used_in_scoring: boolean;
    claims_allowed: string;
    claims_not_allowed: string;
  };
  cases: PhaseZeroCase[];
}

export interface PhaseZeroProbe extends PhaseZeroCase {
  active_required_ids: string[];
  active_excluded_ids: string[];
  classification: "interactive_diagnostic";
  method_runs: Record<
    PhaseZeroMethod,
    {
      ranked_document_ids: string[];
      elapsed_ms: number;
      postings_touched: number;
      score_updates: number;
      documents_scored: number;
      trace: Record<string, unknown>;
    }
  >;
  index: {
    documents: number;
    passages: number;
    vocabulary_terms: number;
    posting_entries: number;
    estimated_serialized_bytes: number;
  };
}

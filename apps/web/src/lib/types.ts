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

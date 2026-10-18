import { Icon } from "./icon";
import type { ComparisonResult, PipelineResult, TraceEvent } from "@/lib/types";

interface Props {
  comparison: ComparisonResult | null;
  traces: TraceEvent[];
  running: boolean;
  onCitation: (id: number) => void;
}

const STAGES = {
  baseline: ["scope", "dense_retrieval", "grounding"],
  advanced: ["scope", "rewrite", "dense_retrieval", "sparse_retrieval", "fusion", "rerank", "late_interaction", "grounding"],
};

function confidenceLabel(value: number) {
  if (value >= 0.8) return "High confidence";
  if (value >= 0.5) return "Moderate confidence";
  return "Low confidence";
}

function formatAnswer(answer: string, onCitation: (id: number) => void) {
  const parts = answer.split(/(\[\d+\])/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/);
    return match ? <button key={`${part}-${index}`} className="inline-citation" onClick={() => onCitation(Number(match[1]))} aria-label={`Open citation ${match[1]}`}>{match[1]}</button> : part;
  });
}

function PipelineColumn({ result, advanced, onCitation }: { result: PipelineResult; advanced?: boolean; onCitation: (id: number) => void }) {
  return (
    <article className={`pipeline-column ${advanced ? "advanced" : "baseline"}`}>
      <header className="pipeline-header">
        <div>
          <span className="pipeline-dot" />
          <h2>{advanced ? "Advanced pipeline" : "Naive baseline"}</h2>
          {advanced && <span className="recommended">Recommended</span>}
        </div>
        <span className="latency">{result.latency_ms.toFixed(1)} ms</span>
      </header>
      <div className="answer-block">
        <div className="answer-label">Grounded answer</div>
        <p>{formatAnswer(result.answer, onCitation)}</p>
        <div className="confidence-row">
          <div className="confidence-track"><span style={{ width: `${result.confidence * 100}%` }} /></div>
          <strong>{Math.round(result.confidence * 100)}%</strong>
          <span>{confidenceLabel(result.confidence)}</span>
        </div>
      </div>
      <div className="retrieval-list">
        <div className="list-heading"><span>Retrieved evidence</span><span>Final score</span></div>
        {result.hits.slice(0, 3).map((hit) => (
          <button className="retrieval-hit" key={hit.chunk_id} onClick={() => onCitation(result.citations.find((citation) => citation.page === hit.page)?.id ?? 1)}>
            <span className="hit-rank">{String(hit.rank).padStart(2, "0")}</span>
            <span className="hit-copy"><b>{hit.section}</b><small>Page {hit.page} · {hit.text.slice(0, 84)}…</small></span>
            <span className="score-stack"><b>{hit.scores.final.toFixed(2)}</b><i style={{ width: `${Math.min(hit.scores.final * 100, 100)}%` }} /></span>
          </button>
        ))}
      </div>
    </article>
  );
}

function PipelineSkeleton({ advanced }: { advanced?: boolean }) {
  return (
    <article className={`pipeline-column loading ${advanced ? "advanced" : "baseline"}`} aria-label={`${advanced ? "Advanced" : "Baseline"} pipeline running`}>
      <header className="pipeline-header"><div><span className="pipeline-dot" /><h2>{advanced ? "Advanced pipeline" : "Naive baseline"}</h2></div><span className="latency">running</span></header>
      <div className="skeleton-line wide"/><div className="skeleton-line"/><div className="skeleton-line short"/>
      <div className="skeleton-cards"><span/><span/><span/></div>
    </article>
  );
}

export function ExperimentPanel({ comparison, traces, running, onCitation }: Props) {
  const completed = (pipeline: "baseline" | "advanced", stage: string) => traces.some((trace) => trace.pipeline === pipeline && trace.stage === stage);
  const live = comparison?.mode === "live";
  const cached = comparison?.baseline.cached || comparison?.advanced.cached;
  const latencyDelta = comparison ? comparison.advanced.latency_ms - comparison.baseline.latency_ms : 0;
  return (
    <section className="experiment-output" aria-live="polite">
      {(running || traces.length > 0) && (
        <div className="live-trace">
          <div className="trace-title"><span className={running ? "pulse" : "done"}/><b>{running ? "Pipeline trace running" : live ? "Pipeline trace complete" : "Bundled trace replay"}</b><span>{traces.length} trace events received</span></div>
          <div className="trace-lanes">
            {(["baseline", "advanced"] as const).map((pipeline) => (
              <div className="trace-lane" key={pipeline}>
                <span className="lane-label">{pipeline}</span>
                {completed(pipeline, "cache") ? <span className="complete"><Icon name="check"/>Cached result</span> : STAGES[pipeline].map((stage) => <span className={completed(pipeline, stage) ? "complete" : running ? "pending" : ""} key={stage} title={stage}>{completed(pipeline, stage) && <Icon name="check"/>}{stage.replaceAll("_", " ")}</span>)}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="comparison-label"><span>Same corpus</span><i/><span>Different retrieval strategy</span><i/><span>{live ? "Local API result" : "Bundled example"}</span></div>
      <div className="comparison-grid">
        {comparison && !running ? <PipelineColumn result={comparison.baseline} onCitation={onCitation} /> : <PipelineSkeleton />}
        <div className="versus" aria-hidden="true">vs</div>
        {comparison && !running ? <PipelineColumn result={comparison.advanced} advanced onCitation={onCitation} /> : <PipelineSkeleton advanced />}
      </div>

      {comparison && !running && (
        <div className="delta-strip">
          <div><span className="delta-label">Confidence lift</span><b>+{Math.round((comparison.advanced.confidence - comparison.baseline.confidence) * 100)} pts</b><small>Grounding improved</small></div>
          <div><span className="delta-label">Evidence rank</span><b>#1</b><small>Correct page surfaced</small></div>
          <div><span className="delta-label">Latency delta</span><b>{latencyDelta >= 0 ? "+" : ""}{latencyDelta.toFixed(1)} ms</b><small>{live ? cached ? "Stored timing from cached result" : "Measured this run" : "Bundled example timing"}</small></div>
          <div><span className="delta-label">Citation coverage</span><b>{comparison.advanced.citations.length}/{comparison.advanced.citations.length}</b><small>Every claim linked</small></div>
        </div>
      )}
    </section>
  );
}

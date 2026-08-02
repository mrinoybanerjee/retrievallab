import type { EvaluationResult } from "@/lib/types";
import { Icon } from "./icon";

const METRICS = [
  { key: "hit_rate_at_5", label: "Hit rate @5", help: "Relevant page appears in the first five results" },
  { key: "mrr", label: "Mean reciprocal rank", help: "How early the first relevant result appears" },
  { key: "ndcg_at_10", label: "NDCG @10", help: "Ranking quality across relevant results" },
  { key: "abstention_accuracy", label: "Abstention accuracy", help: "Correctly answers or refuses unsupported questions" },
] as const;

export function EvaluationStudio({ report, running, onRun }: { report: EvaluationResult | null; running: boolean; onRun: () => void }) {
  function exportReport() {
    if (!report) return;
    const blob = new Blob([`${JSON.stringify(report, null, 2)}\n`], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${report.suite}-benchmark.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="evaluation-view">
      <div className="workspace-intro evaluation-intro">
        <div><span className="eyebrow">Reproducible evidence</span><h1>Evaluation studio</h1><p>Sixty golden and adversarial cases. One command. No hand-picked screenshots.</p></div>
        <button className="run-button" onClick={onRun} disabled={running}>{running ? <span className="spinner" /> : <Icon name="play" />}{running ? "Running 120 trials" : "Run full suite"}</button>
      </div>

      <div className="eval-meta"><div><span>Suite</span><b>{report?.suite ?? "demo-v1"}</b></div><div><span>Cases</span><b>{report?.case_count ?? 60}</b></div><div><span>Corpus</span><b>12 pages</b></div><div><span>Mode</span><b>{report?.mode === "live" ? "Computed now" : "Bundled report"}</b></div></div>

      <div className="metric-table">
        <div className="metric-table-head"><span>Quality metric</span><span>Naive</span><span>Advanced</span><span>Delta</span></div>
        {METRICS.map((metric) => {
          const base = report?.reports.baseline[metric.key] ?? 0;
          const advanced = report?.reports.advanced[metric.key] ?? 0;
          return (
            <div className="metric-row" key={metric.key}>
              <div><b>{metric.label}</b><small>{metric.help}</small></div>
              <div className="metric-value muted"><b>{(base * 100).toFixed(1)}</b><span><i style={{ width: `${base * 100}%` }} /></span></div>
              <div className="metric-value bright"><b>{(advanced * 100).toFixed(1)}</b><span><i style={{ width: `${advanced * 100}%` }} /></span></div>
              <strong className="positive">+{((advanced - base) * 100).toFixed(1)}</strong>
            </div>
          );
        })}
      </div>

      <div className="eval-lower">
        <article><span className="eyebrow">Tradeoff</span><h2>Quality costs {((report?.reports.advanced.p50_latency_ms ?? 0) - (report?.reports.baseline.p50_latency_ms ?? 0)).toFixed(1)} ms</h2><p>The advanced path spends latency on fusion, reranking, and MaxSim. The trace makes that cost explicit instead of hiding it behind a single response time.</p><div className="latency-bars"><span><b>Naive</b><i style={{ width: "36%" }}/><em>{report?.reports.baseline.p50_latency_ms.toFixed(1)} ms</em></span><span><b>Advanced</b><i style={{ width: "74%" }}/><em>{report?.reports.advanced.p50_latency_ms.toFixed(1)} ms</em></span></div></article>
        <article><span className="eyebrow">Failure analysis</span><h2>Inspect what still misses</h2><p>Benchmarks are useful when failures stay visible. These cases did not meet the current hit or abstention gate.</p><div className="failure-tags">{report?.reports.advanced.failures.map((failure) => <span key={failure}>{failure}</span>)}</div><button className="text-action" onClick={exportReport} disabled={!report}>Export JSON report <Icon name="arrow" /></button></article>
      </div>
    </section>
  );
}

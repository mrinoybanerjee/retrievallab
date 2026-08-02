"use client";

import { useMemo, useState } from "react";

import { runPhaseZeroProbe } from "@/lib/api";
import type {
  PhaseZeroCase,
  PhaseZeroHeadlineMethod,
  PhaseZeroMethod,
  PhaseZeroProbe,
  PhaseZeroReport,
  PhaseZeroSource,
} from "@/lib/types";

import { Icon } from "./icon";

type CardMethod = PhaseZeroHeadlineMethod | "bm25";

const HEADLINE_COPY: Record<
  CardMethod,
  { eyebrow: string; description: string; accent: string }
> = {
  dense: {
    eyebrow: "Naive baseline",
    description: "One feature-hashed vector. Topical strength can hide a missing condition.",
    accent: "neutral",
  },
  hybrid: {
    eyebrow: "Hybrid control",
    description: "Monolithic dense + BM25 with reciprocal-rank fusion.",
    accent: "amber",
  },
  bm25: {
    eyebrow: "Strongest matched control",
    description: "One monolithic sparse query. Fast, cheap, and strongest on the pinned external suite.",
    accent: "amber",
  },
  coverage_first: {
    eyebrow: "Experimental candidate",
    description: "Rarest condition first, then complete → coverage → weakest evidence.",
    accent: "signal",
  },
};

const CRITERION_LABELS: Record<string, string> = {
  two_external_families: "Two external benchmark families",
  five_point_gain_vs_strongest_control: "+5 points vs strongest matched control",
  parser_and_order_robustness: "Parser and order robustness",
  beir_regression_under_one_point: "BEIR regression under one point",
  latency_or_cost_pareto_gain: "Latency or serving-cost Pareto gain",
  paired_statistics_and_multiplicity: "Paired statistics + multiplicity control",
};

function percent(value: number) {
  return `${(value * 100).toFixed(value === 0 || value === 1 ? 0 : 1)}%`;
}

function bytes(value: number) {
  if (value < 1024) return `${Math.round(value)} B`;
  return `${(value / 1024).toFixed(1)} KB`;
}

function conditionTint(value: number, excluded = false) {
  const alpha = Math.max(0.04, Math.min(0.3, value * 0.3));
  return excluded
    ? { background: `rgb(245 118 104 / ${alpha})`, color: value >= 0.35 ? "#ff9d91" : undefined }
    : { background: `rgb(201 243 106 / ${alpha})`, color: value >= 0.35 ? "#d9ff87" : undefined };
}

function MethodCard({ report, method, rejected = false }: { report: PhaseZeroReport; method: PhaseZeroMethod; rejected?: boolean }) {
  const metrics = report.reports[method];
  const copy = HEADLINE_COPY[method as CardMethod] ?? {
    eyebrow: "Strongest matched control",
    description: "The highest-performing matched control on this exact suite.",
    accent: "amber",
  };
  return (
    <article className={`frontier-method ${copy.accent} ${rejected ? "rejected" : ""}`}>
      <div className="frontier-method-top">
        <span className="eyebrow">{copy.eyebrow}</span>
        <span className="measurement-badge">Measured</span>
      </div>
      <h2>{metrics.label}</h2>
      <p>{copy.description}</p>
      <div className="frontier-primary-metric">
        <strong>{percent(metrics.complete_before_partial_at_10)}</strong>
        <span>complete before partial @10</span>
      </div>
      <dl>
        <div><dt>p95 query</dt><dd>{metrics.p95_latency_ms.toFixed(3)} ms</dd></div>
        <div><dt>{method === "coverage_first" ? "Tuples assembled" : "Docs scored"}</dt><dd>{metrics.mean_documents_scored.toFixed(1)}</dd></div>
        <div><dt>Top-1 violations</dt><dd>{percent(metrics.logical_violation_at_1)}</dd></div>
      </dl>
    </article>
  );
}

function CaseExplorer({ report, source }: { report: PhaseZeroReport; source: PhaseZeroSource }) {
  const [caseId, setCaseId] = useState(report.cases[0]?.id ?? "");
  const selected = useMemo(
    () => report.cases.find((item) => item.id === caseId) ?? report.cases[0],
    [caseId, report.cases],
  );
  const [requiredIds, setRequiredIds] = useState<string[]>(selected?.required.map((item) => item.id) ?? []);
  const [excludedIds, setExcludedIds] = useState<string[]>(selected?.excluded.map((item) => item.id) ?? []);
  const [probe, setProbe] = useState<PhaseZeroProbe | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  if (!selected) return null;
  const displayed: PhaseZeroCase = probe ?? selected;
  const orderedDocuments = [...displayed.documents].sort(
    (left, right) => left.ranks.coverage_first - right.ranks.coverage_first,
  );

  function toggle(id: string, values: string[], update: (next: string[]) => void) {
    update(values.includes(id) ? values.filter((value) => value !== id) : [...values, id]);
  }

  function selectCase(nextId: string) {
    const next = report.cases.find((item) => item.id === nextId);
    if (!next) return;
    setCaseId(nextId);
    setRequiredIds(next.required.map((item) => item.id));
    setExcludedIds(next.excluded.map((item) => item.id));
    setProbe(null);
    setError("");
  }

  async function runProbe() {
    if (!requiredIds.length || running) return;
    setRunning(true);
    setError("");
    try {
      setProbe(await runPhaseZeroProbe(source, selected.id, requiredIds, excludedIds));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The interactive probe could not run.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="case-explorer" aria-labelledby="case-explorer-title">
      <div className="case-explorer-head">
        <div>
          <span className="eyebrow">Live case explorer</span>
          <h2 id="case-explorer-title">Break the query apart. Watch the ranking move.</h2>
          <p>Conditions are benchmark-provided oracle structure. Turn one off, rerun locally, and inspect every evidence score.</p>
        </div>
        <label>
          <span>Diagnostic case</span>
          <select value={selected.id} onChange={(event) => selectCase(event.target.value)}>
            {report.cases.map((item) => <option value={item.id} key={item.id}>{item.family} · {item.id.split("-").slice(1).join(" ")}</option>)}
          </select>
        </label>
      </div>

      <blockquote className="research-query">{selected.query}</blockquote>

      <div className="condition-workbench">
        <div className="condition-groups">
          <div>
            <span className="condition-label">Must satisfy every condition</span>
            <div className="condition-chips">
              {selected.required.map((condition) => {
                const active = requiredIds.includes(condition.id);
                return <button className={active ? "active" : ""} aria-pressed={active} key={condition.id} onClick={() => toggle(condition.id, requiredIds, setRequiredIds)}><span>{active ? "✓" : "+"}</span>{condition.text}</button>;
              })}
            </div>
          </div>
          {selected.excluded.length > 0 && <div>
              <span className="condition-label excluded">Must not contain</span>
              <div className="condition-chips excluded">
                {selected.excluded.map((condition) => {
                  const active = excludedIds.includes(condition.id);
                  return <button className={active ? "active" : ""} aria-pressed={active} key={condition.id} onClick={() => toggle(condition.id, excludedIds, setExcludedIds)}><span>{active ? "×" : "+"}</span>{condition.text}</button>;
                })}
              </div>
            </div>}
        </div>
        <div className="probe-actions">
          <button className="run-button" disabled={running || !requiredIds.length} onClick={() => void runProbe()}>{running ? <span className="spinner" /> : <Icon name="play" />}{running ? "Scoring" : "Run edited query"}</button>
          <button className="reset-probe" disabled={!probe} onClick={() => setProbe(null)}>Reset artifact</button>
          <small>{probe ? "Live API measurement" : "Committed artifact"}</small>
        </div>
      </div>
      {error && <div className="probe-error" role="alert">{error} Start the local API to enable editing; the committed measurement remains visible.</div>}

      <div className="evidence-matrix-wrap">
        <table className="evidence-matrix">
          <thead>
            <tr>
              <th>Candidate document</th>
              {selected.required.map((condition) => <th key={condition.id} title={condition.text}>{condition.id}</th>)}
              {selected.excluded.map((condition) => <th className="excluded" key={condition.id} title={condition.text}>{condition.id}</th>)}
              <th>Dense</th><th>Hybrid</th><th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {orderedDocuments.map((document) => (
              <tr key={document.id} className={document.truth}>
                <td><span className={`truth-dot ${document.truth}`} /><div><b>{document.title}</b><small>{document.truth === "complete" ? "All conditions satisfied" : "Known partial / violating match"}</small></div></td>
                {selected.required.map((condition) => {
                  const score = document.condition_scores[condition.id] ?? 0;
                  return <td style={conditionTint(score)} key={condition.id}>{Math.round(score * 100)}</td>;
                })}
                {selected.excluded.map((condition) => {
                  const score = document.violation_scores[condition.id] ?? 0;
                  return <td style={conditionTint(score, true)} key={condition.id}>{Math.round(score * 100)}</td>;
                })}
                <td>#{document.ranks.dense}</td><td>#{document.ranks.hybrid}</td><td className="coverage-rank">#{document.ranks.coverage_first}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="matrix-legend">
        <span><i className="complete" /> Known complete</span>
        <span><i className="partial" /> Known partial</span>
        <span>Cell = normalized sparse evidence · pass threshold 35</span>
        <span>Labels are evaluation-only, never scoring inputs</span>
      </div>
    </section>
  );
}

export function FrontierLab({
  report,
  source,
  mode,
  running,
  onRerun,
  onSourceChange,
}: {
  report: PhaseZeroReport;
  source: PhaseZeroSource;
  mode: "live" | "artifact";
  running: boolean;
  onRerun: () => void;
  onSourceChange: (source: PhaseZeroSource) => void;
}) {
  const external = source === "external";
  const strongest = report.reports[report.comparison.strongest_control];
  const candidate = report.reports.coverage_first;
  const displayedMethods: PhaseZeroMethod[] = external
    ? ["dense", report.comparison.strongest_control, "coverage_first"]
    : report.headline_methods;
  const sourceMetadata = report.provenance.source as {
    name?: string;
    repository?: string;
    revision?: string;
    selected_row_count?: number;
    skipped_row_count?: number;
    condition_source?: string;
  };
  return (
    <section className="frontier-view">
      <div className="workspace-intro frontier-intro">
        <div>
          <div className="frontier-kicker"><span className="eyebrow">Phase 0 · Falsification before training</span><span className={`synthetic-badge ${external ? "external" : ""}`}>{external ? "External evidence" : "Synthetic diagnostic"}</span></div>
          <h1>Complete evidence, before partial matches.</h1>
          <p>A zero-training probe of the retrieval bottleneck where every condition matters—and a public record when an idea fails.</p>
        </div>
        <div className="frontier-actions">
          <div className="suite-toggle" aria-label="Evidence suite">
            <button className={external ? "active" : ""} onClick={() => onSourceChange("external")}>MultiConIR · 2,299</button>
            <button className={!external ? "active" : ""} onClick={() => onSourceChange("synthetic")}>Synthetic · 16</button>
          </div>
          {!external && <button className="run-button" onClick={onRerun} disabled={running}>{running ? <span className="spinner" /> : <Icon name="play" />}{running ? "Measuring 800 runs" : "Rerun on this CPU"}</button>}
        </div>
      </div>

      <div className="truth-banner">
        <div><span className="truth-icon">!</span><div><b>Research gate not passed</b><p>{report.gate.reason}</p></div></div>
        <span>{mode === "live" ? "Computed by local API" : "Committed artifact"}</span>
      </div>

      <div className="frontier-method-grid">
        {displayedMethods.map((method) => <MethodCard report={report} method={method} rejected={external && method === "coverage_first"} key={method} />)}
      </div>

      <section className="falsification-result">
        <div>
          <span className="eyebrow">{external ? "External falsification result" : "What the diagnostic disproved"}</span>
          <h2>{external ? "The first candidate is rejected." : "A scoring formula is not the contribution."}</h2>
          <p>{external ? <>Across {report.case_count.toLocaleString()} parsable MultiConIR cases, <b>{strongest.label}</b> reaches {percent(strongest.complete_before_partial_at_10)} while coverage-first reaches {percent(candidate.complete_before_partial_at_10)}. The candidate trails by {Math.abs(report.comparison.delta * 100).toFixed(1)} points; 95% bootstrap CI [{(report.comparison.ci95_low * 100).toFixed(1)}, {(report.comparison.ci95_high * 100).toFixed(1)}]. This is evidence against the current method, not a benchmark win.</> : <>Coverage-first beats monolithic dense and hybrid on this controlled fixture, but <b>{strongest.label}</b> also reaches {percent(strongest.complete_before_partial_at_10)}. The candidate&apos;s measured delta against the strongest matched control is {report.comparison.delta >= 0 ? "+" : ""}{(report.comparison.delta * 100).toFixed(1)} points, 95% bootstrap CI [{(report.comparison.ci95_low * 100).toFixed(1)}, {(report.comparison.ci95_high * 100).toFixed(1)}].</>}</p>
        </div>
        <div className={`work-reduction ${report.economics.pareto_improvement_observed ? "pareto" : "rejected"}`}>
          <span>{report.economics.pareto_improvement_observed ? "Pareto improvement observed" : "Economic check · no Pareto win"}</span>
          <strong>{candidate.mean_documents_scored.toFixed(1)} <small>condition tuples assembled</small></strong>
          <div><i style={{ width: `${Math.min(100, (candidate.mean_documents_scored / strongest.mean_documents_scored) * 100)}%` }} /></div>
          <p>The anchor reduces tuple assembly versus {strongest.mean_documents_scored.toFixed(1)} documents, but touches {report.economics.postings_touched_ratio.toFixed(2)}× the postings and takes {report.economics.p50_latency_ratio.toFixed(2)}× the p50 time. The traversal—not the rank formula—is the next research target.</p>
        </div>
      </section>

      <CaseExplorer report={report} source={source} />

      <div className="research-lower-grid">
        <section className="gate-card">
          <div><span className="eyebrow">Preregistered decision gate</span><span className="gate-state">Not evaluable</span></div>
          <h2>What must be true before a paper claim</h2>
          <ul>
            {report.gate.criteria.map((criterion) => {
              const failed = criterion.status.includes("failed") || criterion.status.includes("not_pareto");
              const ready = criterion.status.includes("implemented") || criterion.status.includes("pass");
              const diagnostic = criterion.status.includes("diagnostic") || criterion.status.includes("oracle") || criterion.status.includes("microbenchmark");
              return <li key={criterion.id}><span className={failed ? "failed" : ready ? "ready" : diagnostic ? "diagnostic" : "pending"}>{failed ? "×" : ready ? "✓" : diagnostic ? "~" : "·"}</span><b>{CRITERION_LABELS[criterion.id] ?? criterion.id}</b><small>{criterion.status.replaceAll("_", " ")}</small></li>;
            })}
          </ul>
        </section>
        <section className="provenance-card">
          <span className="eyebrow">Measurement receipt</span>
          <h2>Nothing hidden behind the chart.</h2>
          <dl>
            <div><dt>Cases / families</dt><dd>{report.case_count} / {report.family_count}</dd></div>
            {external && <div><dt>Source rows skipped</dt><dd>{sourceMetadata.skipped_row_count ?? 0}</dd></div>}
            <div><dt>Repeated trials</dt><dd>{report.provenance.repeats_per_case} per case</dd></div>
            <div><dt>Bootstrap samples</dt><dd>{report.provenance.bootstrap_samples.toLocaleString()}</dd></div>
            <div><dt>Index build p95</dt><dd>{report.systems.index_build_p95_ms.toFixed(3)} ms</dd></div>
            <div><dt>Mean sparse index</dt><dd>{bytes(report.systems.mean_estimated_index_bytes)}</dd></div>
            <div><dt>Scoring labels</dt><dd>{report.provenance.labels_used_in_scoring ? "Used" : "Never used"}</dd></div>
          </dl>
          <p>{external ? `${sourceMetadata.name ?? "External suite"} @ ${sourceMetadata.revision?.slice(0, 8)} · ${sourceMetadata.condition_source}. ` : ""}{report.provenance.latency_scope}. Generated {new Date(report.provenance.generated_at).toLocaleString()}.</p>
          <a href="https://github.com/mrinoybanerjee/retrievallab/blob/main/docs/FRONTIER_RETRIEVAL_RESEARCH_PLAN.md" target="_blank" rel="noreferrer">Read the full research protocol <Icon name="arrow" /></a>
        </section>
      </div>
    </section>
  );
}

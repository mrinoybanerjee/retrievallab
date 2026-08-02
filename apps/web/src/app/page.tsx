"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { CorpusView } from "@/components/corpus-view";
import { EvaluationStudio } from "@/components/evaluation-studio";
import { EvidenceDrawer } from "@/components/evidence-drawer";
import { ExperimentPanel } from "@/components/experiment-panel";
import { FrontierLab } from "@/components/frontier-lab";
import { Icon } from "@/components/icon";
import { loadPhaseZeroReport, runComparison, runEvaluation } from "@/lib/api";
import { DEMO, FALLBACK_COMPARISON, FALLBACK_EVALUATION } from "@/lib/demo";
import type { ActiveCorpus, ComparisonResult, EvaluationResult, PhaseZeroReport, PhaseZeroSource, TraceEvent } from "@/lib/types";

type View = "experiment" | "frontier" | "evaluation" | "corpus";

const NAVIGATION: { id: View; label: string; icon: "spark" | "chart" | "book" }[] = [
  { id: "experiment", label: "Experiment", icon: "spark" },
  { id: "frontier", label: "Frontier lab", icon: "chart" },
  { id: "evaluation", label: "Evaluation studio", icon: "chart" },
  { id: "corpus", label: "Corpus lab", icon: "book" },
];

export default function Home() {
  const [view, setView] = useState<View>("experiment");
  const [question, setQuestion] = useState(DEMO.suggested_questions[0]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(FALLBACK_COMPARISON);
  const [traces, setTraces] = useState<TraceEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [connection, setConnection] = useState<"live" | "replay" | "checking">("checking");
  const [selectedCitation, setSelectedCitation] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(FALLBACK_EVALUATION);
  const [evaluationRunning, setEvaluationRunning] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [phaseZero, setPhaseZero] = useState<PhaseZeroReport | null>(null);
  const [phaseZeroSource, setPhaseZeroSource] = useState<PhaseZeroSource>("external");
  const [phaseZeroMode, setPhaseZeroMode] = useState<"live" | "artifact">("artifact");
  const [phaseZeroRunning, setPhaseZeroRunning] = useState(false);
  const [phaseZeroError, setPhaseZeroError] = useState("");
  const [activeCorpus, setActiveCorpus] = useState<ActiveCorpus>({ id: "demo", name: "RAG field guide", pages: 12, chunks: DEMO.corpus.chunks });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/healthz`, {
      signal: AbortSignal.timeout(1200),
    })
      .then((response) => setConnection(response.ok ? "live" : "replay"))
      .catch(() => setConnection("replay"));
  }, []);

  useEffect(() => {
    if (view !== "frontier" || phaseZero) return;
    let active = true;
    void loadPhaseZeroReport(phaseZeroSource).then((result) => {
      if (!active) return;
      setPhaseZero(result.report);
      setPhaseZeroMode(result.mode);
      if (result.mode === "live") setConnection("live");
    }).catch((error: unknown) => {
      if (active) setPhaseZeroError(error instanceof Error ? error.message : "Phase 0 report is unavailable.");
    });
    return () => { active = false; };
  }, [view, phaseZero, phaseZeroSource]);

  const visibleTraces = useMemo(
    () => traces.filter((trace, index, all) => all.findIndex((item) => item.pipeline === trace.pipeline && item.stage === trace.stage) === index),
    [traces],
  );

  async function handleRun() {
    if (question.trim().length < 3 || isRunning) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setIsRunning(true);
    setTraces([]);
    setComparison(null);
    setDrawerOpen(false);
    try {
      const result = await runComparison(question, (trace) => setTraces((current) => [...current, trace]), controller.signal, activeCorpus.id);
      setComparison(result);
      setConnection(result.mode === "live" ? "live" : "replay");
    } finally {
      setIsRunning(false);
    }
  }

  async function handleEvaluation() {
    setEvaluationRunning(true);
    try {
      const report = await runEvaluation();
      setEvaluation(report);
      if (report.mode === "live") setConnection("live");
    } finally {
      setEvaluationRunning(false);
    }
  }

  async function handlePhaseZero(rerun: boolean, suite = phaseZeroSource) {
    setPhaseZeroRunning(true);
    setPhaseZeroError("");
    try {
      const result = await loadPhaseZeroReport(suite, rerun);
      setPhaseZero(result.report);
      setPhaseZeroMode(result.mode);
      if (result.mode === "live") setConnection("live");
    } catch (error) {
      setPhaseZeroError(error instanceof Error ? error.message : "Phase 0 report is unavailable.");
    } finally {
      setPhaseZeroRunning(false);
    }
  }

  function selectPhaseZeroSource(source: PhaseZeroSource) {
    if (source === phaseZeroSource || phaseZeroRunning) return;
    setPhaseZeroSource(source);
    setPhaseZero(null);
    setPhaseZeroError("");
  }

  function openCitation(id: number) {
    setSelectedCitation(id);
    setDrawerOpen(true);
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to workspace</a>
      <header className="topbar">
        <button className="brand" onClick={() => setView("experiment")} aria-label="RetrievalLab home">
          <span className="brand-mark"><span /></span>
          <span className="brand-name">RetrievalLab</span>
          <span className="version">v0.2</span>
        </button>
        <div className="topbar-center" aria-label="Current workspace">
          <span className="workspace-title">Observable retrieval research</span>
          <span className="keyboard-hint"><kbd>⌘</kbd><kbd>K</kbd></span>
        </div>
        <div className={`connection-pill ${connection}`} title={connection === "live" ? "Connected to the local retrieval API" : "Using the bundled offline trace replay"}>
          <span className="status-dot" />
          {connection === "checking" ? "Checking API" : connection === "live" ? "Local engine" : "Replay mode"}
        </div>
      </header>

      <aside className="rail" aria-label="Primary navigation">
        <nav className="primary-nav">
          {NAVIGATION.map((item) => (
            <button key={item.id} className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}>
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <section className="corpus-summary" aria-labelledby="corpus-title">
          <div className="section-kicker">Active corpus</div>
          <div className="corpus-heading">
            <span className="file-badge">PDF</span>
            <div>
              <h2 id="corpus-title">{activeCorpus.name}</h2>
              <p>{activeCorpus.pages} pages · {activeCorpus.chunks} chunks</p>
            </div>
          </div>
          <div className="index-state"><span /> Indexed locally</div>
          <dl className="corpus-stats">
            <div><dt>Encoder</dt><dd>Hash 384d</dd></div>
            <div><dt>Sparse</dt><dd>BM25</dd></div>
            <div><dt>Privacy</dt><dd>On device</dd></div>
          </dl>
        </section>

        <div className="rail-bottom">
          <a className="rail-link" href="https://github.com/mrinoybanerjee/retrievallab/blob/main/docs/ARCHITECTURE.md" target="_blank" rel="noreferrer"><Icon name="code" /><span>View architecture</span></a>
          <a className="rail-link" href="https://github.com/mrinoybanerjee/retrievallab" target="_blank" rel="noreferrer"><Icon name="github" /><span>GitHub</span></a>
        </div>
      </aside>

      <main id="main-content" className="workspace">
        {view === "experiment" && (
          <>
            <section className="workspace-intro">
              <div>
                <span className="eyebrow">Live retrieval experiment</span>
                <h1>See what changed the answer.</h1>
                <p>One question. Two pipelines. Every retrieval decision exposed.</p>
              </div>
              <button className="advanced-toggle" aria-expanded={advancedOpen} onClick={() => setAdvancedOpen((open) => !open)}>
                <Icon name="sliders" /> Strategy controls <Icon name="chevron" />
              </button>
            </section>

            {advancedOpen && (
              <section className="strategy-strip" aria-label="Advanced retrieval strategy">
                {["Rewrite", "Dense 12", "BM25 12", "RRF k=60", "Rerank 10", "MaxSim 6", "Abstain .31"].map((label, index) => (
                  <span key={label}><b>{String(index + 1).padStart(2, "0")}</b>{label}</span>
                ))}
              </section>
            )}

            <section className="query-composer" aria-label="Ask the corpus">
              <label htmlFor="question">Question</label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === "Enter") void handleRun();
                }}
                rows={2}
                maxLength={500}
              />
              <div className="composer-actions">
                <div className="suggestions" aria-label="Suggested questions">
                  {DEMO.suggested_questions.slice(0, 3).map((suggestion) => (
                    <button key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion.split("?")[0]}</button>
                  ))}
                </div>
                <button className="run-button" onClick={() => void handleRun()} disabled={isRunning || question.trim().length < 3}>
                  {isRunning ? <span className="spinner" /> : <Icon name="play" />}
                  {isRunning ? "Running both pipelines" : "Run comparison"}
                  {!isRunning && <kbd>⌘↵</kbd>}
                </button>
              </div>
            </section>

            <ExperimentPanel
              comparison={comparison}
              traces={visibleTraces}
              running={isRunning}
              onCitation={openCitation}
            />
          </>
        )}

        {view === "evaluation" && (
          <EvaluationStudio report={evaluation} running={evaluationRunning} onRun={() => void handleEvaluation()} />
        )}
        {view === "frontier" && phaseZero && (
          <FrontierLab
            key={phaseZero.suite}
            report={phaseZero}
            source={phaseZeroSource}
            mode={phaseZeroMode}
            running={phaseZeroRunning}
            onRerun={() => void handlePhaseZero(true)}
            onSourceChange={selectPhaseZeroSource}
          />
        )}
        {view === "frontier" && !phaseZero && (
          <section className="frontier-loading" aria-live="polite">
            <span className="spinner" />
            <h1>{phaseZeroError ? "Research artifact unavailable" : "Loading the measurement receipt"}</h1>
            <p>{phaseZeroError || "Reading the committed Phase 0 run and its provenance."}</p>
            {phaseZeroError && <button className="run-button" onClick={() => void handlePhaseZero(false, phaseZeroSource)}>Retry</button>}
          </section>
        )}
        {view === "corpus" && <CorpusView activeCorpus={activeCorpus} onCorpusReady={setActiveCorpus} onAsk={(nextQuestion) => { setQuestion(nextQuestion); setView("experiment"); }} />}
      </main>

      {drawerOpen && <EvidenceDrawer
        open
        corpusId={activeCorpus.id}
        citation={comparison?.advanced.citations.find((item) => item.id === selectedCitation) ?? null}
        onClose={() => setDrawerOpen(false)}
      />}
      {drawerOpen && <button className="drawer-scrim" onClick={() => setDrawerOpen(false)} aria-label="Close evidence drawer" />}
    </div>
  );
}

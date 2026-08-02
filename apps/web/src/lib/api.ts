import { FALLBACK_COMPARISON, FALLBACK_EVALUATION, FALLBACK_TRACES } from "./demo";
import type { ActiveCorpus, ComparisonResult, EvaluationResult, TraceEvent } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function replay(onTrace: (trace: TraceEvent) => void, signal: AbortSignal): Promise<ComparisonResult> {
  for (const trace of FALLBACK_TRACES) {
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    await new Promise((resolve) => setTimeout(resolve, 150));
    onTrace(trace);
  }
  return FALLBACK_COMPARISON;
}

export async function runComparison(
  question: string,
  onTrace: (trace: TraceEvent) => void,
  signal: AbortSignal,
  corpusId = "demo",
): Promise<ComparisonResult> {
  try {
    const accepted = await fetch(`${API_URL}/api/v1/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, corpus_id: corpusId }),
      signal,
    });
    if (!accepted.ok) throw new Error(`API returned ${accepted.status}`);
    const job = (await accepted.json()) as { query_id: string; events_url: string };
    return await new Promise<ComparisonResult>((resolve, reject) => {
      const source = new EventSource(`${API_URL}${job.events_url}`);
      const abort = () => { source.close(); reject(new DOMException("Aborted", "AbortError")); };
      signal.addEventListener("abort", abort, { once: true });
      source.addEventListener("trace", (event) => onTrace(JSON.parse((event as MessageEvent).data) as TraceEvent));
      source.addEventListener("result", (event) => {
        const result = JSON.parse((event as MessageEvent).data) as Omit<ComparisonResult, "mode">;
        source.close();
        signal.removeEventListener("abort", abort);
        resolve({ ...result, mode: "live" });
      });
      source.addEventListener("error", () => { source.close(); reject(new Error("Live event stream failed")); });
    });
  } catch (error) {
    if (signal.aborted) throw error;
    return replay(onTrace, signal);
  }
}

export async function uploadCorpus(file: File): Promise<ActiveCorpus> {
  const corpusForm = new FormData();
  corpusForm.append("name", file.name.replace(/\.pdf$/i, ""));
  const created = await fetch(`${API_URL}/api/v1/corpora`, { method: "POST", body: corpusForm });
  if (!created.ok) throw new Error(`Could not create corpus (${created.status})`);
  const corpus = (await created.json()) as { id: string; name: string };

  const uploadForm = new FormData();
  uploadForm.append("file", file);
  const uploaded = await fetch(`${API_URL}/api/v1/corpora/${corpus.id}/documents`, {
    method: "POST",
    body: uploadForm,
  });
  if (!uploaded.ok) {
    const payload = (await uploaded.json().catch(() => null)) as
      | { detail?: { message?: string; fix?: string } }
      | null;
    const detail = payload?.detail;
    throw new Error([detail?.message, detail?.fix].filter(Boolean).join(" ") || `Upload failed (${uploaded.status})`);
  }
  const document = (await uploaded.json()) as { pages: number; chunks: number };
  return { id: corpus.id, name: corpus.name, pages: document.pages, chunks: document.chunks };
}

export async function runEvaluation(): Promise<EvaluationResult> {
  try {
    const response = await fetch(`${API_URL}/api/v1/evaluations`, { method: "POST", signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    return { ...(await response.json()), mode: "live" } as EvaluationResult;
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 900));
    return FALLBACK_EVALUATION;
  }
}

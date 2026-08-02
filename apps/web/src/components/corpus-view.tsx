"use client";

import { useRef, useState } from "react";

import { uploadCorpus } from "@/lib/api";
import type { ActiveCorpus } from "@/lib/types";

const PAGES = [
  [1, "Retrieval before generation", "foundations"], [2, "Dense and sparse retrieval", "retrieval"], [3, "Chunking and parent context", "chunking"], [4, "Retrieve then rerank", "reranking"], [5, "Grounding and page citations", "grounding"], [6, "Retrieval evaluation", "evaluation"], [7, "Confidence and abstention", "abstention"], [8, "Caching and latency", "performance"], [9, "Query rewriting and expansion", "queries"], [10, "Late interaction", "late-interaction"], [11, "Security and privacy", "security"], [12, "Operational design", "operations"],
] as const;

interface Props {
  activeCorpus: ActiveCorpus;
  onAsk: (question: string) => void;
  onCorpusReady: (corpus: ActiveCorpus) => void;
}

export function CorpusView({ activeCorpus, onAsk, onCorpusReady }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file || uploading) return;
    setUploading(true);
    setMessage(null);
    try {
      const corpus = await uploadCorpus(file);
      onCorpusReady(corpus);
      setMessage(`${file.name} is indexed and active. Ask it a question from the Experiment view.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The PDF could not be indexed.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <section className="corpus-view">
      <div className="workspace-intro"><div><span className="eyebrow">Page-aware source map</span><h1>Corpus lab</h1><p>Every indexed child remains attached to a source page and parent section.</p></div><div className="index-badge"><span/>{activeCorpus.chunks} chunks active</div></div>

      <div className="upload-workbench">
        <div><span className="eyebrow">Bring your own evidence</span><h2>Index a local PDF</h2><p>PDF only · 20 MB · 200 pages. Text is extracted in memory and never leaves the local API.</p></div>
        <input ref={inputRef} id="pdf-upload" type="file" accept="application/pdf,.pdf" onChange={(event) => void handleFile(event.target.files?.[0])} />
        <button className="run-button" onClick={() => inputRef.current?.click()} disabled={uploading}>{uploading ? <span className="spinner"/> : "+"}{uploading ? "Indexing PDF" : "Choose PDF"}</button>
        <div className="upload-status" aria-live="polite">{message ?? <>Active: <b>{activeCorpus.name}</b> · {activeCorpus.pages} pages · {activeCorpus.chunks} chunks</>}</div>
      </div>

      <div className="corpus-map">
        <div className="document-spine"><div className="cover-mini"><span>RetrievalLab</span><b>The Observable RAG Field Guide</b><small>Original bundled demo corpus</small></div><dl><div><dt>Pages</dt><dd>12</dd></div><div><dt>Child cap</dt><dd>500 tokens</dd></div><div><dt>Overlap</dt><dd>50 tokens</dd></div><div><dt>Parents</dt><dd>12</dd></div></dl></div>
        <div className="page-index">
          <div className="page-index-head"><span>Bundled page / parent section</span><span>Metadata topic</span><span>Action</span></div>
          {PAGES.map(([page, section, topic]) => <div className="page-row" key={page}><span className="page-chip">{String(page).padStart(2, "0")}</span><div><b>{section}</b><small>demo-p{page} · 1 child window</small></div><code>{topic}</code><button onClick={() => onAsk(`Explain ${section.toLowerCase()}.`)}>Ask this page</button></div>)}
        </div>
      </div>
    </section>
  );
}

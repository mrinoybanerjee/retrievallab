import type { Citation } from "@/lib/types";
import { Icon } from "./icon";

export function EvidenceDrawer({ open, citation, corpusId, onClose }: { open: boolean; citation: Citation | null; corpusId: string; onClose: () => void }) {
  return (
    <aside className={`evidence-drawer ${open ? "open" : ""}`} aria-hidden={!open} aria-label="Citation evidence">
      <header>
        <div><span className="eyebrow">Source evidence</span><h2>Citation {citation?.id ?? ""}</h2></div>
        <button onClick={onClose} aria-label="Close evidence"><Icon name="close" /></button>
      </header>
      {citation && (
        <>
          <div className="source-meta"><span className="file-badge">PDF</span><div><b>{citation.source}</b><span>Page {citation.page} · {citation.section}</span></div></div>
          <div className="page-preview">
            <div className="paper-page">
              <span className="page-number">{citation.page}</span>
              <h3>{citation.section}</h3>
              <p className="faded-lines">Retrieval systems become useful when each stage can be inspected, compared, and improved with evidence.</p>
              <blockquote>{citation.quote}</blockquote>
              <p className="faded-lines second">The ranking trace records why this passage was selected and how each strategy changed its final position.</p>
            </div>
          </div>
          <div className="evidence-footer"><span>Grounding score</span><b>{Math.round(citation.score * 100)}%</b><div><i style={{ width: `${citation.score * 100}%` }} /></div></div>
          {corpusId === "demo" ? (
            <a className="open-pdf" href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/documents/demo.pdf#page=${citation.page}`} target="_blank" rel="noreferrer">Open original PDF <Icon name="arrow" /></a>
          ) : (
            <p className="local-source-note">The uploaded original stays local; RetrievalLab keeps only its extracted page chunks in memory.</p>
          )}
        </>
      )}
    </aside>
  );
}

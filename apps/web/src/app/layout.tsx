import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RetrievalLab — Observable RAG Workbench",
  description: "Compare retrieval strategies, inspect page-level citations, and benchmark RAG quality locally.",
  metadataBase: new URL("https://github.com/mrinoybanerjee/retrievallab"),
  openGraph: {
    title: "RetrievalLab",
    description: "One question. Two RAG pipelines. Every retrieval decision exposed.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

const load = createRequire(import.meta.url);

// Render the shipped TSX with the installed TypeScript compiler; no extra test
// framework or browser download is needed. This hook is local to this test process.
for (const extension of [".ts", ".tsx"]) {
  load.extensions[extension] = (module, filename) => {
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
      fileName: filename,
    });
    module._compile(outputText, filename);
  };
}
const { ExperimentPanel } = load("../src/components/experiment-panel.tsx");
const { EvidenceDrawer } = load("../src/components/evidence-drawer.tsx");
const { FALLBACK_COMPARISON } = load("../src/lib/demo.ts");
const render = (component, props) => renderToStaticMarkup(React.createElement(component, props));
const panel = (comparison, traces = []) => render(ExperimentPanel, {
  comparison, traces, running: false, onCitation() {},
});

test("bundled preview timing is never labeled as a current measurement", () => {
  const html = panel(FALLBACK_COMPARISON);
  assert.match(html, /Bundled example timing/);
  assert.doesNotMatch(html, /Measured this run/);
});

test("live and cache-hit results distinguish measurement from stored timing", () => {
  const live = { ...FALLBACK_COMPARISON, mode: "live" };
  assert.match(panel(live), /Measured this run/);
  const cached = {
    ...live,
    baseline: { ...live.baseline, cached: true },
    advanced: { ...live.advanced, cached: true },
  };
  const traces = ["baseline", "advanced"].map((pipeline) => ({ pipeline, stage: "cache" }));
  const html = panel(cached, traces);
  assert.match(html, /2 trace events received/);
  assert.equal((html.match(/Cached result/g) || []).length, 2);
  assert.match(html, /Stored timing from cached result/);
  assert.doesNotMatch(html, /Measured this run|title="grounding"/);
});

test("full query reports all received stage events", () => {
  const stages = {
    baseline: ["scope", "dense_retrieval", "grounding"],
    advanced: ["scope", "rewrite", "dense_retrieval", "sparse_retrieval", "fusion", "rerank", "late_interaction", "grounding"],
  };
  const traces = Object.entries(stages).flatMap(([pipeline, names]) => names.map((stage) => ({ pipeline, stage })));
  assert.match(panel({ ...FALLBACK_COMPARISON, mode: "live" }, traces), /11 trace events received/);
});

test("citation drawer contains the actual excerpt without invented surrounding prose", () => {
  const citation = { ...FALLBACK_COMPARISON.advanced.citations[0], quote: "Synthetic exact source excerpt." };
  const html = render(EvidenceDrawer, { open: true, citation, corpusId: "demo", onClose() {} });
  assert.match(html, /Synthetic exact source excerpt\./);
  assert.match(html, /Cited excerpt · not a full page rendering/);
  assert.doesNotMatch(html, /Retrieval systems become useful|The ranking trace records why/);
  assert.match(html, /demo\.pdf#page=2/);
});

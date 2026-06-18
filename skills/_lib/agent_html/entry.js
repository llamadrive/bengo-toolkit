// Entry point for the vendored offline renderer bundle.
//
// Bundled (via build_bundle.mjs / esbuild) into dist/renderer_bundle.js, which
// build_html.py inlines into every self-contained .html legal diagram. The
// resulting file renders the exact same jp-court layout as the agent-format MCP
// (Claude Desktop inline render) and the public web viewer — but fully offline,
// with no network access and no third-party site (see the CSP in shell.html).
import React from "react";
import { createRoot } from "react-dom/client";
import { AgentRenderer } from "@agent-format/renderer";
import { jpCourtPlugin } from "@agent-format/jp-court";

// Exposed on window so the bootstrap <script> in shell.html can mount the
// renderer with the inlined .agent payload. showOpenInViewer is forced off so
// the self-contained file never offers to round-trip data through the public
// web viewer (the whole point is to stay local).
window.__bengoMountAgent = function (data, el) {
  createRoot(el).render(
    React.createElement(AgentRenderer, {
      data: data,
      plugins: [jpCourtPlugin],
      showOpenInViewer: false,
    })
  );
};

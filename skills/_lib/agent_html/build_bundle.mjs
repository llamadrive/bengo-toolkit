// Dev-only: build the vendored offline renderer bundle.
//
//   cd skills/_lib/agent_html && npm install && npm run build
//
// Produces dist/renderer_bundle.js (minified IIFE: react + react-dom +
// @agent-format/renderer + @agent-format/jp-court) and dist/renderer_styles.css.
// Both are committed and read at runtime by build_html.py. Rebuild whenever the
// @agent-format/* versions in package.json change so the offline .html stays
// visually identical to the agent-format MCP inline render. Keep the pinned
// versions in package.json in sync with the renderer range that
// @agent-format/mcp (see /.mcp.json) resolves.
import { build } from "esbuild";
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "dist");
mkdirSync(dist, { recursive: true });

await build({
  entryPoints: [join(here, "entry.js")],
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2020",
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "none",
  outfile: join(dist, "renderer_bundle.js"),
});

copyFileSync(
  join(here, "node_modules/@agent-format/renderer/dist/styles.css"),
  join(dist, "renderer_styles.css")
);

console.log("built dist/renderer_bundle.js + dist/renderer_styles.css");

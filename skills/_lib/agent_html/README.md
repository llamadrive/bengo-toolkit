# agent_html — 自己完結 HTML 描画（開発者向け）

`family-tree` / `lawsuit-analysis` の成果物を、第三者ビューアにもネットワークにも
依存しない **単一の `.html`** として出力するための部品。`.agent`（agent-format
JSON）を描画エンジンごと 1 ファイルに inline するため、弁護士はダブルクリックで
開け、メール添付でき、ブラウザの ⌘P で裁判所提出用 PDF にできる。

## 実行時（プラグイン利用者）

`build_html.py` だけが動く。Node も npm もネットワークも不要。

```bash
python3 build_html.py build --input family_tree_2026-06-18.agent          # → .html を出力
python3 build_html.py build --input X.agent --output Y.html --open         # 生成して開く
python3 build_html.py host                                                 # cli|inline を判定
```

`dist/renderer_bundle.js` と `dist/renderer_styles.css`（コミット済み）を読み、
`shell.html` に差し込んで出力する。

## バンドルの再生成（コントリビュータのみ）

`dist/` の中身はコミット済みの成果物。`@agent-format/*` のバージョンを上げたとき
**だけ** 再生成する。利用者の環境では実行されない。

```bash
cd skills/_lib/agent_html
npm install
npm run build      # → dist/renderer_bundle.js + dist/renderer_styles.css
```

### バージョン整合

`package.json` の `@agent-format/renderer` / `@agent-format/jp-court` は、
`/.mcp.json` の `@agent-format/mcp` が解決する renderer レンジと一致させる。
ずれると Claude Code の HTML 出力と Claude Desktop の inline 描画で見た目が
食い違う。MCP を上げたら本バンドルも再生成すること。

## 設計メモ

- **オフライン保証**: `shell.html` の CSP（`default-src 'none'` + 明示の
  `connect-src 'none'`）が fetch / XHR / WebSocket / beacon と外部リソース読込を
  すべて遮断する。本 HTML はネットワークを一切使わない（弁護士法23条 守秘義務）。
  ※ `<meta>` 配信の CSP では top-level navigation は止められない（`sandbox`
  ディレクティブは `<meta>` では無視される）ため、汚染スクリプトによる exfil は
  「絶対不能」ではなく「緩和」である。バンドルは pinned 依存からオフラインで
  ビルドし、信頼境界を固定する。
- **描画エンジンは同一**: MCP inline・公開ビューア・本 HTML は同じ
  `@agent-format/renderer` + `@agent-format/jp-court` を使う。書式は完全一致する。
- **`.agent` はユーザーに残さない使い捨て入力**: `build --prune-agent` で HTML
  生成後に必ず削除する。`host` が `inline` を返すホスト（Claude Desktop / Cursor
  等）では、削除前に `render_agent_file` で in-chat のインライン描画にも使う。

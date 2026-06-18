---
description: 訴訟関連文書を分析し構造化レポート（自己完結HTML）を生成
allowed-tools: Read, Write, Glob, mcp__docx-editor__read_document, mcp__agent-format__render_agent_file, Bash(python3 skills/_lib/audit.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/first_run.py:*), Bash(python3 skills/_lib/agent_html/build_html.py:*), Bash(python3 skills/family-tree/open_viewer.py:*)
---

訴訟関連文書（訴状、答弁書、準備書面、証拠説明書等）を読み取り、構造化データ（タイムライン、登場人物、主張・認否・証拠）を抽出して自己完結 HTML（ダブルクリックで開け、⌘P で PDF 化できる単一ファイル）を生成する。
MCP Apps 対応環境（Claude Desktop, Cursor 等）では併せてインライン描画も行う。
監査ログは現在の案件フォルダの `./.claude-bengo/audit.jsonl` に記録される。
`./.claude-bengo/` がまだ無ければ、実行時に現在のフォルダへ自動作成される。

$ARGUMENTS: 文書ファイルのパスまたはディレクトリ（任意。なければ対話で確認）。

## Step 0: 動作環境ガード

```
Bash: python3 skills/_lib/workspace.py check --require local_fs --require docx_mcp
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## Step 1

まず `skills/lawsuit-analysis/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

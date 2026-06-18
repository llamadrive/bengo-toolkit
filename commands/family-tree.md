---
description: 戸籍謄本PDFから家族関係を分析し相続関係説明図（自己完結HTML）を生成
allowed-tools: Read, Write, Glob, mcp__agent-format__render_agent_file, Bash(python3 skills/_lib/audit.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/first_run.py:*), Bash(python3 skills/_lib/agent_html/build_html.py:*), Bash(python3 skills/family-tree/open_viewer.py:*)
---

戸籍謄本のPDF文書から人物と関係性を抽出し、裁判所標準形式（相続関係説明図）を
自己完結 HTML（ダブルクリックで開け、⌘P で PDF 化できる単一ファイル）として生成する。
MCP Apps 対応環境（Claude Desktop, Cursor 等）では併せてインライン描画も行う。
監査ログは現在の案件フォルダの `./.claude-bengo/audit.jsonl` に記録される。
`./.claude-bengo/` がまだ無ければ、実行時に現在のフォルダへ自動作成される。

$ARGUMENTS: 戸籍謄本PDFのパス（任意。なければ対話で確認）。

## Step 0: 動作環境ガード

```
Bash: python3 skills/_lib/workspace.py check --require local_fs
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## Step 1

まず `skills/family-tree/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

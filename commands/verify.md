---
description: bengo-toolkit プラグインの動作確認テストを実行
allowed-tools: Read, Write, Glob, mcp__xlsx-editor__get_workbook_info, mcp__xlsx-editor__read_sheet, mcp__docx-editor__get_document_info, mcp__docx-editor__read_document, mcp__agent-format__render_agent_inline, Bash(python3 scripts/verify.py:*), Bash(python3 scripts/verify_mcp_integrity.py:*), Bash(python3 skills/_lib/audit.py --self-test:*), Bash(python3 skills/_lib/first_run.py --self-test:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/runtime.py:*), Bash(python3 skills/_lib/menu.py:*), Bash(python3 skills/_lib/agent_html/build_html.py:*), Bash(bash tests/agent_html.sh:*)
---

bengo-toolkit の各機能の動作を確認する。

$ARGUMENTS の指定方法:
- 引数なし: MCP サーバ接続テスト + fixtures 存在確認
- スキル名: 指定スキルの機能テスト（template-fill | family-tree | typo-check | lawsuit-analysis）
- `all`: 全スキルの機能テストを順次実行

## Step 0: 動作環境ガード（Cowork は完全機能 verify 不可）

`/verify` は MCP 接続と fixtures を実機テストするため、Cowork では実行不能である。

```
Bash: python3 skills/_lib/workspace.py check --require local_fs --require docx_mcp --require xlsx_mcp --require agent_format_mcp
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止。Cowork で
  動作する subset を試したいなら `/law-search 民法709条` や `/inheritance-calc` を提案する
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## Step 1

まず `skills/verify/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

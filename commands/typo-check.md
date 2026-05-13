---
description: 法律文書の誤字脱字・表記揺れを校正（修正履歴付き）
allowed-tools: Read, Write, Glob, mcp__docx-editor__*, Bash(python3 skills/_lib/audit.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/first_run.py:*)
---

DOCX法律文書を日本語法律文書作成ルールに照合し、誤字脱字・文法エラー・表記揺れを検出する。
承認された修正は修正履歴（Track Changes）付きで適用する。
監査ログは現在の案件フォルダの `./.claude-bengo/audit.jsonl` に記録される。
`./.claude-bengo/` がまだ無ければ、実行時に現在のフォルダへ自動作成される。

$ARGUMENTS: DOCXファイルのパス（任意。なければ対話で確認）。

## Step 0: 動作環境ガード

最初に以下を実行する:

```
Bash: python3 skills/_lib/workspace.py check --require docx_mcp --require local_fs
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージを**編集せずそのままユーザーへ表示**して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## Step 1

まず `skills/typo-check/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

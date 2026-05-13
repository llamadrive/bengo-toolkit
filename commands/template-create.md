---
description: XLSXファイルからテンプレート定義を作成・登録
allowed-tools: Read, Write, Glob, Bash(python3 skills/_lib/copy_file.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/template_detect.py:*), Bash(python3 skills/_lib/pii_scan.py:*), Bash(python3 skills/_lib/template_lib.py:*), Bash(python3 skills/_lib/first_run.py:*), mcp__xlsx-editor__*
---

XLSXファイルのセル構造を分析し、入力フィールドを特定してテンプレート定義（YAML）を作成する。
作成した定義とXLSXのコピーは、選んだ**保存場所**に保存される:
- 「この案件のみ」（`--scope case`、既定）: 現在の案件フォルダの `./.claude-bengo/templates/` に保存
- 「事務所共有」（`--scope firm`）: `/template-firm-setup` で設定したクラウド同期フォルダ（Google Drive / Dropbox / OneDrive 等）に保存
- 「この PC の全案件で共通」（`--scope user`）: `~/.claude-bengo/templates/` に保存

$ARGUMENTS: XLSXファイルのパス（任意。なければ対話で確認）。

フラグ（直接指定する場合。通常はスキルが質問するので不要）:
- `--scope case`   — 「この案件のみ」（**既定**）。この案件フォルダの中にだけ保存される。
- `--scope firm`   — 「事務所共有」（要 `/template-firm-setup`）。個人情報が含まれていると保存を拒否する。
- `--scope user`   — 「この PC の全案件で共通」。個人情報が含まれていると保存を拒否する。
- `--sample <path>` — 記入済みサンプル XLSX を指定（差分検出モード。推奨）。

## Step 0: 動作環境ガード

```
Bash: python3 skills/_lib/workspace.py check --require local_fs --require xlsx_mcp
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## Step 1

まず `skills/template-create/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

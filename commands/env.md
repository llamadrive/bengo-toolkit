---
description: 今の環境（案件・プラン・拡張・外部ツール・守り）をコマンド不要で一目で見える化する
allowed-tools: Read, Bash(python3 skills/env/build_env.py:*), Bash(python3 skills/_lib/agent_html/build_html.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/audit.py:*), mcp__agent-format__render_agent_file
---

弁護士が状態確認コマンドを 1 つずつ打たなくても、自分の Claude Code 環境を一目で確認できる
自己完結 HTML ダッシュボードを生成し、自動でブラウザに表示する。

表示するもの: 今の案件フォルダ／契約プラン・ログイン／入っている拡張と版／つながっている外部ツール
（Excel・Word・図の描画など）／守り（改ざん検知ログ・成果物の外部送信不可・プランと学習）／
この画面で分かること・分からないこと。

**方針**: 事実だけを見せ、健全性（緑=安全）は主張しない。秘密（監査 HMAC 鍵など）は載せない。
確実な現在値は本体の `/config`・`/mcp`・`/permissions` に案内する。

## $ARGUMENTS

- **引数なし**: 現在の案件フォルダを対象に環境ダッシュボードを生成・表示する。

## 実行

`env` スキルのワークフローに従う（`skills/env/SKILL.md`）:

1. Step 0: `python3 skills/_lib/workspace.py check --require local_fs`。exit 2 なら HTML を作らず
   テキスト要約で提示する。
2. `python3 skills/env/build_env.py` で環境を収集し `.agent` を生成。
3. （外部ツール連携ホストのみ）`build_html.py host` が `inline` なら `render_agent_file` で in-chat 描画。
4. `python3 skills/_lib/agent_html/build_html.py build --input env_dashboard_<日付>.agent --open --prune-agent`
   で自己完結 HTML を生成・自動表示。
5. `python3 skills/_lib/audit.py record --skill env --event file_write --file "<html>"` で監査記録。
6. です・ます調で案内し、この画面で分からない項目は本体の `/config`・`/mcp`・`/permissions` に誘導する。

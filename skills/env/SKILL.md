---
name: env
description: This skill should be used when the user asks to "環境を見せて", "今の環境", "今どうなってる", "設定は安全", "何が使える", "環境の状態", "環境ダッシュボード", "show my environment", "environment status", or wants a visual, at-a-glance overview of installed plugins, connected MCP tools, plan, and safety posture WITHOUT typing status commands one by one. Do NOT trigger for "verify / 動作確認 / テスト" (that is the verify skill).
version: 0.1.0
---

# 環境の見える化（env）

弁護士が**コマンドを打たずに**、自分の Claude Code 環境（今の案件・契約プラン・入っている拡張・
つながっている外部ツール・守りの状態）を**一目で確認**できる自己完結 HTML ダッシュボードを生成し、
自動でブラウザに表示する（family-tree / lawsuit-analysis と同じ描画方式）。

## 設計方針（厳守）

- **事実だけを見せ、健全性（緑=安全）は主張しない。** 外部ツール(MCP)が「今実際に動くか」・権限が
  「実際に適用されているか」はセッション時に Claude Code 本体が握り、ここからは観測できない。
  MCP には緑赤の健全性バッジを付けず「設定上つながっている」表示に留める。
- **秘密を載せない。** 監査ログの HMAC 鍵など（workspace の config）は一切ダッシュボードに出さない。
  `build_env.py` は config を読まない実装になっている。
- **免責を明記。** 生成時点のスナップショットであること、確実な現在値は本体 `/config`・`/mcp`・
  `/permissions` で見ることを画面内に出す。

## ワークフロー

### Step 0: 動作環境ガード

```bash
python3 skills/_lib/workspace.py check --require local_fs
```

exit code が 2（HTML をファイル出力できない環境、例: 一部の Cowork）なら、stdout の友好的メッセージを
そのままユーザーに提示し、**HTML 生成はスキップして Step 1 のデータをテキスト要約で提示する**
（下記「予備表示」）。

### Step 1: 環境データの収集と `.agent` 生成

```bash
python3 skills/env/build_env.py
```

`build_env.py` は `claude auth status --json` / `claude plugin list --json` /
`workspace.py info` / `audit.py verify` / 有効プラグインの `mcpServers` を集め、描画エンジン入力
`env_dashboard_{YYYY-MM-DD}.agent` を現在の案件フォルダに書き、そのパスを stdout に出す。
どのコマンドが失敗しても落とさず「確認できず」で続行する。

### Step 1.5: （任意・予備表示）外部ツール連携対応ホストでの in-chat 描画

```bash
python3 skills/_lib/agent_html/build_html.py host   # inline か cli を判定
```

`inline`（Claude Desktop / Cursor 等）のときのみ、`mcp__agent-format__render_agent_file` に
Step 1 の `.agent` を渡して in-chat インライン描画する。**必ず Step 2 の build より前**に行う
（build で `.agent` を削除するため）。`cli` のときはスキップ。

### Step 2: 自己完結 HTML の生成・自動表示

```bash
python3 skills/_lib/agent_html/build_html.py build --input env_dashboard_{YYYY-MM-DD}.agent --open --prune-agent
```

出力 `env_dashboard_{YYYY-MM-DD}.html`（唯一の成果物。6 セクション: いまの状態 / まず確認 /
できること / つながっている外部の道具 / 守り / この画面の見かた）。`--open` は既定ブラウザで自動表示
（開けない環境はパス表示にフォールバック）、`--prune-agent` は使い捨ての `.agent` を削除する。

### Step 3: 監査ログ

```bash
python3 skills/_lib/audit.py record --skill env --event file_write --file "env_dashboard_{YYYY-MM-DD}.html"
```

### Step 4: ユーザーへの案内（です・ます調）

```
今の環境の状態を env_dashboard_{YYYY-MM-DD}.html にまとめ、ブラウザで開きました。

  ・特別なソフトは不要です。自動で開かなかった場合もダブルクリックで開けます。
  ・「まず確認」に🟡が出ていたら、その内容をご確認ください。
  ・実際に適用されている権限や通信の状態など、この画面で分からない項目は、
    Claude Code 本体の /config・/mcp・/permissions でご確認いただけます。
  ・この画面は外部と通信しません。ただし拡張構成や案件名が載るため、共有の前に内容をご確認ください。
```

### 予備表示（local_fs が無い環境）

`build_env.py` の出力（`.agent` の JSON）から、案件・プラン・拡張数・記録件数・つながっている外部ツール・
守り・限界を**テキストで**要約して提示する。HTML は生成しない。

## セキュリティ

- `build_env.py` は workspace の config（HMAC 鍵等の秘密）を読まない。ダッシュボードに秘密は出ない。
- 生成物 HTML は `connect-src 'none'` の CSP により外部送信不能（弁護士法23条 守秘義務）。
- 環境情報（拡張構成・案件名・パス）を平文 HTML に集約するため、共有前の確認をユーザーに促す。

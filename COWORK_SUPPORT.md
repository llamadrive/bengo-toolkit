# Cowork 対応マトリクス

bengo-toolkit は Claude Code（CLI / Mac/Windows デスクトップアプリ）と
Claude Cowork の両方にインストール可能だが、Cowork は sandboxed VM 上で動作
するため一部の機能はローカル機能（ローカル MCP・ローカル FS）を必要とし、
利用できない。

本ファイルは **「どの skill がどの surface で動くか」の単一の真実点（SSOT）**。
スキル frontmatter にこの情報は持たせない（doc-only field は腐るため）。

## 判定方法

### 仕組み

- `skills/_lib/runtime.py`（import-only モジュール）が surface を判定する。
- 判定優先順位:
  1. 環境変数 `CLAUDE_CODE_IS_COWORK=1` → cowork（fast path）
  2. capability probe（`~/.claude-bengo/` への書込テスト）
- ユーザー向け CLI は `workspace.py surface` / `workspace.py check --require <cap>`。
- exit code: `0` = ok, `2` = blocked-by-surface（stdout に日本語の友好的メッセージ）, `1` = その他のエラー。

### Capability ラベル

| Cap | 必要なもの |
|---|---|
| `local_fs` | `~/.claude-bengo/` 配下に書込可能（workspace・templates・audit ログ） |
| `docx_mcp` | `mcp__docx-editor__*`（ローカル stdio MCP） |
| `xlsx_mcp` | `mcp__xlsx-editor__*` |
| `pptx_mcp` | `mcp__pptx-editor__*` |
| `agent_format_mcp` | `mcp__agent-format__*`（.agent ファイル描画） |

Cowork では上記いずれも利用不可。

## 全 23 command の対応表

★ = Cowork でも動作 / ✗ = Cowork で blocked（Claude Code 限定）

### 計算系（決定論的）

| Command | Cowork | 必要 capability |
|---|:---:|---|
| `/inheritance-calc` | ★ | なし（純計算） |
| `/child-support-calc` | ★ | なし（audit は best-effort、Cowork で silent skip） |
| `/iryubun-calc` | ★ | 同上 |
| `/traffic-damage-calc` | ★ | 同上 |
| `/overtime-calc` | ★ | 同上 |
| `/property-division-calc` | ★ | 同上 |
| `/debt-recalc` | ★ (※) | XLSX 入力 branch のみ `xlsx_mcp` 必要。インライン入力なら動作 |

(※) `/debt-recalc` は対話入力で動作するが、XLSX ファイルからの取引履歴
読込を選んだ場合のみ `xlsx_mcp` ガードが発火する。

### 検索

| Command | Cowork | 備考 |
|---|:---:|---|
| `/law-search` | ★ | 条文取得（`fetch-article`）は Cowork で WebFetch fallback に切替。条見出しキーワード検索（`search-keyword`）は **Cowork 未対応**（全文 XML 1-5MB の DL 不可）。代替: 条番号がわかれば `fetch-article` で取得、または `references/law-id-list.tsv` の Grep（Cowork でも動作）。 |

### ドキュメント処理

| Command | Cowork | 必要 capability |
|---|:---:|---|
| `/typo-check` | ✗ | `local_fs` + `docx_mcp` |
| `/family-tree` | ✗ | `local_fs` + `agent_format_mcp` |
| `/lawsuit-analysis` | ✗ | `local_fs` + `docx_mcp` + `agent_format_mcp` |

### テンプレート

| Command | Cowork | 必要 capability |
|---|:---:|---|
| `/template-install` | ✗ | `local_fs` |
| `/template-list` | ✗ | `local_fs` |
| `/template-create` | ✗ | `local_fs` + `xlsx_mcp` |
| `/template-fill` | ✗ | `local_fs` + `xlsx_mcp` |
| `/template-promote` | ✗ | `local_fs` |
| `/template-demote` | ✗ | `local_fs` |
| `/template-firm-setup` | ✗ | `local_fs` |

### 案件フォルダ管理

| Command | Cowork | 必要 capability |
|---|:---:|---|
| `/audit-config` | ✗ | `local_fs` |
| `/case-info` | ✗ | `local_fs` |
| `/verify` | ✗ | `local_fs` + 全 MCP |

### メニュー

| Command | Cowork | 備考 |
|---|:---:|---|
| `/help` | ★ | `menu.py` が surface に応じてメニューを render（blocked skill は非表示 / `--all` で "Claude Code 限定" マーク） |
| `/quickstart` | ★ | 同上。Cowork では 条文検索デモ + 法定相続分計算デモのみ表示 |

## 友好的エラーメッセージ

`workspace.py check --require <cap>` が `exit 2` を返した場合、stdout に以下
形式の日本語メッセージが出力される。SKILL.md / commands は **これをそのまま
ユーザーへ表示し停止する**（編集・要約禁止）:

```
この機能は <必要 capability の和訳> を必要とするため、Claude Cowork からは利用できない。

Claude Code（CLI または Mac/Windows デスクトップアプリ）で同じプラグインを
使えば全機能が動作する。
  入手: https://claude.com/code
  追加: /plugin marketplace add anthropics/bengo-toolkit

Cowork でも動作する機能:
  ・計算系（残業代・養育費・遺留分・財産分与・相続・交通事故・婚姻費用）
  ・/law-search（条文取得）
```

## 自然言語マッチング時の扱い

CLAUDE.md の「自然言語からの機能マッチング」セクションで blocked skill が
match した場合も、同じ `workspace.py check --require <cap>` を経由する。
exit 2 なら stdout を user に見せて停止する。slash command と自然言語の
どちらでも整合性の取れた UX を保つ。

## メンテナンス

新しい skill を追加するとき:

1. その skill が必要とする capability を本ファイルに追記する
2. blocked skill なら `commands/{name}.md` に `## Step 0: 動作環境ガード`
   ブロックを追加する（既存パターンを踏襲）
3. `skills/_lib/menu.py` の `ALL_COMMANDS` / `HELP_CATEGORIES` /
   `QUICKSTART_OPTIONS` に surface ラベル付きで追加する
4. `tests/cowork_gating.sh` / `tests/menu_surface.sh` の対象に追加する

`runtime.py` 自体は通常変更不要である。

## 設計ノート

- **`CLAUDE_CODE_IS_COWORK` は undocumented な Anthropic 内部 signal** で、
  rename されると silent に壊れる。これを受けて capability probe
  （`~/.claude-bengo/` への 1 度の書込テスト）も併用しており、env var が
  消えても FS 書込が通らない surface は cowork として degrade する。
- **runtime.py は import-only** にしてある。Bash CLI を新設すると各 command
  の `allowed-tools` を全部書き換える必要が出るため。surface check の
  ユーザー向け CLI は既に大半の command の allowed-tools に載っている
  `workspace.py` のサブコマンドとして実装した（`workspace.py surface` /
  `workspace.py check --require <cap>`）。
- **`/help` `/quickstart` は `menu.py` が render する**。Markdown 内の条件
  分岐（"if cowork then hide X"）は Claude の解釈が非決定的なため、Python
  が直接出力する形にして決定論的にした。テストも `grep -E` で blocked
  skill 名が漏れていないかを assert する。

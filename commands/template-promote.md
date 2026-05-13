---
description: 「この案件のみ」に登録したテンプレートを「この PC の全案件で共通」へ移動する（他の案件からも使えるようにする）
allowed-tools: Read, Bash(python3 skills/_lib/template_lib.py:*), Bash(python3 skills/_lib/workspace.py:*), Bash(python3 skills/_lib/pii_scan.py:*)
---

現在の案件フォルダに登録されたテンプレートを「この PC の全案件で共通」（既定）または
「事務所共有」に**移動**する（元の案件側からは削除）。移動後は他の案件からも
`/template-fill` で選択できるようになる。

$ARGUMENTS:
- テンプレート ID（必須）
- `--to user` — 「この PC の全案件で共通」（既定）
- `--to firm` — 「事務所共有」（要 `/template-firm-setup`）
- `--replace` で移動先の既存を上書き

## 典型的なユースケース

案件 A のために登録した独自書式が、他の案件でも使えると気づいたとき。移動すれば
案件 A 側からも消え、「この PC の全案件で共通」の 1 本に統合される。

## ワークフロー

### Step 0: 動作環境ガード

```
Bash: python3 skills/_lib/workspace.py check --require local_fs
```

- exit 0 → Step 1 へ
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

### Step 1: 現状確認

```bash
python3 skills/_lib/workspace.py templates
```

戻り値 JSON の `case` 配列に対象 ID が存在するか確認する。無ければ
「この案件フォルダに `{id}` はない。`/template-list` で確認してほしい」と案内。

### Step 2: 事前の個人情報確認（必須・ハードブロック）

**「この PC の全案件で共通」へ移動するとこの PC 上の全案件から見えるため、クライアントの
個人情報が残っていないか先に確認する必要がある。** 対象 XLSX に個人情報のような
記述が含まれないかをスキャンする:

```bash
python3 skills/_lib/pii_scan.py scan --xlsx "<対象の xlsx_path>" --json
```

- `verdict: "clean"` → Step 3 へ進む
- `verdict: "suspicious"` → **v3.3.0〜 昇格を拒否する**（ユーザー override 不可）:

```
⛔ テンプレート '{id}' の移動を中止した。
   クライアントの個人情報のような記述が {N} 件検出されたため:
  - B3 [氏名]: 「甲野太郎様」
  - D7 [住所]: 「〒100-0001 東京都千代田区...」

次のいずれかを選んでほしい:
  1. 案件側の XLSX を開いて該当箇所を削除 → 再実行
  2. 移動をあきらめて「この案件のみ」のまま使い続ける
```

本コマンドは個人情報検出時に **スキャン結果のみを提示して終了** する。ユーザーが
「構わないから移動して」と言っても実行しない（個人情報を残したまま PC 全体に
広げるのは守秘義務違反に直結するため）。どうしても移動させたい場合は
XLSX 側を先に修正してから再実行してほしい。

**開発者・CI 専用バックドア（ユーザーに案内しないこと）:** 環境変数
`CLAUDE_BENGO_ALLOW_PII_ON_GLOBAL=1` で PII findings を無視して昇格できる。
テスト・CI 用の escape hatch で、通常運用では設定しない。

### Step 3: 昇格実行

```bash
python3 skills/_lib/template_lib.py promote <id>
# 上書きが必要なら: python3 skills/_lib/template_lib.py promote <id> --replace
```

**PII は code レベルで強制される（v3.3.0-iter1〜）:** promote_template() が
内部で pii_scan を呼び、findings>0 なら exit 4 で終了する。Step 2 を実行しても
しなくても、最終的に code-gate が通らなければ昇格は起こらない。

戻り値 JSON:
```json
{
  "id": "...", "src_scope": "case", "dst_scope": "user",
  "src_yaml": "...", "src_xlsx": "...",
  "dst_yaml": "~/.claude-bengo/templates/{id}.yaml",
  "dst_xlsx": "~/.claude-bengo/templates/{id}.xlsx",
  "replaced": "False", "kept_original": "False", "delete_failed": "False"
}
```

exit 4 時のエラー JSON:
```json
{"error": "...", "code": "pii_found", "findings": [...], "total_findings": 5}
```

### Step 4: 完了案内

戻り値 JSON の `delete_failed` を必ずチェックする。

**`delete_failed: "False"` の通常ケース:**

```
テンプレート '{id}' を「この PC の全案件で共通」へ移動した。
  移動先: ~/.claude-bengo/templates/{id}.{yaml,xlsx}
  元の案件側: 削除済み（共通領域が唯一のコピー）

以降この PC のどの案件フォルダからでも /template-fill で選択できる。
特定の案件だけカスタマイズしたくなったら /template-demote を使う。
```

**`delete_failed: "True"` の場合（コピーは成功したが元の案件側の削除に失敗）:**

```
⚠ テンプレート '{id}' は移動先へのコピーは成功したが、案件側の削除に失敗した。
  共通領域: ~/.claude-bengo/templates/{id}.{yaml,xlsx} ✅ 新規配置
  案件側:   {src_yaml} ⚠ 残存（手動削除が必要）

現在 /template-fill は **案件側を優先** するため、このまま放置すると
移動が実質反映されない。以下のいずれかで解決してほしい:
  1. 案件側ファイルを手動で削除してから /template-fill を使う
  2. 権限問題であれば解決後、/template-promote {id} --replace を再実行
  エラー詳細: {delete_error}
```

### エラーハンドリング

- 移動先に同 ID がある → `exit 3`。`--replace` 併用を確認
- 対象 ID が案件側にない → `exit 1`。案件側の登録有無を確認
- 無効な ID 形式 → `exit 1`。パストラバーサル防御のため拒否

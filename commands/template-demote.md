---
description: 共通領域のテンプレートを現在の案件フォルダにコピーする（この案件だけ微修正したいとき）
allowed-tools: Read, Bash(python3 skills/_lib/template_lib.py:*), Bash(python3 skills/_lib/workspace.py:*)
---

「この PC の全案件で共通」または「事務所共有」にあるテンプレートを、現在の案件フォルダの
`.claude-bengo/templates/` に **コピー**する（コピー元は残す）。これにより
`/template-fill` はこの案件では案件側を優先的に使う。他の案件は従来どおり
共通領域のテンプレートを参照する。

$ARGUMENTS:
- テンプレート ID（必須）
- `--from user` — 「この PC の全案件で共通」（`~/.claude-bengo/templates/`）からコピー（既定）
- `--from firm` — 「事務所共有」（要 `/template-firm-setup`）からコピー
- `--replace` で案件側の既存を上書き

## 典型的なユースケース

PC 全案件で使う標準書式を、この事件に限り一部カスタマイズしたい場合（項目追加・
文言差し替え等）。共通領域のものを直接いじると全案件に波及してしまうため、案件
フォルダにコピーしてそれを編集する。

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

`user` 配列に対象 ID があるか確認する。無ければ「「この PC の全案件で共通」に
`{id}` はない。`/template-install` で同梱書式から入れるか、`/template-create` で
新規登録してほしい」と案内。

### Step 2: 降格実行

```bash
python3 skills/_lib/template_lib.py demote <id>
# case 側に既存があれば: python3 skills/_lib/template_lib.py demote <id> --replace
```

戻り値 JSON（抜粋）:
```json
{
  "id": "...", "src_scope": "user", "dst_scope": "case",
  "dst_yaml": "<workspace>/.claude-bengo/templates/{id}.yaml",
  "replaced": "False", "kept_original": "True"
}
```

### Step 3: 完了案内

```
テンプレート '{id}' をこの案件フォルダにコピーした（共通領域はそのまま残す）。
  コピー先: <案件フォルダ>/.claude-bengo/templates/{id}.{yaml,xlsx}
  共通領域: 従来どおり（他案件に影響なし）

この案件では案件側のテンプレートが優先的に使われる。YAML / XLSX を
自由に編集してよい。変更を PC 全体に反映したくなったら /template-promote
で移動（共通領域の既存は上書きされる点に注意）。
```

### エラーハンドリング

- 案件側に同 ID がある → `exit 3`。`--replace` 併用を確認
- 対象 ID が共通領域にない → `exit 1`

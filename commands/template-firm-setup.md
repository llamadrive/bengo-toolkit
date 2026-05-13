---
description: 「事務所共有」のテンプレート保存フォルダを設定する（クラウド同期されているフォルダを指定）
allowed-tools: Bash(python3 skills/_lib/workspace.py:*)
---

事務所全員で共有するテンプレートディレクトリのローカルパスを設定する。本プラグインは
クラウドサービスに直接アップロードしない。設定されたローカルディレクトリを読み書きする
だけで、実体の同期はあなたの PC 上で動いている同期アプリ（Google Drive / Dropbox /
OneDrive / 社内 SMB マウント等）が担当する。

$ARGUMENTS:
- パス（必須、`--unset` を除く）— クラウド同期アプリが PC 上にマウントしているローカルディレクトリ
- `--unset` — 既存設定を削除する

## Step 0: 動作環境ガード

```
Bash: python3 skills/_lib/workspace.py check --require local_fs
```

- exit 0 → 次の Step へ進む
- exit 2 → stdout の日本語メッセージをそのままユーザーへ表示して停止
- exit 1 → stderr の error JSON をユーザーに伝えて停止

## 典型的なセットアップ

事務所の管理担当が一度だけ:

1. Google Shared Drive（または社内 SMB / Dropbox 共有フォルダ）に
   `事務所/法人テンプレート/` のようなフォルダを作る
2. 事務所メンバー全員にアクセス権を付与
3. 各メンバーが自分の PC で同期アプリを起動し、フォルダがローカルにマウント
   されることを確認（macOS なら `~/Library/CloudStorage/GoogleDrive-.../Shared drives/...`）

各メンバーが一度だけ:

```
/template-firm-setup ~/Library/CloudStorage/GoogleDrive-xxx@firm.jp/Shared\ drives/事務所/法人テンプレート
```

## ワークフロー

### Step 1: パス検証 + 設定書込

```bash
python3 skills/_lib/workspace.py firm-setup "<absolute path>"
```

戻り値 JSON:
```json
{
  "ok": true,
  "firm_templates_path": "/path/to/folder",
  "readme_created": true,
  "message": "firm スコープを ... に設定した。"
}
```

エラーケース（exit 1）:
- パスが存在しない → 「クラウド同期アプリが起動していて、フォルダが PC 上にマウントされているか確認してほしい」と案内
- ディレクトリではない（ファイル等）→ 「ファイルではなくフォルダを指定してほしい」と案内
- `~/.claude-bengo/` 配下を指定 → 「「この PC の全案件で共通」の領域と混線するので不可」と案内

### Step 2: 完了案内

設定成功後、以下を案内する:

```
「事務所共有」の保存フォルダを設定した: {path}

以降:
  /template-list                       — 全保存場所のテンプレートを一覧
  /template-create --scope firm        — このフォルダに新規テンプレートを登録（個人情報検出時は拒否）
  /template-install <id> --scope firm  — 同梱書式を「事務所共有」にインストール
  /template-promote <id> --to firm     — この案件のみ → 事務所共有 へ移動（管理担当向け）
  /template-demote <id> --from firm    — 事務所共有 → この案件のみ にコピー（特定案件だけカスタマイズ）

注意: このフォルダにはクライアントの個人情報を含むファイルを置かないこと。事務所全員から見える。
個人情報のスキャンは移動・保存時に自動的にかかる（検出時は拒否）。
```

### Step 3: 設定削除（`--unset`）

```bash
python3 skills/_lib/workspace.py firm-setup --unset
```

戻り値:
```json
{"unset": true, "message": "firm スコープ設定を削除した。"}
```

削除後は「事務所共有」が未設定状態に戻り、テンプレート解決は「この案件のみ」と
「この PC の全案件で共通」の 2 つだけになる。

## 状態確認

```bash
python3 skills/_lib/workspace.py firm-status
# → {"state": "unconfigured" | "unreachable" | "reachable", "path": "..."}
```

- `unconfigured` — まだ設定されていない
- `unreachable` — 設定済みだが現在パスにアクセスできない（同期アプリ未起動、フォルダ削除等）
- `reachable` — 正常

## エラーハンドリング

- `unreachable` 状態で `/template-fill` が走った場合、「事務所共有」を黙ってスキップして
  「この案件のみ」→「この PC の全案件で共通」の順で解決する。両方にも対象テンプレートが
  無く、事務所共有にだけあるような状況は次回詳細な案内メッセージを出す予定。

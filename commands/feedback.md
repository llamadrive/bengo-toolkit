---
description: 不具合の報告・機能の要望をフォームから送る（GitHub アカウント不要）。/report-issue のエイリアス
allowed-tools: Read, Write, Bash(python3 skills/_lib/report.py:*), Bash(python3 skills/_lib/workspace.py:*)
---

`/report-issue` のエイリアス。bengo-toolkit に対する不具合の報告・機能の要望・感想を、GitHub アカウントなしで送るための slash command。

`feedback` という語からこのコマンドを探す利用者が多いため、`/report-issue` と同じ動作をするエイリアスとして用意してある。挙動は `/report-issue` と完全に同一。

$ARGUMENTS の指定方法:
- 引数なし: 対話形式で種別と本文を聞く
- `--type bug` / `--type feature` / `--type other` を付けて起動すれば、その種別から開始する

## 動作の流れ

1. 利用者から種別（不具合 / 機能要望 / その他）と本文を聞き取る
2. プラグイン版・OS・実行環境などの自動診断情報を付けて、Markdown 形式の下書きを `~/.claude-bengo/reports/feedback_<日時>.md` に書き出す
3. その下書きを OS 既定のテキストエディタで開く（macOS は TextEdit、Windows はメモ帳、Linux は xdg-open）
4. llama-drive.com のフィードバックフォームを、ブラウザで開く（種別と診断情報は URL の query param で渡してフォーム側が自動入力する）
5. 利用者はエディタの本文を選択コピーし、フォームに貼り付けて、内容を確認してから送信する

**自動送信はしない。** プラグインがネットワーク越しに送信することはない。送信はあくまで利用者の手元で、ブラウザ経由で行う。

## Step 1

まず `skills/report-issue/SKILL.md` を Read ツールで読み込み、そこに記載された手順に従って実行する。

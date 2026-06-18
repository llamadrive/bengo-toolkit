#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`.agent` から自己完結 HTML を組み立てる（弁護士向けの成果物）。

第三者ビューアもネットワークも使わず、すべて（描画エンジン・スタイル・データ）
を 1 つの `.html` に inline する。ダブルクリックで開け、メールに添付でき、
ブラウザの ⌘P で裁判所提出用 PDF にできる。`connect-src 'none'` の CSP により
ファイルは外部送信不能（弁護士法23条 守秘義務）。

使い方:
    python3 build_html.py build --input family_tree_YYYY-MM-DD.agent
    python3 build_html.py build --input X.agent --open --prune-agent
    python3 build_html.py host          # 描画ホスト判定: 'cli' か 'inline'

成果物は常に `.html`。`--open` は既定ブラウザで自動的に開き（開けない環境では
自動でパス表示にフォールバック）、`--prune-agent` は内部入力の `.agent` を削除して
ユーザーに残るのを `.html` だけにする。`.agent` はユーザーに残さない使い捨ての
描画エンジン入力である。

`host` サブコマンドは描画ホストを判定する。外部ツール連携対応ホスト
（Claude Desktop / Cursor 等、$CLAUDECODE 未設定）では `inline` を返す。
呼び出し側は `--prune-agent` で `.agent` を消す前に、`render_agent_file` で
in-chat のインライン描画を行える（ブラウザを開けないホスト向けの予備表示）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
SHELL = HERE / "shell.html"
BUNDLE = DIST / "renderer_bundle.js"
STYLES = DIST / "renderer_styles.css"


def host_mode() -> str:
    """'cli' = HTML のみ / 'inline' = .agent も出して MCP Apps で描画。"""
    return "cli" if os.environ.get("CLAUDECODE") == "1" else "inline"


def _escape_html_text(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(agent_path: Path, out_path: Path) -> Path:
    """`.agent` を読み、自己完結 HTML を out_path に書き出す。"""
    for asset in (SHELL, BUNDLE, STYLES):
        if not asset.exists():
            raise SystemExit(
                f"エラー: 描画エンジンの部品が見つからない: {asset.name}\n"
                f"  開発者向け: cd {HERE} && npm install && npm run build で再生成する。"
            )

    raw = agent_path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"エラー: .agent が有効な JSON ではない: {e}")

    title = data.get("name") or agent_path.stem

    replacements = {
        "TITLE": _escape_html_text(title),
        "STYLES": STYLES.read_text(encoding="utf-8"),
        # JSON を <script type="application/json"> へ安全に inline する。'<' を
        # < に逃がし、</script> によるパーサ・ブレイクアウトを防ぐ
        # （JSON としても JS としても valid なまま）。
        "AGENT_JSON": json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"),
        # バンドル内の文字列リテラルに </script>（大小無視）が含まれても HTML
        # パーサが途中で閉じないよう無害化する（JS としては等価）。
        "BUNDLE": re.sub(
            r"</script",
            r"<\\/script",
            BUNDLE.read_text(encoding="utf-8"),
            flags=re.IGNORECASE,
        ),
    }

    # 単一パスで置換する。置換後テキストを再走査しないため、untrusted データ
    # （戸籍 PDF 由来）に %%BUNDLE%% 等のトークンが混入しても後段の置換を壊さ
    # ない。置換に関数を渡すので、挿入文字列内の \1 等もバックリファレンスと
    # 解釈されない。
    html = re.sub(
        r"%%(TITLE|STYLES|AGENT_JSON|BUNDLE)%%",
        lambda m: replacements[m.group(1)],
        SHELL.read_text(encoding="utf-8"),
    )

    out_path.write_text(html, encoding="utf-8")
    return out_path


def _open_local(path: Path) -> None:
    """既定ブラウザでローカル HTML を開く。失敗してもパス表示で続行する。"""
    url = path.resolve().as_uri()
    try:
        if webbrowser.open(url, new=2):
            return
    except Exception:  # noqa: BLE001 — 環境依存で webbrowser が例外を投げ得る
        pass
    print(f"自動で開けなかった。次のファイルを手動で開いてほしい: {path}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="自己完結 HTML を生成する")
    p_build.add_argument("--input", required=True, help=".agent ファイルのパス")
    p_build.add_argument("--output", help="出力 .html（既定: 入力と同名 .html）")
    p_build.add_argument(
        "--open",
        action="store_true",
        help="生成後、既定ブラウザでローカル HTML を自動的に開く（開けなければパス表示にフォールバック）",
    )
    p_build.add_argument(
        "--prune-agent",
        action="store_true",
        help="生成後、内部入力の .agent を削除し、ユーザーに残るのを .html だけにする",
    )

    sub.add_parser("host", help="描画ホストを判定し cli|inline を出力する")

    args = ap.parse_args()

    if args.cmd == "host":
        print(host_mode())
        return 0

    agent_path = Path(args.input)
    if not agent_path.exists():
        print(f"エラー: ファイルが見つからない: {agent_path}", file=sys.stderr)
        return 1

    out = Path(args.output) if args.output else agent_path.with_suffix(".html")
    if out.resolve() == agent_path.resolve():
        print("エラー: 出力先が入力 .agent と同一パスである。", file=sys.stderr)
        return 1
    build_html(agent_path, out)
    print(str(out))

    if args.open:
        _open_local(out)
    if args.prune_agent and agent_path.resolve() != out.resolve():
        agent_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

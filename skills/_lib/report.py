#!/usr/bin/env python3
"""report.py — フィードバック報告の下書きを書き出し、ブラウザフォームを開く。

`/report-issue` skill 用のヘルパー。次の手順で動作する:

1. 利用者が記入した本文（ファイル経由で渡す）と、自動取得したプラグイン版・
   OS・surface・実行可能診断などを統合し、Markdown のレポートを
   `~/.claude-bengo/reports/feedback_<timestamp>.md` に書き出す。
2. その Markdown ファイルを OS 規定のテキストエディタで開く（TextEdit /
   Notepad / xdg-open）。利用者は内容を選択コピーする。
3. llama-drive.com の Web フォームを、type / version / os / surface の
   query param 付きでブラウザで開く。利用者はテキストを貼り付けて送信する。

設計上の注意:
- 自動送信はしない。利用者が必ずブラウザで確認・編集・送信する。
- ファイル名・パス・コマンド引数など、個人情報を含みうる文字列は
  自動収集しない。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

FEEDBACK_FORM_URL = "https://llama-drive.com/bengo-toolkit/feedback"
REPORTS_DIRNAME = ".claude-bengo/reports"
ALLOWED_TYPES = ("bug", "feature", "other")


def _plugin_root() -> Path:
    """skills/_lib/ から見たプラグインルート。"""
    return Path(__file__).resolve().parent.parent.parent


def _plugin_version() -> str:
    """.claude-plugin/plugin.json の version を読む。失敗時は 'unknown'。"""
    try:
        p = _plugin_root() / ".claude-plugin" / "plugin.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        v = data.get("version")
        if isinstance(v, str) and v:
            return v
    except Exception:
        pass
    return "unknown"


def _surface() -> str:
    """surface 判定（runtime.py がある場合はそれを使う）。"""
    here = str(Path(__file__).resolve().parent)
    added = False
    if here not in sys.path:
        sys.path.insert(0, here)
        added = True
    try:
        import importlib

        rt = importlib.import_module("runtime")
        return rt.surface()
    except Exception:
        return "unknown"
    finally:
        if added:
            try:
                sys.path.remove(here)
            except ValueError:
                pass


def _os_label() -> str:
    """`darwin 25.3.0` / `windows 10.0.22631` 等の短い OS ラベル。"""
    system = platform.system().lower() or "unknown"
    release = platform.release() or ""
    return f"{system} {release}".strip()


def _output_path() -> Path:
    """書き出し先パスを返す。同名衝突時は `_2`, `_3` … を付与。"""
    home = Path.home()
    base = home / REPORTS_DIRNAME
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = base / f"feedback_{ts}.md"
    i = 2
    while candidate.exists():
        candidate = base / f"feedback_{ts}_{i}.md"
        i += 1
    return candidate


def _open_in_editor(path: Path) -> bool:
    """OS 規定のテキストエディタで開く。成功なら True。"""
    try:
        system = platform.system().lower()
        if system == "darwin":
            # TextEdit を明示指定。`open <file>` だと拡張子で別アプリに飛ぶ。
            subprocess.Popen(
                ["open", "-a", "TextEdit", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        if system == "windows":
            # メモ帳で開く。`os.startfile` でも開けるが、拡張子の関連付けに
            # 依存して別アプリが立ち上がる事故を避けるため notepad 明示。
            subprocess.Popen(
                ["notepad.exe", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        # Linux / その他 — xdg-open 経由（GNOME Text Editor / kate / vi 等）
        if shutil.which("xdg-open"):
            subprocess.Popen(
                ["xdg-open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
    except Exception:
        pass
    return False


def _open_in_browser(url: str) -> bool:
    """既定のブラウザでフォーム URL を開く。成功なら True。

    Claude Code CLI 以外（SSH / CI など）では失敗することがあるため、
    呼び出し側は URL を必ず stdout にも印字すること。
    """
    try:
        system = platform.system().lower()
        if system == "darwin":
            subprocess.Popen(
                ["open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        if system == "windows":
            # `os.startfile` で URL を開ける。
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        if shutil.which("xdg-open"):
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
    except Exception:
        pass
    return False


def _build_form_url(report_type: str, version: str, os_label: str, surface: str) -> str:
    """フォーム URL に diagnostic を query param として乗せる。

    本文は乗せない（URL 長制限 + ブラウザ履歴漏洩を避ける）。利用者は
    エディタで開いたファイルから手動で貼り付ける。
    """
    params = {
        "type": report_type,
        "version": version,
        "os": os_label,
        "surface": surface,
    }
    return f"{FEEDBACK_FORM_URL}?{urlencode(params)}"


def _render_report(
    report_type: str,
    title: str,
    body: str,
    version: str,
    os_label: str,
    surface: str,
) -> str:
    """書き出すレポートの本体を組み立てる。"""
    ts = datetime.now().isoformat(timespec="seconds")
    type_label = {
        "bug": "不具合の報告",
        "feature": "機能の要望",
        "other": "その他のフィードバック",
    }.get(report_type, "フィードバック")

    lines = [
        f"# {type_label}",
        "",
        f"- 件名: {title or '(未記入)'}",
        f"- 種別: {report_type}",
        f"- 生成日時: {ts}",
        f"- プラグイン版: {version}",
        f"- OS: {os_label}",
        f"- 実行環境: {surface}",
        "",
        "---",
        "",
        "## 本文",
        "",
        body.rstrip() or "(本文未記入)",
        "",
        "---",
        "",
        "## 送信方法",
        "",
        "1. 上の本文を **全選択コピー**（macOS: ⌘A → ⌘C / Windows: Ctrl+A → Ctrl+C）",
        "2. 自動で開いたブラウザのフォーム本文欄に貼り付ける",
        "3. 機密情報（事務所名・依頼者名・案件番号・PDF 本文の引用等）が含まれていないか",
        "   読み直して必要なら削除する",
        "4. 「送信する」ボタンを押す",
        "",
        "ブラウザが開かなかった場合のフォーム URL:",
        "",
    ]
    return "\n".join(lines)


def cmd_emit(args: argparse.Namespace) -> int:
    """報告を書き出してエディタ + ブラウザを開く。"""
    if args.type not in ALLOWED_TYPES:
        print(
            json.dumps(
                {"error": f"--type は {ALLOWED_TYPES} のいずれかを指定してほしい"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    body = ""
    if args.body_file:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except OSError as e:
            print(
                json.dumps({"error": f"本文ファイルが読めない: {e}"}, ensure_ascii=False),
                file=sys.stderr,
            )
            return 1
    elif not sys.stdin.isatty():
        body = sys.stdin.read()

    if not body.strip():
        print(
            json.dumps(
                {"error": "本文が空。--body-file または stdin で本文を渡してほしい"},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    version = _plugin_version()
    os_label = _os_label()
    surface = _surface()
    form_url = _build_form_url(args.type, version, os_label, surface)

    report = _render_report(
        report_type=args.type,
        title=args.title or "",
        body=body,
        version=version,
        os_label=os_label,
        surface=surface,
    )
    # フォーム URL を末尾に貼り、テキストエディタからも辿れるようにする。
    report = f"{report}\n{form_url}\n"

    out = _output_path()
    out.write_text(report, encoding="utf-8")

    editor_opened = _open_in_editor(out) if not args.no_open else False
    browser_opened = _open_in_browser(form_url) if not args.no_open else False

    print(
        json.dumps(
            {
                "output_path": str(out),
                "form_url": form_url,
                "editor_opened": editor_opened,
                "browser_opened": browser_opened,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _self_test() -> int:
    """軽量 self-test。書込・URL 構築のみ検証する（エディタ・ブラウザは開かない）。"""
    import tempfile

    failures: list[str] = []

    # URL 構築
    url = _build_form_url("bug", "3.7.7", "darwin 25.3.0", "code")
    if "type=bug" not in url or "version=3.7.7" not in url:
        failures.append(f"_build_form_url did not include params: {url}")

    # render
    rendered = _render_report(
        report_type="feature",
        title="hoge",
        body="本文サンプル",
        version="3.7.7",
        os_label="darwin",
        surface="code",
    )
    if "機能の要望" not in rendered or "本文サンプル" not in rendered:
        failures.append("rendered report missing expected sections")

    # emit dry-run via tmp file
    with tempfile.TemporaryDirectory() as tmpdir:
        body_file = Path(tmpdir) / "body.md"
        body_file.write_text("テスト本文", encoding="utf-8")
        ns = argparse.Namespace(
            type="bug",
            title="t",
            body_file=str(body_file),
            no_open=True,
        )
        rc = cmd_emit(ns)
        if rc != 0:
            failures.append(f"emit returned {rc}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("report.py self-test: all passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="bengo-toolkit feedback report writer")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="command")

    p_emit = sub.add_parser("emit", help="レポートを書き出してエディタ + ブラウザを開く")
    p_emit.add_argument("--type", required=True, choices=ALLOWED_TYPES)
    p_emit.add_argument("--title", default="")
    p_emit.add_argument("--body-file", help="本文を読み込むファイルのパス")
    p_emit.add_argument(
        "--no-open",
        action="store_true",
        help="エディタ・ブラウザを開かない（CI / SSH 用）。output_path と form_url のみ印字する",
    )
    p_emit.set_defaults(func=cmd_emit)

    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not getattr(args, "command", None):
        ap.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

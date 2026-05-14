#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`/help` `/quickstart` の決定論的メニュー出力。

Claude による markdown-conditional 解釈は非決定的なため、surface に応じた
メニューを Python が直接 render する。各 command の `.md` 本体は本スクリプトの
出力を verbatim にユーザーへ見せるだけにすることで:

- Cowork で blocked skill が menu に出ない（grep で deterministic に検証可能）
- 番号ずれを起こさない（surface ごとに番号付け直す）

CLI:

    menu.py print-help [args...]
    menu.py print-quickstart [args...]
    menu.py --self-test

modes:
    --plain     罫線・装飾なしの ASCII モード（pipe / 自動テスト用）
    NO_COLOR=1  同上
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# surface 判定
# ---------------------------------------------------------------------------


def _surface() -> str:
    """runtime.surface() を遅延 import で呼ぶ。"""
    import importlib
    here = str(Path(__file__).resolve().parent)
    added = False
    if here not in sys.path:
        sys.path.insert(0, here)
        added = True
    try:
        rt = importlib.import_module("runtime")
        return rt.surface()
    finally:
        if added:
            try:
                sys.path.remove(here)
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# 装飾
# ---------------------------------------------------------------------------


def _is_plain(args_plain: bool) -> bool:
    return args_plain or os.environ.get("NO_COLOR") == "1"


def _hr(plain: bool, char: str = "━", width: int = 38) -> str:
    return ("-" if plain else char) * width


def _box_top(plain: bool) -> str:
    return _hr(plain)


def _box_bottom(plain: bool) -> str:
    return _hr(plain)


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------


# (number_label, emoji, title, description, required_surface)
HELP_CATEGORIES: List[Tuple[str, str, str, str, str]] = [
    ("1", "[doc]" if False else "📄", "書類を作成する",
     "裁判所書式・訴状・示談書・陳述書・財産目録... を PDF から自動入力", "code"),
    ("2", "👨‍👩‍👧", "相続を整理する",
     "戸籍謄本から相続関係説明図、法定相続分を分数で計算、遺留分侵害額の算出",
     "mixed"),
    ("3", "✏️ ", "書面を校正する",
     "準備書面・契約書の誤字脱字、表記揺れ、法律用語を修正履歴付きでチェック", "code"),
    ("4", "⚖️ ", "訴訟文書を分析する",
     "訴状・答弁書・準備書面からタイムライン・当事者・認否を抽出しレポート生成", "code"),
    ("5", "🧮", "計算する",
     "養育費・婚姻費用、財産分与、交通事故損害賠償、残業代、引き直し計算", "any"),
    ("6", "📖", "法令を調べる",
     "e-Gov 法令 API で 2,078 法令の条文を検索・参照", "any"),
    ("7", "📁", "案件フォルダと監査を管理する",
     "フォルダ単位でテンプレート・監査ログ・出力物を分離管理", "code"),
]


# (cmd, oneliner, surface)
ALL_COMMANDS: List[Tuple[str, str, str]] = [
    # 案件フォルダ / workspace
    ("/case-info", "現在の案件フォルダの状態を表示", "code"),
    ("/audit-config", "監査ログ設定（記録先・HMAC・クラウド同期）", "code"),
    # テンプレート
    ("/template-install", "同梱書式から選択してインストール", "code"),
    ("/template-create", "独自 XLSX 書式を登録", "code"),
    ("/template-list", "登録済み書式の一覧", "code"),
    ("/template-fill", "PDF からデータを抽出して書式に自動入力", "code"),
    ("/template-promote", "案件書式を「この PC の全案件で共通」または「事務所共有」へ移動", "code"),
    ("/template-demote", "共通領域の書式を案件側へコピー", "code"),
    ("/template-firm-setup", "事務所共有テンプレート用フォルダを設定", "code"),
    # ドキュメント処理
    ("/family-tree", "戸籍から相続関係説明図を生成", "code"),
    ("/typo-check", "DOCX の誤字脱字・表記揺れ校正", "code"),
    ("/lawsuit-analysis", "訴状・答弁書から事件分析レポート生成", "code"),
    # 計算器
    ("/inheritance-calc", "法定相続分（民法）", "any"),
    ("/traffic-damage-calc", "交通事故損害賠償（赤い本基準）", "any"),
    ("/child-support-calc", "養育費・婚姻費用（令和元年方式）", "any"),
    ("/debt-recalc", "引き直し計算（利息制限法）", "any"),
    ("/overtime-calc", "未払残業代（労基法 37 条）", "any"),
    ("/iryubun-calc", "遺留分侵害額（民法 1042 条）", "any"),
    ("/property-division-calc", "離婚財産分与（民法 768 条）", "any"),
    # 検索
    ("/law-search", "法令条文を検索（e-Gov API 経由）", "any"),
    # メンテナンス
    ("/quickstart", "60 秒で試す（同梱サンプル）", "any"),
    ("/verify", "動作確認", "code"),
    ("/report-issue", "不具合の報告・機能の要望をフォームから送る（GitHub 不要）", "code"),
    ("/help", "このメニュー", "any"),
]


def _available_in_cowork(s: str) -> bool:
    """surface ラベルから cowork で利用可能かを返す。"""
    return s in ("any", "mixed")


def render_help(surface: str, plain: bool, args: List[str]) -> str:
    """`/help` 全文を返す。"""
    is_cowork = surface == "cowork"
    lines: List[str] = []
    sub = " ".join(args).strip()

    if sub == "--all":
        return _render_help_all(surface, plain)

    lines.append(_box_top(plain))
    if is_cowork:
        lines.append("  bengo-toolkit — 今日何をしたい？  [Cowork モード]")
    else:
        lines.append("  bengo-toolkit — 今日何をしたい？")
    lines.append(_box_top(plain))
    lines.append("")

    if is_cowork:
        lines.append("  Cowork 環境では計算系と法令検索のみ動作する。")
        lines.append("  ローカルファイル操作（書類作成・校正・戸籍解析）は")
        lines.append("  Claude Code（デスクトップ／CLI）でご利用いただきたい。")
        lines.append("")

    # Cowork では mixed (=相続) は inheritance-calc + iryubun-calc のみ表示する形に整理。
    counter = 1
    for label, emoji, title, desc, surf in HELP_CATEGORIES:
        if is_cowork and surf == "code":
            continue
        if is_cowork and surf == "mixed":
            # 戸籍読込は不可だが、相続分・遺留分計算は可能。
            lines.append(f"  {counter}. {emoji} {title}（一部のみ）")
            lines.append(f"     法定相続分・遺留分侵害額の計算（戸籍解析は Claude Code 限定）")
            counter += 1
            continue
        lines.append(f"  {counter}. {emoji} {title}")
        lines.append(f"     {desc}")
        counter += 1

    lines.append("")
    lines.append("  " + _hr(plain, "─", 34))
    if not is_cowork:
        lines.append("  ?. 初めて使う → /quickstart")
        lines.append("  ?. 全コマンド → /help --all")
        lines.append("  ?. 動作確認 → /verify")
        lines.append("  ?. 更新 → /plugin install bengo-toolkit@llamadrive")
    else:
        lines.append("  ?. 初めて使う → /quickstart")
        lines.append("  ?. 全コマンド → /help --all")
    lines.append("")
    lines.append(_box_bottom(plain))
    lines.append("")
    lines.append("番号を選ぶか、やりたいことを自由に書いてほしい。")

    return "\n".join(lines)


def _render_help_all(surface: str, plain: bool) -> str:
    is_cowork = surface == "cowork"
    lines: List[str] = []
    lines.append(_box_top(plain))
    lines.append("  全コマンド一覧" + ("  [Cowork: ★印のみ動作]" if is_cowork else ""))
    lines.append(_box_top(plain))
    lines.append("")

    if is_cowork:
        for cmd, oneliner, surf in ALL_COMMANDS:
            mark = "★" if _available_in_cowork(surf) else "  "
            note = "" if _available_in_cowork(surf) else "  （Claude Code 限定）"
            lines.append(f"  {mark} {cmd:24s} {oneliner}{note}")
    else:
        for cmd, oneliner, _surf in ALL_COMMANDS:
            lines.append(f"  {cmd:24s} {oneliner}")
    lines.append("")
    lines.append(_box_bottom(plain))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# /quickstart
# ---------------------------------------------------------------------------


# (option_label, title, detail, required_surface)
QUICKSTART_OPTIONS = [
    ("戸籍から相続関係説明図を描く",
     "サンプル戸籍 PDF から .agent を生成。ブラウザでツリー表示。", "code"),
    ("PDF から XLSX 書式へ自動入力",
     "訴状 PDF から当事者・事件番号・請求額を抽出し、書式の該当セルへ記入。", "code"),
    ("準備書面の校正（修正履歴付き）",
     "サンプル DOCX に対して Word 修正履歴で誤字・用語を指摘。", "code"),
    ("訴状と答弁書から事件分析レポート",
     "タイムライン・登場人物・認否を .agent で可視化。", "code"),
    ("条文を引く（民法709条）",
     "e-Gov API から条文を整形表示。案件登録不要・即動作。", "any"),
    ("法定相続分を計算（配偶者＋子3人、1人放棄）",
     "分数で正確に計算。案件登録不要・即動作。", "any"),
]


def render_quickstart(surface: str, plain: bool, args: List[str]) -> str:
    is_cowork = surface == "cowork"
    lines: List[str] = []
    lines.append(_box_top(plain))
    if is_cowork:
        lines.append("  bengo-toolkit を 60 秒で試す  [Cowork モード]")
    else:
        lines.append("  bengo-toolkit を 60 秒で試す")
    lines.append(_box_top(plain))
    lines.append("")
    if is_cowork:
        lines.append("  Cowork 環境で動くデモを表示する。")
        lines.append("  ローカル PDF/DOCX/XLSX を扱うデモは Claude Code でご利用いただきたい。")
        lines.append("")

    counter = 1
    for title, detail, surf in QUICKSTART_OPTIONS:
        if is_cowork and surf == "code":
            continue
        lines.append(f"  {counter}. {title}")
        lines.append(f"     → {detail}")
        counter += 1
        lines.append("")

    if is_cowork:
        lines.append("  全機能版を試す → https://claude.com/code（Claude Code）に")
        lines.append("                     bengo-toolkit を追加")
    else:
        lines.append("  番号を選ぶだけでよい。途中で止めたくなったら何もせずに抜けて構わない。")
    lines.append(_box_bottom(plain))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------


def _self_test() -> int:
    failures = []

    blocked_names = (
        "typo-check",
        "template-install",
        "template-fill",
        "template-create",
        "template-promote",
        "template-demote",
        "template-list",
        "template-firm-setup",
        "family-tree",
        "lawsuit-analysis",
        "audit-config",
        "case-info",
        "verify",
    )

    # /help in cowork must not list any blocked skill name.
    out_help = render_help("cowork", plain=True, args=[])
    for name in blocked_names:
        if name in out_help:
            failures.append(f"help (cowork) contains blocked name: {name}")

    # /quickstart in cowork must not list blocked workflow titles.
    out_qs = render_quickstart("cowork", plain=True, args=[])
    forbidden_qs = ("戸籍", "テンプレート", "校正", "訴訟分析", "訴状と答弁書", "PDF から XLSX")
    for f in forbidden_qs:
        if f in out_qs:
            failures.append(f"quickstart (cowork) contains forbidden item: {f}")

    # /help --all in cowork must include all but flag with "Claude Code 限定" for blocked.
    out_all = render_help("cowork", plain=True, args=["--all"])
    if "Claude Code 限定" not in out_all:
        failures.append("help --all (cowork) should annotate blocked skills")

    # In Code surface, /help should show everything.
    out_code = render_help("code", plain=True, args=[])
    if "書類を作成する" not in out_code:
        failures.append("help (code) should show full menu including 書類を作成する")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("menu.py self-test: all passed")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="bengo-toolkit menu renderer (surface-aware)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--plain", action="store_true", help="ASCII / 装飾なしモード")
    sub = ap.add_subparsers(dest="command")

    p_help = sub.add_parser("print-help", help="`/help` のメニュー本文を render")
    p_help.add_argument("--plain", action="store_true")
    p_help.add_argument("--all", dest="all_flag", action="store_true",
                       help="全コマンド一覧を表示")
    p_help.add_argument("args", nargs="*", default=[])
    p_help.set_defaults(func="help")

    p_qs = sub.add_parser("print-quickstart", help="`/quickstart` のメニュー本文を render")
    p_qs.add_argument("--plain", action="store_true")
    p_qs.add_argument("args", nargs="*", default=[])
    p_qs.set_defaults(func="quickstart")

    parsed = ap.parse_args()
    if parsed.self_test:
        return _self_test()
    if parsed.command is None:
        ap.print_help()
        return 1

    plain = _is_plain(parsed.plain)
    s = _surface()
    if parsed.func == "help":
        args = list(parsed.args)
        if getattr(parsed, "all_flag", False) and "--all" not in args:
            args.insert(0, "--all")
        print(render_help(s, plain=plain, args=args))
    elif parsed.func == "quickstart":
        print(render_quickstart(s, plain=plain, args=parsed.args))
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

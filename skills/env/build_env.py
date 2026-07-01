#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""環境ダッシュボードの `.agent`（描画エンジン入力）を決定論的に組み立てる。

方針（重要）:
- コマンドを打たずに読める「事実」だけを集める。実効・健全状態は主張しない。
- MCP は「設定上つながっている」表示に留め、緑赤の健全性バッジを付けない
  （実際に応答するかはセッション時に本体が握り、ここからは観測できないため）。
- 秘密（監査 HMAC 鍵など）は一切 HTML に載せない（workspace の config は読まない）。
- どのコマンドが失敗しても落とさず「確認できず」で続行する。

出力: 現在の案件フォルダ（CWD）に `env_dashboard_{YYYY-MM-DD}.agent` を書き、そのパスを stdout に出す。
呼び出し側（SKILL.md）が build_html.py で自己完結 HTML に変換して自動表示する。
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # skills/env
SKILLS = HERE.parent                            # skills
LIB = SKILLS / "_lib"


def _run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:  # noqa: BLE001 — 環境依存の失敗を握りつぶして続行
        return 1, "", str(e)


def _jrun(cmd):
    code, out, _ = _run(cmd)
    if code != 0 or not out.strip():
        return None
    try:
        return json.loads(out)
    except Exception:  # noqa: BLE001
        return None


# --- 契約プランの平易化 ---
def _plan(auth):
    if not auth or not auth.get("loggedIn"):
        return {"label": "確認できず", "consumer": None, "note": "ログイン状態を取得できませんでした。"}
    st = (auth.get("subscriptionType") or "").lower()
    prov = auth.get("apiProvider")
    if st in ("max", "pro"):
        return {"label": f"個人プラン（{st}）", "consumer": True,
                "note": "個人プランは設定によっては学習に使われることがあります。機密案件では事務所の商用アカウントをお使いください。"}
    if st in ("team",):
        return {"label": "事務所プラン（Team）", "consumer": False, "note": "商用プランです。既定では学習に使われません。"}
    if st in ("enterprise",):
        return {"label": "事務所プラン（Enterprise）", "consumer": False, "note": "商用プランです。既定では学習に使われません。"}
    if prov and prov != "firstParty":
        return {"label": f"外部プロバイダ（{prov}）", "consumer": False, "note": "外部ゲートウェイ経由です。"}
    return {"label": st or "不明", "consumer": None, "note": "プランの種別を判定できませんでした。プラン設定をご確認ください。"}


# --- 外部ツール(MCP)の平易名 ---
_MCP_PLAIN = {
    "xlsx-editor": "Excel（.xlsx）の作成・編集",
    "docx-editor": "Word（.docx）の作成・編集",
    "agent-format": "図・レポートの描画（家系図・訴訟分析の HTML）",
}

# --- この端末で使える主な業務（bengo の機能・平易名） ---
_FEATURES = [
    ("相続関係図の作成", "戸籍から相続関係説明図（HTML）を作る"),
    ("文書の誤字チェック", "準備書面など Word 文書の校正（修正履歴つき）"),
    ("訴訟文書の整理", "訴状・答弁書などからタイムライン・主張・認否を整理"),
    ("各種の計算", "交通事故・養育費・財産分与・遺留分・相続分・過払金・残業代"),
    ("書式への入力", "資料 PDF から裁判所書式（Excel）へ自動入力"),
    ("法令の確認", "e-Gov から条文を検索・参照"),
]


def build_agent(cwd: Path) -> dict:
    auth = _jrun(["claude", "auth", "status", "--json"])
    plugins = _jrun(["claude", "plugin", "list", "--json"]) or []
    ws = _jrun(["python3", str(LIB / "workspace.py"), "info"])  # config(秘密)は使わない
    code_v, _, _ = _run(["python3", str(LIB / "audit.py"), "verify"])
    audit_ok = code_v == 0

    plan = _plan(auth)

    # 案件フォルダ（秘密の config は参照しない）
    case_title = "未設定"
    audit_lines = 0
    initialized = False
    if isinstance(ws, dict):
        initialized = bool(ws.get("initialized"))
        case_title = (ws.get("metadata") or {}).get("title") or "未設定"
        audit_lines = (ws.get("audit") or {}).get("lines") or 0

    enabled_plugins = [p for p in plugins if isinstance(p, dict) and p.get("enabled")]

    # 宣言されている MCP（有効プラグインの mcpServers から。健全性は主張しない）
    mcp_rows = []
    seen = set()
    for p in enabled_plugins:
        for name in (p.get("mcpServers") or {}):
            if name in seen:
                continue
            seen.add(name)
            mcp_rows.append({
                "id": name,
                "tool": _MCP_PLAIN.get(name, name),
                "state": "設定上つながっている（実際に応答するかは使うとき確認）",
            })

    # --- 「まず確認」の総合一言 ---
    if plan.get("consumer") is True:
        headline = f"🟡 確認したい点が 1 件あります： {plan['note']}"
    elif not (auth and auth.get("loggedIn")):
        headline = "🟡 ログイン状態を確認できませんでした。事務所のアカウントでログインしているかご確認ください。"
    else:
        headline = "🟢 この画面で分かる範囲では、確認が必要な点は見つかりませんでした。"

    today = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    # --- 守り（bengo が保証できる範囲）report。プレーンテキスト・です・ます調 ---
    plan_mark = "🟡" if plan.get("consumer") is True else ("🟢" if plan.get("consumer") is False else "⬜")
    audit_line = ("🟢 記録：改ざん検知つきで記録しています（整合チェック PASS・{n} 件。中身やファイル名は記録しません）"
                  .format(n=audit_lines)) if audit_ok else \
                 "🟡 記録：改ざん検知の整合チェックに失敗したか、記録が未初期化です。IT・開発元にご相談ください"
    mamori = "\n".join([
        audit_line,
        "🟢 外部送信：作った書類（HTML）は外部に送られない設計です。メールに添付して安全に共有できます",
        f"{plan_mark} 学習・プラン：{plan['label']} … {plan['note']}",
        "",
        "「確認モード（AIが実行前に確認する）」「危険な自動実行の無効」「箱の中での実行（サンドボックス）」",
        "「組織による強制設定」は Claude Code 本体が管理します。設定に書かれた値と実際の適用が一致するかは、",
        "本体の /config・/permissions でご確認ください（この画面では断定しません）。",
    ])

    # --- 限界 report。プレーンテキスト・です・ます調 ---
    limits = "\n".join([
        "【この画面で分かること】今の案件フォルダ／契約プラン・ログイン／入っている拡張と版／",
        "改ざん検知ログの件数と整合／どの外部ツールが“設定上”つながっているか。",
        "",
        "【この画面では分からないこと（本体・プラン設定でご確認ください）】",
        "・外部ツール（Excel／Word など）が“今このとき実際に動くか”",
        "・権限や安全設定が“実際に適用されているか”（本体が合成し、作業中に変わることがあります）",
        "・通信の実際の送信先・出口制御（端末やネットワーク側が担います）",
        "・学習に使われるか（プラン設定でご確認ください）",
        "",
        "確実な現在の値は、本体の /config・/mcp・/permissions でご覧になれます。",
        "",
        f"※ この画面は {today} 時点のスナップショットです。外部とは通信しません。",
        "拡張の構成・案件名・パスが載るため、共有・添付の前に内容をご確認ください。",
    ])

    sections = [
        {
            "id": "sec-metrics", "type": "metrics", "label": "いまの状態", "icon": "📊", "order": 0,
            "data": {"cards": [
                {"id": "m1", "label": "今の案件", "value": case_title, "trend": "neutral"},
                {"id": "m2", "label": "契約プラン", "value": plan["label"], "trend": "neutral"},
                {"id": "m3", "label": "使える拡張", "value": str(len(enabled_plugins)), "trend": "neutral"},
                {"id": "m4", "label": "記録（監査ログ）", "value": f"{audit_lines} 件", "trend": "neutral"},
            ]},
        },
        {
            "id": "sec-headline", "type": "report", "label": "まず確認", "icon": "✅", "order": 1,
            "data": {"template": "{{content}}", "reports": [{
                "id": "r-head", "title": "まず確認", "content": headline,
                "createdAt": now_iso, "updatedAt": now_iso,
            }]},
        },
        {
            "id": "sec-features", "type": "table", "label": "できること（この端末で使える主な機能）", "icon": "🛠", "order": 2,
            "data": {
                "columns": [
                    {"key": "feature", "label": "機能", "type": "text"},
                    {"key": "desc", "label": "説明", "type": "text"},
                ],
                "rows": [{"id": f"f{i}", "feature": f, "desc": d} for i, (f, d) in enumerate(_FEATURES)],
            },
        },
        {
            "id": "sec-mcp", "type": "table", "label": "つながっている外部の道具", "icon": "🔌", "order": 3,
            "data": {
                "columns": [
                    {"key": "tool", "label": "道具・用途", "type": "text"},
                    {"key": "state", "label": "状態", "type": "text"},
                ],
                "rows": [{"id": r["id"], "tool": r["tool"], "state": r["state"]} for r in mcp_rows]
                        or [{"id": "none", "tool": "（設定された外部ツールなし）", "state": "—"}],
            },
        },
        {
            "id": "sec-mamori", "type": "report", "label": "守り", "icon": "🛡", "order": 4,
            "data": {"template": "{{content}}", "reports": [{
                "id": "r-mamori", "title": "守り", "content": mamori,
                "createdAt": now_iso, "updatedAt": now_iso,
            }]},
        },
        {
            "id": "sec-limits", "type": "report", "label": "この画面の見かた", "icon": "ℹ️", "order": 5,
            "data": {"template": "{{content}}", "reports": [{
                "id": "r-limits", "title": "この画面の見かた", "content": limits,
                "createdAt": now_iso, "updatedAt": now_iso,
            }]},
        },
    ]

    return {
        "version": "0.1",
        "name": f"bengo-toolkit 環境の状態（{today}）",
        "icon": "🧭",
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "config": {"proactive": False},
        "sections": sections,
        "memory": {
            "observations": [
                "この画面は生成時点のスナップショットです。実効値は Claude Code 本体が管理します。",
                "緑は「設定・記録が基準内」であって「完全に安全」ではありません。実際の権限適用・通信経路・"
                "外部ツールの稼働はこの画面では確認できません（本体の /config・/mcp・/permissions で確認）。",
            ],
            "preferences": {},
        },
    }


def main() -> int:
    cwd = Path.cwd()
    agent = build_agent(cwd)
    out = cwd / f"env_dashboard_{datetime.date.today().isoformat()}.agent"
    out.write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

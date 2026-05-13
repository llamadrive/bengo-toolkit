#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cowork / Claude Code 実行環境（surface）判定。

本モジュールは **import-only**。Bash 経由の CLI は持たない。
ユーザー向け CLI は `workspace.py surface` / `workspace.py check --require <cap>`
として提供する（既存 allowed-tools の `workspace.py:*` で許可される）。

判定の優先順位:

1. **env var fast path** — `CLAUDE_CODE_IS_COWORK=1` なら "cowork" 即返す。
   Anthropic が Cowork 内部で設定する undocumented signal。documented では
   ないが現実に存在し、内部で eager flush 等の挙動制御に使われている。
2. **capability probe** — env var が無いまたは "1" 以外の場合、ローカル FS
   への書込テストと環境 hint を見て判定する。テストは module-level cache。

probe をかける理由:
  - Anthropic が env var を rename しても、`~/.claude-bengo/` への書込が
    実際に通るかという capability で source-of-truth を持つことで silently
    壊れない。
  - 将来の "Code Web" や "VS Code Web" 等の sandboxed surface でも、env
    var なしで正しく degrade できる。

副作用に注意:
  - probe は `~/.claude-bengo/.runtime-probe.tmp` への 1 度の書込・即削除。
  - 結果は module-level dict に cache。同一プロセス内で複数回呼ばれても
    実 I/O は 1 回のみ。

exit code 規約は `workspace.py check --require` 側で固定する:

  exit 0: capability available
  exit 1: その他のエラー（引数誤り等）
  exit 2: surface により blocked。stdout に日本語の友好的メッセージ。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Literal

Surface = Literal["cowork", "code", "unknown"]

# モジュールレベル cache（プロセス内で一度だけ probe）
_cache: Dict[str, object] = {}


# ---------------------------------------------------------------------------
# 判定
# ---------------------------------------------------------------------------


def surface() -> Surface:
    """現在の実行環境を返す。env var を fast path、capability probe を fallback。"""
    if "surface" in _cache:
        return _cache["surface"]  # type: ignore[return-value]

    env_signal = os.environ.get("CLAUDE_CODE_IS_COWORK")
    if env_signal == "1":
        _cache["surface"] = "cowork"
        return "cowork"

    # env var が無い / "1" 以外 → capability probe
    if _probe_local_fs():
        _cache["surface"] = "code"
        return "code"

    # FS 書込もできない → cowork または相当の sandbox とみなす
    _cache["surface"] = "cowork"
    return "cowork"


def has_local_fs() -> bool:
    """`~/.claude-bengo/` 配下に書き込めて、かつそのデータが永続化される
    実機ファイルシステム上にあるかを返す。

    Cowork surface（VM）では env var が cowork を主張する以上、
    たとえ VM 内 $HOME が書込可能でも、書いた内容は VM 終了で消失し
    audit log としての価値がない。よって surface=cowork なら無条件に
    False を返す。

    Why: 当初 env-var だけで判定していたが、VM 内 $HOME が writable
    な構成だと `_probe_local_fs()` が True を返し、`local_fs` のみで
    gate された command（/audit-config / /case-info 等）が cowork 上で
    動作してしまい、監査ログが ephemeral disk に書かれて失われていた。
    """
    if "local_fs" in _cache:
        return bool(_cache["local_fs"])
    if surface() == "cowork":
        _cache["local_fs"] = False
        return False
    ok = _probe_local_fs()
    _cache["local_fs"] = ok
    return ok


def has_mcp(name: str) -> bool:
    """指定 MCP server が現在の surface で利用可能かを返す。

    現状は surface ベースの conservative 判定:
      - "code" surface ではすべての MCP が利用可能と仮定（true）
      - "cowork" surface では local stdio MCP は利用不可（false）

    Cowork は VM 上で動くため、user の machine 上に立っている stdio MCP
    （docx-editor / xlsx-editor / pptx-editor / agent-format 等）には到達
    できない。逆に Cowork が将来 hosted MCP を提供する場合はここを修正する。
    """
    s = surface()
    local_stdio_mcps = {
        "docx-editor",
        "xlsx-editor",
        "pptx-editor",
        "agent-format",
        "filesystem",
    }
    if name in local_stdio_mcps:
        return s == "code"
    # 不明な MCP は保守的に code surface でのみ true
    return s == "code"


# ---------------------------------------------------------------------------
# capability 要件チェック
# ---------------------------------------------------------------------------


CapabilityName = Literal[
    "local_fs",
    "docx_mcp",
    "xlsx_mcp",
    "pptx_mcp",
    "agent_format_mcp",
]


def require(*caps: CapabilityName) -> "RequireResult":
    """指定 capability がすべて利用可能か判定する。

    workspace.py check --require のロジック本体。CLI 側で exit code を組み立てる。
    """
    missing: list[CapabilityName] = []
    for cap in caps:
        if not _has(cap):
            missing.append(cap)
    return RequireResult(ok=not missing, missing=tuple(missing), surface=surface())


class RequireResult:
    """`require()` の結果。"""

    def __init__(self, ok: bool, missing: tuple, surface: Surface) -> None:
        self.ok = ok
        self.missing = missing
        self.surface = surface


# ---------------------------------------------------------------------------
# 友好的メッセージ
# ---------------------------------------------------------------------------


_CAP_LABEL = {
    "local_fs": "ローカルファイル操作",
    "docx_mcp": "DOCX 編集（docx-editor MCP）",
    "xlsx_mcp": "XLSX 編集（xlsx-editor MCP）",
    "pptx_mcp": "PPTX 編集（pptx-editor MCP）",
    "agent_format_mcp": "agent ファイル描画（agent-format MCP）",
}


def cowork_blocked_message(missing: tuple) -> str:
    """blocked-by-cowork の日本語メッセージ。"""
    if not missing:
        labels = "ローカルファイル/MCP"
    else:
        labels = "・".join(_CAP_LABEL.get(c, c) for c in missing)
    return (
        f"この機能は {labels} を必要とするため、Claude Cowork からは利用できない。\n"
        "\n"
        "Claude Code（CLI または Mac/Windows デスクトップアプリ）で同じプラグインを\n"
        "使えば全機能が動作する。\n"
        "  入手: https://claude.com/code\n"
        "  追加: /plugin marketplace add anthropics/bengo-toolkit\n"
        "\n"
        "Cowork でも動作する機能:\n"
        "  ・計算系（残業代・養育費・遺留分・財産分与・相続・交通事故・婚姻費用）\n"
        "  ・/law-search（条文取得）"
    )


# ---------------------------------------------------------------------------
# 内部 helper
# ---------------------------------------------------------------------------


def _probe_local_fs() -> bool:
    """`~/.claude-bengo/` 配下に書込テスト。

    probe ファイル名に pid を含めることで、並列に走る subprocess 間の
    write/unlink race を避ける。Windows では同一パスへの並行 open/unlink
    が ERROR_SHARING_VIOLATION を投げ、probe が偽 False を返して surface
    判定を cowork に誤らせる事象が観測された（issue #16）。
    """
    try:
        base = Path.home() / ".claude-bengo"
        base.mkdir(mode=0o700, exist_ok=True)
        probe = base / f".runtime-probe-{os.getpid()}.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except (OSError, PermissionError):
        return False


def _has(cap: CapabilityName) -> bool:
    if cap == "local_fs":
        return has_local_fs()
    if cap == "docx_mcp":
        return has_mcp("docx-editor")
    if cap == "xlsx_mcp":
        return has_mcp("xlsx-editor")
    if cap == "pptx_mcp":
        return has_mcp("pptx-editor")
    if cap == "agent_format_mcp":
        return has_mcp("agent-format")
    return False


def _reset_cache_for_testing() -> None:
    """テスト用: cache をクリアする。本番からは呼ばない。"""
    _cache.clear()


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """簡易 self-test。env var 優先順位の確認のみ。"""
    import sys

    failures = []

    # Test 1: env var = "1" → cowork
    _reset_cache_for_testing()
    os.environ["CLAUDE_CODE_IS_COWORK"] = "1"
    if surface() != "cowork":
        failures.append("Test 1: env=1 should yield cowork")

    # Test 2: env var = "0" → falls through to probe（FS あれば code）
    _reset_cache_for_testing()
    os.environ["CLAUDE_CODE_IS_COWORK"] = "0"
    s = surface()
    if s not in ("code", "cowork"):
        failures.append(f"Test 2: env=0 should yield code or cowork, got {s}")

    # Test 3: env var 未設定 → probe
    _reset_cache_for_testing()
    os.environ.pop("CLAUDE_CODE_IS_COWORK", None)
    s = surface()
    if s not in ("code", "cowork"):
        failures.append(f"Test 3: no env should yield code or cowork, got {s}")

    # Test 4: require() unknown cap → not ok
    _reset_cache_for_testing()
    os.environ["CLAUDE_CODE_IS_COWORK"] = "1"
    r = require("docx_mcp")
    if r.ok:
        failures.append("Test 4: docx_mcp should be missing in cowork")
    if "docx_mcp" not in r.missing:
        failures.append("Test 4: missing should contain docx_mcp")

    # Test 5: cowork_blocked_message non-empty
    msg = cowork_blocked_message(("docx_mcp",))
    if "DOCX" not in msg or "claude.com/code" not in msg:
        failures.append("Test 5: message missing key parts")

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("runtime.py self-test: all passed")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("self-test", "--self-test"):
        sys.exit(_self_test())
    print(
        "runtime.py is import-only. CLI lives in workspace.py "
        "(surface / check --require). For tests: --self-test.",
        file=sys.stderr,
    )
    sys.exit(1)

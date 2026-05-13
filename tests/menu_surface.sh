#!/usr/bin/env bash
# menu.py の surface-aware 出力を決定論的に検証する。
#
# Cowork mode で `/help` と `/quickstart` の menu 本文に blocked skill 名が
# 出ないことを `! grep -E` で assert する。

set -e
set -o pipefail

cd "$(dirname "$0")/.."
PASS=0
FAIL=0

ok() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
ng() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "=== menu_surface.sh ==="

# menu.py self-test
if python3 skills/_lib/menu.py --self-test >/dev/null 2>&1; then
  ok "menu.py self-test"
else
  ng "menu.py self-test"
fi

# /help in cowork must NOT include any blocked skill name in the basic menu.
BLOCKED_REGEX='typo-check|template-(install|fill|create|promote|demote|list|firm-setup)|family-tree|lawsuit-analysis|audit-config|case-info|verify'

out=$(CLAUDE_CODE_IS_COWORK=1 NO_COLOR=1 python3 skills/_lib/menu.py print-help --plain)
if ! echo "$out" | grep -E "$BLOCKED_REGEX" >/dev/null; then
  ok "print-help (cowork) has no blocked skill names"
else
  ng "print-help (cowork) leaks blocked skill name: $(echo "$out" | grep -E "$BLOCKED_REGEX" | head -1)"
fi

# /help --all in cowork: blocked names appear with 'Claude Code 限定' annotation.
out_all=$(CLAUDE_CODE_IS_COWORK=1 NO_COLOR=1 python3 skills/_lib/menu.py print-help --plain -- --all)
if echo "$out_all" | grep -q "Claude Code 限定"; then
  ok "print-help --all (cowork) annotates blocked skills"
else
  ng "print-help --all (cowork) missing 'Claude Code 限定' annotation"
fi

# /quickstart in cowork: must NOT include forbidden demo items.
# Patterns must match the current QUICKSTART_OPTIONS titles for the 4 blocked demos:
#   family-tree       → 「戸籍から相続関係説明図を描く」
#   template-fill     → 「PDF から XLSX 書式へ自動入力」
#   typo-check        → 「準備書面の校正」
#   lawsuit-analysis  → 「訴状と答弁書から事件分析レポート」
out_qs=$(CLAUDE_CODE_IS_COWORK=1 NO_COLOR=1 python3 skills/_lib/menu.py print-quickstart --plain)
if ! echo "$out_qs" | grep -E '戸籍から相続関係|XLSX 書式へ自動入力|準備書面の校正|事件分析レポート' >/dev/null; then
  ok "print-quickstart (cowork) has no blocked demo items"
else
  ng "print-quickstart (cowork) leaks blocked demo item"
fi

# Code mode: /help must include 書類 / 戸籍 categories.
unset CLAUDE_CODE_IS_COWORK
out_code=$(NO_COLOR=1 python3 skills/_lib/menu.py print-help --plain)
if echo "$out_code" | grep -q "書類を作成する"; then
  ok "print-help (code) shows full menu"
else
  ng "print-help (code) missing 書類を作成する"
fi

echo
echo "=== menu_surface.sh: ${PASS} passed / ${FAIL} failed ==="
exit $((FAIL == 0 ? 0 : 1))

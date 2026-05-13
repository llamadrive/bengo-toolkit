#!/usr/bin/env bash
# Cowork gating の自動テスト。
#
# 検証内容:
#   1. runtime.py self-test
#   2. CLAUDE_CODE_IS_COWORK=1 下で workspace.py check が exit 2 + 日本語 stdout
#   3. CLAUDE_CODE_IS_COWORK=1 下で audit.py record が exit 0 + cowork notice
#   4. CLAUDE_CODE_IS_COWORK=1 下で first_run.py notice が exit 0 + cowork notice
#   5. CLAUDE_CODE_IS_COWORK=1 下で search.py fetch-article が WebFetch JSON を stderr 最終行に出す
#   6. CLAUDE_CODE_IS_COWORK=1 下で search.py search-keyword が degrade JSON を出す
#   7. workspace.py --help に surface / check が含まれる

# set -e は使わない（test 内で exit !=0 を意図的に検査するため）
set -o pipefail

cd "$(dirname "$0")/.."
PASS=0
FAIL=0

ok() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
ng() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "=== cowork_gating.sh ==="

# 1. runtime.py self-test
if python3 skills/_lib/runtime.py --self-test >/dev/null 2>&1; then
  ok "runtime.py self-test"
else
  ng "runtime.py self-test"
fi

# 2. workspace.py check exit 2 + Japanese stdout
out=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/_lib/workspace.py check --require docx_mcp 2>/dev/null)
ec=$?
if [ $ec -eq 2 ]; then ok "workspace.py check exit code 2"; else ng "workspace.py check exit code (got $ec)"; fi
if echo "$out" | grep -q "Claude Cowork"; then ok "workspace.py check Japanese stdout"; else ng "workspace.py check stdout missing Japanese message"; fi
if echo "$out" | grep -q "claude.com/code"; then ok "workspace.py check install link"; else ng "workspace.py check missing install link"; fi

# 3. audit.py record skipped in cowork
err=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/_lib/audit.py record --skill child-support-calc --event calc_result 2>&1 >/dev/null)
ec=$?
if [ $ec -eq 0 ]; then ok "audit.py record exit 0 in cowork"; else ng "audit.py record exit (got $ec)"; fi
if echo "$err" | grep -q "skipped (cowork)"; then ok "audit.py record cowork notice"; else ng "audit.py record missing notice"; fi

# 4. first_run.py notice no-op in cowork
err=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/_lib/first_run.py notice 2>&1 >/dev/null)
ec=$?
if [ $ec -eq 0 ]; then ok "first_run.py notice exit 0"; else ng "first_run.py notice exit (got $ec)"; fi
if echo "$err" | grep -q "skipped (cowork)"; then ok "first_run.py cowork notice"; else ng "first_run.py missing notice"; fi

# 5. search.py fetch-article webfetch JSON on stderr last line
err=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/law-search/search.py fetch-article \
  --law-id 129AC0000000089 --article 709 2>&1 >/dev/null)
ec=$?
last=$(echo "$err" | tail -n 1)
if [ $ec -eq 0 ]; then ok "search.py fetch-article exit 0 in cowork"; else ng "search.py fetch-article exit (got $ec)"; fi
if echo "$last" | python3 -c 'import sys, json; j=json.loads(sys.stdin.read()); sys.exit(0 if j.get("use_webfetch") else 1)'; then
  ok "search.py fetch-article emits valid use_webfetch JSON"
else
  ng "search.py fetch-article stderr last line not valid use_webfetch JSON"
fi

# 6. search.py search-keyword degrade JSON
err=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/law-search/search.py search-keyword \
  --law-id 129AC0000000089 --keyword 監護 2>&1 >/dev/null)
ec=$?
last=$(echo "$err" | tail -n 1)
if [ $ec -eq 0 ]; then ok "search.py search-keyword exit 0 in cowork"; else ng "search.py search-keyword exit (got $ec)"; fi
if echo "$last" | python3 -c 'import sys, json; j=json.loads(sys.stdin.read()); sys.exit(0 if j.get("degraded") else 1)'; then
  ok "search.py search-keyword emits degrade JSON"
else
  ng "search.py search-keyword stderr last line not valid degrade JSON"
fi

# 7. workspace.py --help has surface and check
help=$(python3 skills/_lib/workspace.py --help 2>&1)
if echo "$help" | grep -q "surface"; then ok "workspace.py --help includes 'surface'"; else ng "workspace.py --help missing 'surface'"; fi
if echo "$help" | grep -q "check"; then ok "workspace.py --help includes 'check'"; else ng "workspace.py --help missing 'check'"; fi

# 8. exit code 0 in code surface
unset CLAUDE_CODE_IS_COWORK
out=$(python3 skills/_lib/workspace.py check --require local_fs 2>&1)
ec=$?
if [ $ec -eq 0 ]; then ok "workspace.py check exit 0 in code"; else ng "workspace.py check exit in code (got $ec)"; fi

# 9. local_fs gate blocks in cowork even if VM $HOME is writable
#    （regression: 旧 has_local_fs() は surface を見ず probe のみで判定して
#     いたため、書込可能な VM 上では local_fs gate が素通りし、監査ログが
#     ephemeral disk に書かれて消失していた。）
out=$(CLAUDE_CODE_IS_COWORK=1 python3 skills/_lib/workspace.py check --require local_fs 2>/dev/null)
ec=$?
if [ $ec -eq 2 ]; then ok "workspace.py check --require local_fs blocks in cowork"; else ng "workspace.py check --require local_fs in cowork (got $ec, expected 2)"; fi
if echo "$out" | grep -q "Claude Cowork"; then ok "local_fs block has Japanese stdout"; else ng "local_fs block missing Japanese message"; fi

# 10. menu.py print-help --all renders the full command list
#     （regression: argparse が --all を unrecognized argument として拒否していた。）
out=$(python3 skills/_lib/menu.py print-help --all --plain 2>&1)
ec=$?
if [ $ec -eq 0 ]; then ok "menu.py print-help --all exit 0"; else ng "menu.py print-help --all exit (got $ec)"; fi
if echo "$out" | grep -q "全コマンド一覧"; then ok "menu.py print-help --all renders header"; else ng "menu.py print-help --all missing header"; fi

# 11. .mcp.json declares the three bundled servers
#     （regression: 一度 mcpServers が空のままコミット候補に上がっていた。）
if python3 -c "import json; d=json.load(open('.mcp.json')); s=d.get('mcpServers',{}); assert 'xlsx-editor' in s and 'docx-editor' in s and 'agent-format' in s" 2>/dev/null; then
  ok ".mcp.json declares xlsx-editor / docx-editor / agent-format"
else
  ng ".mcp.json missing one or more bundled MCP server definitions"
fi

echo
echo "=== cowork_gating.sh: ${PASS} passed / ${FAIL} failed ==="
exit $((FAIL == 0 ? 0 : 1))

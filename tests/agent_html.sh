#!/usr/bin/env bash
# 自己完結 HTML 生成（skills/_lib/agent_html）の自動テスト。
#
# 検証内容:
#   1. コミット済み描画エンジン部品（dist/）が存在する
#   2. host サブコマンド: $CLAUDECODE=1 → cli / 未設定 → inline
#   3. build が .html を生成し、データ・描画エンジン・厳格 CSP を inline する
#   4. 生成 HTML が外部リソースを参照しない（完全自己完結）
#   5. --prune-agent: どのホストでも入力 .agent を削除し成果物を .html に一本化

set -o pipefail
cd "$(dirname "$0")/.."
PASS=0
FAIL=0
ok() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
ng() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

echo "=== agent_html.sh ==="

LIB="skills/_lib/agent_html"
BH="$LIB/build_html.py"

# 1. committed dist artifacts
if [ -f "$LIB/dist/renderer_bundle.js" ] && [ -f "$LIB/dist/renderer_styles.css" ]; then
  ok "dist/renderer_bundle.js + renderer_styles.css are committed"
else
  ng "missing dist/ artifacts — run: cd $LIB && npm install && npm run build"
fi

# 2. host detection
h_cli=$(CLAUDECODE=1 python3 "$BH" host 2>/dev/null)
[ "$h_cli" = "cli" ] && ok "host=cli under \$CLAUDECODE=1" || ng "host under \$CLAUDECODE=1 (got '$h_cli')"
h_inline=$(env -u CLAUDECODE python3 "$BH" host 2>/dev/null)
[ "$h_inline" = "inline" ] && ok "host=inline without \$CLAUDECODE" || ng "host without \$CLAUDECODE (got '$h_inline')"

# sample .agent
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/sample.agent" <<'JSON'
{
  "version": "0.1",
  "name": "テスト 相続関係説明図",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "config": { "proactive": false },
  "sections": [
    { "id": "s1", "type": "family-graph", "label": "図", "order": 0,
      "data": { "variant": "jp-court", "focusedPersonId": "p1",
        "persons": [
          {"id":"p1","name":"鈴木一郎","role":"被相続人","deathDate":"令和6年1月1日"},
          {"id":"p2","name":"鈴木花子","role":"妻"}
        ],
        "relationships": [ {"type":"spouse","person1Id":"p1","person2Id":"p2"} ] } }
  ],
  "memory": { "observations": ["⚠ AI ドラフト"], "preferences": {} }
}
JSON

# 3. build produces self-contained html (inline host → keeps .agent, no browser)
out=$(env -u CLAUDECODE python3 "$BH" build --input "$TMP/sample.agent" 2>/dev/null)
if [ -f "$TMP/sample.html" ]; then
  ok "build produced sample.html"
else
  ng "build did not produce sample.html (stdout: $out)"
fi

H="$TMP/sample.html"
grep -q "connect-src 'none'" "$H" && ok "html embeds strict CSP (connect-src 'none')" || ng "html missing CSP"
grep -q "鈴木一郎" "$H" && ok "html inlines the agent data" || ng "html missing agent data"
grep -q "__bengoMountAgent" "$H" && ok "html inlines the render bundle" || ng "html missing render bundle"

# 4. fully self-contained: no external script/style/link resource loads
if grep -qE '(src|href)="https?:' "$H"; then
  ng "html references an external resource (not self-contained)"
else
  ok "html loads no external resources"
fi

# 4b. single-pass substitution: untrusted data containing placeholder tokens
#     (戸籍 PDF 由来で %%BUNDLE%% 等が混入) must NOT corrupt later substitutions.
cat > "$TMP/inject.agent" <<'JSON'
{ "version": "0.1", "name": "%%BUNDLE%% %%AGENT_JSON%% 注入テスト",
  "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
  "config": { "proactive": false }, "sections": [],
  "memory": { "observations": [], "preferences": {} } }
JSON
env -u CLAUDECODE python3 "$BH" build --input "$TMP/inject.agent" --output "$TMP/inject.html" >/dev/null 2>&1
if grep -q "%%BUNDLE%%" "$TMP/inject.html" && grep -q "__bengoMountAgent" "$TMP/inject.html"; then
  ok "placeholder tokens in data are preserved (single-pass; bundle intact)"
else
  ng "placeholder tokens in data corrupted the output (chained-replace regression)"
fi

# 4c. output path may not equal the input .agent (data-loss guard)
cp "$TMP/sample.agent" "$TMP/guard.agent"
env -u CLAUDECODE python3 "$BH" build --input "$TMP/guard.agent" --output "$TMP/guard.agent" >/dev/null 2>&1
gec=$?
if [ $gec -ne 0 ] && [ -s "$TMP/guard.agent" ]; then
  ok "build rejects --output equal to input (.agent preserved)"
else
  ng "build should reject --output == input (exit=$gec)"
fi

# 5a. --prune-agent removes the input .agent under cli (html kept)
cp "$TMP/sample.agent" "$TMP/cli.agent"
CLAUDECODE=1 python3 "$BH" build --input "$TMP/cli.agent" --prune-agent >/dev/null 2>&1
if [ -f "$TMP/cli.html" ] && [ ! -f "$TMP/cli.agent" ]; then
  ok "--prune-agent removes .agent under cli (html kept)"
else
  ng "--prune-agent behavior under cli (html=$([ -f "$TMP/cli.html" ] && echo y || echo n) agent=$([ -f "$TMP/cli.agent" ] && echo y || echo n))"
fi

# 5b. --prune-agent removes the input .agent on inline host too (always internal)
cp "$TMP/sample.agent" "$TMP/inl.agent"
env -u CLAUDECODE python3 "$BH" build --input "$TMP/inl.agent" --prune-agent >/dev/null 2>&1
if [ -f "$TMP/inl.html" ] && [ ! -f "$TMP/inl.agent" ]; then
  ok "--prune-agent removes .agent on inline host too (html kept)"
else
  ng "--prune-agent should remove .agent on inline host (html=$([ -f "$TMP/inl.html" ] && echo y || echo n) agent=$([ -f "$TMP/inl.agent" ] && echo y || echo n))"
fi

# 5c. without --prune-agent the input is kept (opt-in viewer path)
cp "$TMP/sample.agent" "$TMP/keep.agent"
CLAUDECODE=1 python3 "$BH" build --input "$TMP/keep.agent" >/dev/null 2>&1
if [ -f "$TMP/keep.html" ] && [ -f "$TMP/keep.agent" ]; then
  ok "build without --prune-agent keeps the .agent"
else
  ng "build without --prune-agent should keep the .agent"
fi

echo ""
echo "=== agent_html.sh: $PASS passed, $FAIL failed ==="
[ $FAIL -eq 0 ]

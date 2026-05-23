#!/usr/bin/env bash
# stock-analysis HTML 自检脚本（Linear Terminal+ 规范）
# 用法：bash verify_html.sh <html-file>
set -u

if [ $# -lt 1 ]; then
  echo "用法：bash verify_html.sh <html-file>" >&2
  exit 2
fi

FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "[X] 文件不存在：$FILE" >&2
  exit 2
fi

pass=0
fail=0

check() {
  local desc="$1"; local cond="$2"
  if eval "$cond"; then
    echo "[PASS] $desc"
    pass=$((pass+1))
  else
    echo "[FAIL] $desc"
    fail=$((fail+1))
  fi
}

# 1. lavender 主题
check "accent lavender token" "[ \$(grep -c -- '\--accent: *#5e6ad2' '$FILE') -ge 1 ]"

# 2. nav 13 或 14 个锚点（=14 iff #bear-case 存在）
check "nav 13-14 anchors" "[ \$(grep -o 'href=\"#' '$FILE' | wc -l) -ge 13 ] && [ \$(grep -o 'href=\"#' '$FILE' | wc -l) -le 14 ]"

# 2.5 mermaid 块 + CDN
check "mermaid block exists" "[ \$(grep -c 'class=\"mermaid\"' '$FILE') -ge 1 ]"
check "mermaid.initialize present" "[ \$(grep -c 'mermaid.initialize' '$FILE') -ge 1 ]"
check "mermaid CDN v10" "[ \$(grep -c 'mermaid@10' '$FILE') -ge 1 ]"
check "echarts CDN v5" "[ \$(grep -c 'echarts@5\|echarts.min.js' '$FILE') -ge 1 ]"
check "mathjax CDN v3" "[ \$(grep -c 'mathjax@3' '$FILE') -ge 1 ]"

# 3. compliance banner 存在
check "compliance banner" "[ \$(grep -c 'compliance-banner' '$FILE') -ge 1 ]"

# 4. 4 个 hero-meta-item
check "hero meta items (4)" "[ \$(grep -o 'hero-meta-item' '$FILE' | wc -l) -ge 4 ]"

# 5. 9 个 step id 全部存在
for id in mission macro chain quality elasticity risk valuation compare tracking; do
  check "step id #$id" "[ \$(grep -c 'id=\"$id\"' '$FILE') -ge 1 ]"
done

# 6. // CONCLUSION 总结框
check "// CONCLUSION block" "[ \$(grep -c '// CONCLUSION' '$FILE') -ge 1 ]"

# 7. 占位符清零
check "no __RAW_DATA placeholder" "[ \$(grep -c '__RAW_DATA' '$FILE') -eq 0 ]"
check "no __PIE_DATA placeholder" "[ \$(grep -c '__PIE_DATA' '$FILE') -eq 0 ]"

# 8. 无 gold 残留
check "no gold color" "! grep -qE '#FFD700|#fbbf24|color: ?gold' '$FILE'"

# 9. footer 段内禁止 strong
check "footer plain (no <strong>)" "[ \$(awk '/ANCHOR:footer|<footer>/,/<\/footer>/' '$FILE' | grep -c '<strong>') -eq 0 ]"

# 10. script 区块包含 rawData / pieData 声明
check "rawData declaration" "[ \$(grep -c 'const rawData' '$FILE') -ge 1 ]"
check "pieData declaration" "[ \$(grep -c 'const pieData' '$FILE') -ge 1 ]"

echo ""
echo "$pass PASS / $fail FAIL"
if [ $fail -gt 0 ]; then
  exit 1
fi

# === v3.1 内容层校验 ===
HTML_PATH="$1"
DIR="$(dirname "$HTML_PATH")"
DATA="$DIR/data.json"
REPORT="$DIR/report.md"

if [ -f "$DATA" ] && [ -f "$REPORT" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  python "$SCRIPT_DIR/verify_content.py" \
    --html "$HTML_PATH" --report "$REPORT" --data "$DATA"
  CONTENT_RC=$?
  if [ $CONTENT_RC -ne 0 ]; then
    echo "[FAIL] verify_content.py 失败 (rc=$CONTENT_RC)"
    exit 1
  fi

  # v3.2: 跨节一致性校验
  python "$SCRIPT_DIR/verify_consistency.py" \
    --report "$REPORT" --data "$DATA"
  CONS_RC=$?
  if [ $CONS_RC -ne 0 ]; then
    echo "[FAIL] verify_consistency.py 失败 (rc=$CONS_RC)"
    exit 1
  fi
else
  echo "[WARN] 未找到 data.json 或 report.md，跳过 verify_content / verify_consistency"
fi
exit 0

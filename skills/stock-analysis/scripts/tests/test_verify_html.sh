#!/usr/bin/env bash
# 测试 verify_html.sh 在 pass/fail fixture 上的行为
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../verify_html.sh"
PASS_FIXTURE="$HERE/fixtures/pass.html"
FAIL_FIXTURE="$HERE/fixtures/fail.html"

passed=0
failed=0

assert() {
  local desc="$1"; local expect="$2"; local actual="$3"
  if [ "$expect" = "$actual" ]; then
    echo "  ✓ $desc"
    passed=$((passed+1))
  else
    echo "  ✗ $desc (expect=$expect actual=$actual)"
    failed=$((failed+1))
  fi
}

echo "Test 1: pass.html should exit 0"
rc=0
bash "$SCRIPT" "$PASS_FIXTURE" >/dev/null 2>&1 || rc=$?
assert "exit code on PASS fixture" 0 $rc

echo "Test 2: fail.html should exit nonzero"
rc=0
bash "$SCRIPT" "$FAIL_FIXTURE" >/dev/null 2>&1 || rc=$?
assert "exit code on FAIL fixture" 1 $rc

echo "Test 3: pass.html output contains 'PASS'"
rc=0
bash "$SCRIPT" "$PASS_FIXTURE" 2>&1 | grep -q '\[PASS\]' || rc=$?
assert "output PASS marker" 0 $rc

echo "Test 4: fail.html output contains 'FAIL'"
rc=0
bash "$SCRIPT" "$FAIL_FIXTURE" 2>&1 | grep -q '\[FAIL\]' || rc=$?
assert "output FAIL marker" 0 $rc

echo ""
echo "$passed passed, $failed failed"
exit $failed

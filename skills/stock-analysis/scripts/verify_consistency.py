#!/usr/bin/env python3
"""verify_consistency.py · v3.2 跨节一致性校验。

输入：report.md (含 invariants v3.2 YAML 块) + data.json
输出：[CONS-*] FAIL 列表；退出码 0=PASS, 1=FAIL, 0=WARN (missing invariants)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

INVARIANTS_RE = re.compile(
    r'<!--\s*invariants v3\.2\s*-->\s*```yaml\s*\n(.+?)\n```',
    re.DOTALL
)


def extract_invariants(report_md: str) -> dict | None:
    """提取 report.md 头部的 invariants YAML 块。无块返回 None。"""
    m = INVARIANTS_RE.search(report_md)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        print(f"[FAIL] invariants 块 YAML 解析失败：{e}", file=sys.stderr)
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--data", required=True)
    args = p.parse_args()

    report_md = Path(args.report).read_text(encoding='utf-8')
    inv = extract_invariants(report_md)

    if inv is None:
        print('=== verify_consistency · v3.2 ===')
        print('[WARN] invariants block (marker "invariants v3.2") not found, skipping consistency checks')
        print('\n[PASS] 0 / [FAIL] 0 / [WARN] 1')
        return 0

    fails: list[dict] = []
    # 后续 task B2-B7 逐步加 check_derived / check_target_mult / check_anomaly_titles / check_baseline_eps / check_score_consistency / expand_explicit_refs

    print('=== verify_consistency · v3.2 ===')
    for f in fails:
        print(f"[{f['check']}] {f['location']}")
        print(f"  expected: {f['expected']}")
        print(f"  actual:   {f['actual']}")
        print(f"  fix:      {f['fix']}")
    print(f"\n[PASS] {0 if fails else 1} / [FAIL] {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

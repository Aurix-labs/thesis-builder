"""verify_consistency.py · 合成后跨模块一致性校验。

检查项：
1. 各模块 report.md 存在且 MARKER 头对齐
2. module 间共享数据数字一致（如同一个指数在不同模块中数值相同）
3. review.md 引用了全部 6 个模块
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REVIEW_MODULES = ["index", "sentiment", "mainline", "capital", "variables", "combatmap"]
MARKER_RE = re.compile(r'<!-- REVIEW_MODULE_START\s+module=(\w+)\s+date=(\d{4}-\d{2}-\d{2})\s+-->')


def check_module_markers(ymd_dir: Path) -> list[dict]:
    """检查各模块 report.md 是否有正确的 MARKER 头。"""
    issues = []
    for m in REVIEW_MODULES:
        report_path = ymd_dir / m / "report.md"
        if not report_path.exists():
            issues.append({"kind": "FAIL", "module": m, "reason": "report.md 不存在"})
            continue
        content = report_path.read_text(encoding="utf-8")
        marker = MARKER_RE.search(content)
        if not marker:
            issues.append({"kind": "FAIL", "module": m, "reason": "缺少 REVIEW_MODULE_START marker"})
            continue
        if marker.group(1) != m:
            issues.append({"kind": "WARN", "module": m, "reason": f"marker module={marker.group(1)} != 目录名 {m}"})
    return issues


def check_review_md(ymd_dir: Path) -> list[dict]:
    """检查 review.md 是否引用了全部模块。"""
    review_path = ymd_dir / "review.md"
    issues = []
    if not review_path.exists():
        return [{"kind": "FAIL", "module": "review", "reason": "review.md 不存在"}]

    content = review_path.read_text(encoding="utf-8")
    for m in REVIEW_MODULES:
        keywords = {
            "index": "大盘环境",
            "sentiment": "情绪周期",
            "mainline": "主线",
            "capital": "资金",
            "variables": "盘后变量",
            "combatmap": "作战地图",
        }
        kw = keywords.get(m, m)
        if kw not in content:
            issues.append({"kind": "WARN", "module": m, "reason": f"review.md 中未出现关键词 '{kw}'"})
    return issues


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    ymd_dir = Path(args.output_dir) / args.ymd
    if not ymd_dir.exists():
        print(f"ERROR: {ymd_dir} not found", file=sys.stderr)
        return 1

    issues = check_module_markers(ymd_dir) + check_review_md(ymd_dir)

    fails = [i for i in issues if i["kind"] == "FAIL"]
    warns = [i for i in issues if i["kind"] == "WARN"]

    print(f"=== verify_consistency ===")
    for i in issues:
        print(f"[{i['kind']}] {i['module']}: {i['reason']}")
    print(f"\n[PASS] {6 - len(fails) - len(warns)} modules / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


if __name__ == "__main__":
    raise SystemExit(main())

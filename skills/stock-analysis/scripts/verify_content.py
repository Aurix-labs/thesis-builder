"""verify_content.py · Phase 3 末跨产物一致性校验。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAW_DATA_RE = re.compile(r'const\s+rawData\s*=\s*(\[.*?\])\s*;', re.DOTALL)
PIE_DATA_RE = re.compile(r'const\s+pieData\s*=\s*(\[.*?\])\s*;', re.DOTALL)


def extract_hero_value(html: str, label: str) -> str | None:
    pattern = re.compile(
        r'<div\s+class="k">' + re.escape(label) + r'</div>\s*<div\s+class="v[^"]*">([^<]+)</div>',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    return m.group(1).strip() if m else None


def parse_price_str(s: str) -> float | None:
    m = re.search(r'-?\d+\.?\d*', s.replace('¥', '').replace(',', ''))
    return float(m.group(0)) if m else None


def check_latest_price(html: str, data: dict, fails: list):
    kline = data.get("kline_daily", [])
    if not kline:
        return
    expected = kline[-1][2]
    val_str = extract_hero_value(html, "Latest") or extract_hero_value(html, "最新价")
    if val_str is None:
        fails.append({"check": "hero Latest 字段未找到"})
        return
    actual = parse_price_str(val_str)
    if actual is None or abs(actual - expected) > 0.01:
        fails.append({"check": "hero Latest",
                      "expected": expected, "actual": actual,
                      "fix": "修改 HTML hero meta Latest 或 data.json kline_daily 末行"})


def check_pie_data(html: str, data: dict, fails: list):
    m = PIE_DATA_RE.search(html)
    if not m:
        return
    try:
        pie = json.loads(m.group(1))
    except json.JSONDecodeError:
        fails.append({"check": "pieData JSON 格式错误"})
        return

    business = data.get("blocks", {}).get("business", [])
    if not business:
        return

    latest = max((r["报告日期"] for r in business if "报告日期" in r), default=None)
    rows = [r for r in business
            if r.get("报告日期") == latest and r.get("分类类型") == "按产品分类"]
    if not rows:
        return

    expected_names = sorted([r["主营构成"] for r in rows])
    actual_names = sorted([p["name"] for p in pie])
    intersect = set(expected_names) & set(actual_names)
    if not intersect:
        fails.append({"check": "pieData 与 blocks.business 名称完全不匹配",
                      "expected": expected_names[:3], "actual": actual_names[:3],
                      "fix": "Phase 3 写 HTML 时把 pieData 改为 blocks.business 最新报告期按产品分类"})


def check_kline_count(html: str, data: dict, fails: list):
    m = RAW_DATA_RE.search(html)
    if not m:
        return
    try:
        raw = json.loads(m.group(1))
    except json.JSONDecodeError:
        fails.append({"check": "rawData JSON 格式错误"})
        return
    title_3y = re.search(r'近\s*3\s*年', html)
    if title_3y and len(raw) < 720:
        fails.append({
            "check": "标题声明'近 3 年' 但 rawData 仅 " + str(len(raw)) + " 行",
            "fix": "把 data.json.kline_daily 全部 ≥720 行注入，或修改标题为对应实际范围"
        })


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--html", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--data", required=True)
    args = p.parse_args()

    html = Path(args.html).read_text()
    data = json.loads(Path(args.data).read_text())

    fails: list[dict] = []
    check_latest_price(html, data, fails)
    check_pie_data(html, data, fails)
    check_kline_count(html, data, fails)

    print(f"=== verify_content · {Path(args.html).name} ===")
    for f in fails:
        print(f"[FAIL] {f.get('check')}")
        if 'expected' in f:
            print(f"    expected: {f['expected']}, actual: {f.get('actual')}")
        if 'fix' in f:
            print(f"    fix: {f['fix']}")
    print(f"\n[FAIL] {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""record_eval.py · 从 review.md 提取关键判断写入 eval.json。

正则提取情绪周期、主线方向、仓位建议、场景数、风险提示。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SENTIMENT_PAT = re.compile(r'(情绪周期|周期阶段)[：:]\s*(.+?)(?:[。，\n]|$)')
MAINLINE_PAT = re.compile(r'(主线|主线方向)[：:]\s*(.+?)(?:[。，\n]|$)')
POSITION_PAT = re.compile(r'(仓位建议|仓位)[：:]\s*(.+?)(?:[。，\n]|$)')
SCENARIO_PAT = re.compile(r'(强势路径|中性路径|弱势路径)')
RISK_PAT = re.compile(r'(风险提示|警惕|陷阱)[：:]\s*(.+?)(?:[。]|\n\n|$)')


def extract_sentiment_stage(md: str) -> str | None:
    m = SENTIMENT_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_mainline(md: str) -> str | None:
    m = MAINLINE_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_position(md: str) -> str | None:
    m = POSITION_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_scenarios(md: str) -> list[str]:
    return list(set(SCENARIO_PAT.findall(md)))


def extract_risks(md: str) -> list[str]:
    risks = []
    risk_section = re.search(r'风险提示[：:]\s*\n((?:\s*[-•]\s*.+\n?)+)', md)
    if risk_section:
        for line in risk_section.group(1).splitlines():
            cleaned = re.sub(r'^\s*[-•]\s*', '', line).strip()
            if cleaned:
                risks.append(cleaned)
    return risks[:5]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    review_path = Path(args.output_dir) / args.ymd / "review.md"
    if not review_path.exists():
        print(f"ERROR: {review_path} not found", file=sys.stderr)
        return 1

    md = review_path.read_text(encoding="utf-8")

    eval_data = {
        "date": args.ymd,
        "market_review": {
            "sentiment_stage": extract_sentiment_stage(md),
            "mainline_direction": extract_mainline(md),
            "position_advice": extract_position(md),
            "scenarios": extract_scenarios(md),
            "risk_warnings": extract_risks(md),
        },
    }

    eval_path = Path(args.output_dir) / args.ymd / "eval.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"eval.json written to {eval_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

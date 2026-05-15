"""build_inventory.py · Phase 1 末自动产出 data_inventory.md。

读 data.json（必含 meta + blocks），输出：
- 各 block 的行数 / 最新日期 / 健康度（✅/⚠️/❌）
- Step 0-8 字段需求映射
- 推荐补全清单
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# 各 Step 必需字段（与 analysis-framework.md 一致）
STEP_FIELDS = {
    "Step 0.5 异常分析": ["financial_abstract", "fund_flow"],
    "Step 1 宏观": ["news"],
    "Step 2 产业链": ["business", "news"],
    "Step 3 公司质地": ["financials", "top_holders"],
    "Step 4 弹性": ["financials", "business"],
    "Step 5 风险": ["financials", "notice"],
    "Step 6a+ 资金面": ["fund_flow", "margin"],
    "Step 6c 研报验证": ["research", "recommend"],
    "Step 7 对标": ["financials"],
    "Step 8 跟踪": ["financial_abstract"],
}

# 匹配 8 位紧凑日期如 20260331
_DATE8_RE = re.compile(r'^\d{8}$')


def health_of(rows: int, latest: str | None) -> str:
    if rows == 0:
        return "❌ 缺失，需 web 补"
    if rows < 10 and latest is None:
        return "⚠️ 数据极少"
    return "✅"


def latest_date_of(block: list) -> str | None:
    """尝试从 block 行中提取最大日期（多种字段名兼容）。

    兼容两种模式：
    1. 行字典中含日期字段（如 "日期"、"报告日期"）
    2. 行字典的 key 本身是 8 位日期（如 "20260331"，常见于财务摘要宽表）
    """
    if not block or not isinstance(block, list):
        return None
    date_keys = ["日期", "报告日期", "发布日期", "公告日期", "as_of"]
    dates = []
    for row in block:
        if isinstance(row, dict):
            # 模式 1：行内有已知日期字段
            for k in date_keys:
                if k in row and row[k]:
                    dates.append(str(row[k]))
                    break
            # 模式 2：key 本身是 8 位日期（宽表列名）
            for k in row:
                if _DATE8_RE.match(str(k)):
                    dates.append(str(k))
    return max(dates) if dates else None


def render_inventory(data: dict) -> str:
    meta = data.get("meta", {})
    blocks = data.get("blocks", {})

    lines = [
        f"# data_inventory · {meta.get('name', '?')} {meta.get('code', '?')} · {meta.get('as_of', '?')}",
        "",
        "## Block 覆盖矩阵",
        "",
        "| Block | 行数 | 最新日期 | 健康度 |",
        "|---|---|---|---|",
    ]
    for name, block in blocks.items():
        rows = len(block) if isinstance(block, list) else 0
        latest = latest_date_of(block) if isinstance(block, list) else None
        lines.append(f"| {name} | {rows} | {latest or '—'} | {health_of(rows, latest)} |")

    # Top-level 字段
    lines += ["", "## 顶层字段（v3 规范字段）", "", "| 字段 | 行数 | 状态 |", "|---|---|---|"]
    for top_field in ["kline_daily", "financials", "business_segments", "top_holders", "news"]:
        val = data.get(top_field)
        rows = len(val) if isinstance(val, list) else (1 if val else 0)
        status = "✅" if rows > 0 else "❌ 缺失"
        lines.append(f"| {top_field} | {rows} | {status} |")

    # Step 映射
    lines += ["", "## Step 字段需求映射", "", "| Step | 必需字段 | 状态 |", "|---|---|---|"]
    for step, fields in STEP_FIELDS.items():
        # 字段可能在 blocks 内，也可能是 data.json 顶层字段
        missing = [f for f in fields if not (blocks.get(f) or data.get(f))]
        if missing:
            status = f"❌ 缺 {', '.join(missing)}"
        else:
            status = "✅"
        lines.append(f"| {step} | {', '.join(fields)} | {status} |")

    # 推荐补全
    missing_set = set()
    for step, fields in STEP_FIELDS.items():
        for f in fields:
            if not (blocks.get(f) or data.get(f)):
                missing_set.add(f)
    if missing_set:
        lines += ["", "## 推荐补全", ""]
        for m in sorted(missing_set):
            lines.append(f"- [ ] {m} → web_fetch / 调研补 / 显式 [GAP]")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="Path to data.json")
    p.add_argument("--out", required=True, help="Output data_inventory.md path")
    args = p.parse_args()

    data = json.loads(Path(args.data).read_text())
    Path(args.out).write_text(render_inventory(data))
    print(f"[OK] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""verify_facts.py · Phase 2 数字标签反查脚本。

输入：report.md + data.json + anomalies.json
输出：PASS/FAIL/WARN 列表；退出码 0 / 1 / 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r'\[(F|C|I|T|GAP):([^\]]+)\]')

# 解决方案 2: 只匹配数字字面量，不做单位归一化
NUM_RE = re.compile(r'(-?\d+\.?\d*)\s*(亿|万|%|倍|元|万手|手)?')


@dataclass
class Tag:
    kind: str        # 'F' / 'C' / 'I' / 'T' / 'GAP'
    payload: str     # path / formula / reason / assumption / field
    line_no: int
    line: str        # 整行内容（用于反查上下文）
    col: int         # 标签在行中起始列


def extract_tags(text: str) -> list[Tag]:
    """parse MD 文本，返回所有标签。"""
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in TAG_RE.finditer(line):
            out.append(Tag(
                kind=m.group(1),
                payload=m.group(2).strip(),
                line_no=line_no,
                line=line,
                col=m.start(),
            ))
    return out


def resolve_path(data: Any, path: str) -> Any:
    """解析点号 + 下标 path，如 'financials.2025.revenue' 或 'kline_daily[-1][2]'."""
    tokens = re.findall(r'[^.\[\]]+|\[-?\d+\]', path)
    cur = data
    for tok in tokens:
        if tok.startswith('[') and tok.endswith(']'):
            idx = int(tok[1:-1])
            if not isinstance(cur, list):
                raise KeyError(f"path token {tok} expects list, got {type(cur).__name__}")
            cur = cur[idx]
        else:
            if isinstance(cur, list):
                try:
                    cur = cur[int(tok)]
                except (ValueError, IndexError):
                    raise KeyError(f"path token {tok} invalid for list")
            elif isinstance(cur, dict):
                if tok not in cur:
                    raise KeyError(f"path token {tok} not in dict (keys: {list(cur.keys())[:5]})")
                cur = cur[tok]
            else:
                raise KeyError(f"cannot index {type(cur).__name__} with {tok}")
    return cur


def parse_nearest_number(line: str, col: int) -> float | None:
    """在 line 中找距离 col 最近的（位置在标签之前的）数字字面量。
    解决方案 2: 不做单位归一化，直接返回字面量数值。
    """
    matches = list(NUM_RE.finditer(line[:col]))
    if not matches:
        return None
    last = matches[-1]
    try:
        return float(last.group(1))
    except ValueError:
        return None


def rel_diff(a: float, b: float) -> float:
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def check_f_tag(tag: Tag, data: Any) -> dict | None:
    """返回 None 表示 PASS，否则返回 fail dict。"""
    try:
        expected = float(resolve_path(data, tag.payload))
    except (KeyError, ValueError, TypeError) as e:
        return {
            "kind": "FAIL", "tag": f"[F:{tag.payload}]", "line": tag.line_no,
            "reason": f"path 解析失败：{e}",
            "fix": f"修正 line {tag.line_no} 标签 path，或确认字段存在于 data.json"
        }
    actual = parse_nearest_number(tag.line, tag.col)
    if actual is None:
        return {
            "kind": "FAIL", "tag": f"[F:{tag.payload}]", "line": tag.line_no,
            "reason": "标签前未找到数字",
            "fix": f"line {tag.line_no} 标签前应紧跟数字（含单位）"
        }
    if rel_diff(actual, expected) > 0.01:
        return {
            "kind": "FAIL", "tag": f"[F:{tag.payload}]", "line": tag.line_no,
            "reason": f"标 {actual:.4g} vs data.json {expected:.4g}，差 {rel_diff(actual, expected)*100:.1f}%",
            "fix": f"修改 line {tag.line_no} 数字与单位（亿/万/%），或调整 path"
        }
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--anomalies", required=False, default=None)
    p.add_argument("--mode", choices=["partial", "full"], default="full")
    args = p.parse_args()

    md_text = Path(args.report).read_text()
    data = json.loads(Path(args.data).read_text())

    tags = extract_tags(md_text)
    fails, warns = [], []
    for t in tags:
        if t.kind == 'F':
            r = check_f_tag(t, data)
            if r: fails.append(r)
    print(f"=== verify_facts · {len(tags)} tags ===")
    for f in fails:
        print(f"[{f['kind']}] L{f['line']} {f['tag']}: {f['reason']}")
        print(f"  fix: {f['fix']}")
    print(f"\n[PASS] {len(tags)-len(fails)-len(warns)} / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


if __name__ == "__main__":
    raise SystemExit(main())

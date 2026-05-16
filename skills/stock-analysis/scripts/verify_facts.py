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

TAG_RE = re.compile(r'\[(F|C|I|T|GAP):((?:[^\[\]]|\[-?\d+\])+)\]')

# 解决方案 2: 只匹配数字字面量，不做单位归一化
NUM_RE = re.compile(r'(-?\d+\.?\d*)\s*(亿|万|%|倍|元|万手|手)?')


# v3.2: 标签单位归一化
UNIT_SCALES = {
    "亿": 1e8,
    "万": 1e4,
    "千": 1e3,
    "%": 1,      # akshare 百分比字段已是 0-100 区间，不缩放
    "pct": 1,    # 同 %，文档习惯
    "倍": 1,
    "元": 1,     # 默认，等价于不带后缀
}


def parse_payload(payload: str) -> tuple[str, str | None]:
    """拆 path|unit 后缀。返回 (path, unit)，无后缀时 unit=None。"""
    if '|' in payload:
        path, unit = payload.rsplit('|', 1)
        return path.strip(), unit.strip()
    return payload, None


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
    """返回 None 表示 PASS，否则返回 fail dict。v3.2 支持 |单位 后缀。"""
    path, unit = parse_payload(tag.payload)
    try:
        raw = resolve_path(data, path)
        expected = float(raw) / UNIT_SCALES.get(unit, 1) if unit else float(raw)
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
        unit_str = f" {unit}" if unit else ""
        return {
            "kind": "FAIL", "tag": f"[F:{tag.payload}]", "line": tag.line_no,
            "reason": f"标 {actual:.4g}{unit_str} vs data.json normalized {expected:.4g}{unit_str}，差 {rel_diff(actual, expected)*100:.1f}%",
            "fix": f"修改 line {tag.line_no} 数字、单位或调整 |单位 后缀"
        }
    return None


FORMULA_TOKEN = re.compile(r'[\w\.\[\]\-]+')


def eval_formula(formula: str, data: Any) -> float:
    """解析 [C:] 公式：path 引用替换为数值后 eval。仅允许 + - * / 与数字。"""
    def replace(m):
        tok = m.group(0)
        # 单字符运算符直接放行（修 v3.1 独立 `-` 陷阱）
        if tok in ('-', '+', '*', '/'):
            return tok
        # 数字字面量（含负号 / 科学记数法）
        if tok.replace('.', '').replace('-', '').replace('e', '').replace('E', '').isdigit():
            return tok
        try:
            v = resolve_path(data, tok)
            return str(float(v))
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"formula token {tok} 无法解析")
    replaced = FORMULA_TOKEN.sub(replace, formula)
    if re.search(r'[^0-9.\-\+\*/()\s eE]', replaced):
        raise ValueError(f"formula 含非法字符：{replaced}")
    return eval(replaced)  # noqa: S307 — 已限制字符集


def check_c_tag(tag: Tag, data: Any) -> dict | None:
    try:
        expected = eval_formula(tag.payload, data)
    except Exception as e:
        return {
            "kind": "FAIL", "tag": f"[C:{tag.payload}]", "line": tag.line_no,
            "reason": f"公式求值失败：{e}",
            "fix": f"line {tag.line_no} 修正公式或字段"
        }
    actual = parse_nearest_number(tag.line, tag.col)
    if actual is None or rel_diff(actual, expected) > 0.01:
        return {
            "kind": "FAIL", "tag": f"[C:{tag.payload}]", "line": tag.line_no,
            "reason": f"标 {actual} vs 公式算出 {expected:.4g}",
            "fix": f"修改 line {tag.line_no} 数字或公式"
        }
    return None


def check_i_tag(tag: Tag) -> dict | None:
    if len(tag.payload.strip()) < 4:
        return {
            "kind": "FAIL", "tag": f"[I:{tag.payload}]", "line": tag.line_no,
            "reason": "推断依据过短（< 4 字）",
            "fix": f"line {tag.line_no} 提供更具体的中文依据（如'行业常识·龙头地位'）"
        }
    return None


def check_t_tag(tag: Tag, full_text: str) -> dict | None:
    """[T:] 400 字内须有'失效条件'。"""
    idx = full_text.find(tag.line) if tag.line in full_text else 0
    window = full_text[idx: idx + 400]
    if '失效条件' not in window:
        return {
            "kind": "WARN", "tag": f"[T:{tag.payload}]", "line": tag.line_no,
            "reason": "标签后 400 字内未出现'失效条件'",
            "fix": f"line {tag.line_no} 后追加 '失效条件:' 段，列出 2-3 条可观测信号"
        }
    return None


def extract_step_section(md: str, step_marker: str) -> str:
    """提取 'Step 0.5' 标题到下一个 'Step ' 之间的文本。"""
    lines = md.splitlines()
    start, end = None, len(lines)
    for i, l in enumerate(lines):
        if step_marker in l and start is None:
            start = i
        elif start is not None and re.match(r'^#+\s+Step\s+', l) and i > start:
            end = i
            break
    return "\n".join(lines[start:end]) if start is not None else ""


def check_anomaly_coverage(anomalies: dict, md: str) -> list[dict]:
    """CRITICAL anomaly 的 indicator 必须出现在 Step 0.5 section。"""
    out = []
    step05 = extract_step_section(md, "Step 0.5")
    for a in anomalies.get("items", []):
        if a["severity"] == "CRITICAL":
            if a["indicator"] not in step05:
                out.append({
                    "kind": "FAIL", "tag": f"anomaly {a['id']}", "line": 0,
                    "reason": f"CRITICAL anomaly {a['id']} ({a['indicator']}) 未在 Step 0.5 出现",
                    "fix": f"在 part1 Step 0.5 中插入一段 ≥80 字分析，引用 [F:{a.get('blocks_ref', '')}]"
                })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--anomalies", required=False, default=None)
    p.add_argument("--mode", choices=["partial", "full"], default="full")
    args = p.parse_args()

    md_text = Path(args.report).read_text()
    data = json.loads(Path(args.data).read_text())
    anomalies = json.loads(Path(args.anomalies).read_text()) if args.anomalies else {"items": []}

    tags = extract_tags(md_text)
    fails, warns = [], []

    for t in tags:
        r = None
        if t.kind == 'F':   r = check_f_tag(t, data)
        elif t.kind == 'C': r = check_c_tag(t, data)
        elif t.kind == 'I': r = check_i_tag(t)
        elif t.kind == 'T': r = check_t_tag(t, md_text)
        if r:
            (warns if r['kind'] == 'WARN' else fails).append(r)

    if args.mode == 'full' and anomalies['items']:
        fails += check_anomaly_coverage(anomalies, md_text)

    print(f"=== verify_facts · {args.mode} · {len(tags)} tags ===")
    for r in fails + warns:
        print(f"[{r['kind']}] L{r['line']} {r['tag']}: {r['reason']}")
        print(f"  fix: {r['fix']}")
    print(f"\n[PASS] {len(tags) - len(fails) - len(warns)} / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


if __name__ == "__main__":
    raise SystemExit(main())

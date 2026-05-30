"""verify_facts.py · 校验单模块 data.json ↔ report.md 标签对齐。

检查 report.md 中的 [F:] [C:] 标签与 data.json 数据一致性。
复用了 stock-analysis 的标签校验逻辑，适配 market-review 的输出结构。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r'\[(F|C|I|T):([^\[\]]+)\]')
NUM_RE = re.compile(r'(-?\d+\.?\d*)\s*(亿|万|%|倍|元|万手|手)?')

UNIT_SCALES = {
    "亿": 1e8, "万": 1e4, "千": 1e3,
    "%": 1, "pct": 1, "倍": 1, "元": 1,
}

ALLOWED_FUNCS = {'pow': pow, 'sqrt': math.sqrt, 'abs': abs}
FORMULA_TOKEN = re.compile(r'[\w\.\[\]\-\|]+')


def parse_payload(payload: str) -> tuple[str, str | None]:
    if '|' in payload:
        path, unit = payload.rsplit('|', 1)
        return path.strip(), unit.strip()
    return payload, None


def resolve_path(data: Any, path: str) -> Any:
    tokens = re.findall(r'[^.\[\]]+|\[-?\d+\]', path)
    cur = data
    for tok in tokens:
        if tok.startswith('[') and tok.endswith(']'):
            idx = int(tok[1:-1])
            if not isinstance(cur, list):
                raise KeyError(f"expects list, got {type(cur).__name__}")
            cur = cur[idx]
        else:
            if isinstance(cur, list):
                cur = cur[int(tok)]
            elif isinstance(cur, dict):
                if tok not in cur:
                    raise KeyError(f"{tok} not in dict")
                cur = cur[tok]
            else:
                raise KeyError(f"cannot index {type(cur).__name__}")
    return cur


def parse_nearest_number(line: str, col: int) -> float | None:
    matches = list(NUM_RE.finditer(line[:col]))
    if not matches:
        return None
    try:
        return float(matches[-1].group(1))
    except ValueError:
        return None


def rel_diff(a: float, b: float) -> float:
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def check_f_tag(tag_payload: str, data: Any, line_no: int, line: str, col: int) -> dict | None:
    path, unit = parse_payload(tag_payload)
    try:
        raw = resolve_path(data, path)
        expected = float(raw) / UNIT_SCALES.get(unit, 1) if unit else float(raw)
    except (KeyError, ValueError, TypeError) as e:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": f"path 解析失败：{e}",
        }
    actual = parse_nearest_number(line, col)
    if actual is None:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": "标签前未找到数字",
        }
    if rel_diff(actual, expected) > 0.01:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": f"标 {actual} vs data.json {expected:.4g}，差 {rel_diff(actual, expected)*100:.1f}%",
        }
    return None


def eval_formula(formula: str, data: Any) -> float:
    def replace(m):
        tok = m.group(0)
        if tok in ('-', '+', '*', '/'):
            return tok
        if tok.replace('.', '').replace('-', '').replace('e', '').replace('E', '').isdigit():
            return tok
        if tok in ALLOWED_FUNCS:
            return tok
        path, unit = parse_payload(tok)
        try:
            v = resolve_path(data, path)
            return str(float(v) / UNIT_SCALES.get(unit, 1) if unit else float(v))
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"token {tok} 无法解析")
    replaced = FORMULA_TOKEN.sub(replace, formula)
    return eval(replaced, {"__builtins__": None}, ALLOWED_FUNCS)  # noqa: S307


def check_c_tag(tag_payload: str, data: Any, line_no: int, line: str, col: int) -> dict | None:
    try:
        expected = eval_formula(tag_payload, data)
    except Exception as e:
        return {"kind": "FAIL", "tag": f"[C:{tag_payload}]", "line": line_no, "reason": str(e)}
    actual = parse_nearest_number(line, col)
    if actual is None or rel_diff(actual, expected) > 0.01:
        return {"kind": "FAIL", "tag": f"[C:{tag_payload}]", "line": line_no,
                "reason": f"标 {actual} vs 公式算出 {expected:.4g}"}
    return None


def check_i_tag(tag_payload: str, line_no: int) -> dict | None:
    if len(tag_payload.strip()) < 4:
        return {"kind": "FAIL", "tag": f"[I:{tag_payload}]", "line": line_no,
                "reason": "推断依据过短（< 4 字）"}
    return None


def verify_module(data_path: Path, report_path: Path) -> int:
    md_text = report_path.read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    tags = list(TAG_RE.finditer(md_text))
    fails, warns = [], []

    for m in tags:
        kind = m.group(1)
        payload = m.group(2).strip()
        line_no = md_text[:m.start()].count('\n') + 1
        line_start = md_text.rfind('\n', 0, m.start()) + 1
        line_end = md_text.find('\n', m.start())
        if line_end == -1:
            line_end = len(md_text)
        line = md_text[line_start:line_end]
        col = m.start() - line_start

        r = None
        if kind == 'F':
            r = check_f_tag(payload, data, line_no, line, col)
        elif kind == 'C':
            r = check_c_tag(payload, data, line_no, line, col)
        elif kind == 'I':
            r = check_i_tag(payload, line_no)

        if r:
            (warns if r['kind'] == 'WARN' else fails).append(r)

    print(f"=== verify_facts · {len(tags)} tags ===")
    for r in fails + warns:
        print(f"[{r['kind']}] L{r.get('line', '?')} {r['tag']}: {r['reason']}")
    print(f"\n[PASS] {len(tags) - len(fails) - len(warns)} / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--module", required=True, help="模块名")
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    data_path = Path(args.output_dir) / args.ymd / args.module / "data.json"
    report_path = Path(args.output_dir) / args.ymd / args.module / "report.md"

    if not data_path.exists():
        print(f"ERROR: {data_path} not found", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"ERROR: {report_path} not found", file=sys.stderr)
        return 1

    return verify_module(data_path, report_path)


if __name__ == "__main__":
    raise SystemExit(main())

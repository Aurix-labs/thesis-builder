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


def strip_invariants_block(report_md: str) -> str:
    """从 report_md 中删除 invariants 块内容，保留行数（用空行替换），
    避免正文扫描误匹配 invariants 内 keyword + 数字组合，同时维持 line_no。"""
    m = INVARIANTS_RE.search(report_md)
    if not m:
        return report_md
    block_text = report_md[m.start(): m.end()]
    blank_replacement = '\n' * block_text.count('\n')
    return report_md[:m.start()] + blank_replacement + report_md[m.end():]


def safe_eval_expr(expr: str, ctx: dict) -> float:
    """安全 eval 算式字符串：只允许 + - * / ( ) 与 ctx 字典里的变量名。
    返回 float。"""
    # 替换变量名为数值
    def replace_name(m):
        name = m.group(0)
        if name in ctx:
            return str(float(ctx[name]))
        # 数字字面量
        try:
            float(name)
            return name
        except ValueError:
            raise ValueError(f"未知变量：{name}")

    # 抓 [A-Za-z_][\w]*|数字
    name_re = re.compile(r'[A-Za-z_]\w*|\d+\.?\d*')
    replaced = name_re.sub(replace_name, expr)
    if re.search(r'[^0-9.\-\+\*/()\s]', replaced):
        raise ValueError(f"算式含非法字符：{replaced}")
    try:
        return float(eval(replaced))  # noqa: S307
    except ZeroDivisionError:
        raise ValueError(f"算式除零：{expr}")


def find_keyword_near_number(report_md: str, keywords: list[str]) -> list[tuple[int, float, str]]:
    """扫描 report_md，找到任一 keyword 后同行 ±40 字符内的数字。
    返回 [(line_no, number, matched_keyword), ...]，按 (line_no, number) 去重
    （重叠别名如 ["市值", "总市值"] 命中同一 span 时，保留更长的别名）。"""
    raw: list[tuple[int, float, str]] = []
    for line_no, line in enumerate(report_md.splitlines(), 1):
        for kw in keywords:
            for m in re.finditer(re.escape(kw), line):
                # 向后扫 40 字符找数字
                window = line[m.end(): m.end() + 40]
                num_match = re.search(r'(-?\d+\.?\d*)', window)
                if num_match:
                    raw.append((line_no, float(num_match.group(1)), kw))
                    break
    # 去重：同 (line_no, number) 只保留首次（更长的别名优先）
    raw.sort(key=lambda t: -len(t[2]))
    seen: set[tuple[int, float]] = set()
    out: list[tuple[int, float, str]] = []
    for line_no, num, kw in raw:
        key = (line_no, num)
        if key not in seen:
            seen.add(key)
            out.append((line_no, num, kw))
    return out


def check_derived(inv: dict, report_md: str, fails: list) -> None:
    """CONS-derived: derived.X 算式重算 = 正文出现的同名 keyword 附近数字 ±1%"""
    constants = inv.get('constants', {})
    derived_exprs = inv.get('derived', {})
    keywords = inv.get('keywords', {})

    # 构造 eval 上下文：constants + 先算出的 derived
    ctx = dict(constants)
    body_only = strip_invariants_block(report_md)
    for key, expr in derived_exprs.items():
        if isinstance(expr, str):
            try:
                value = safe_eval_expr(expr, ctx)
            except (ValueError, KeyError, ZeroDivisionError) as e:
                fails.append({
                    'check': 'CONS-derived',
                    'location': f'invariants.derived.{key}',
                    'expected': f'算式 {expr} 重算',
                    'actual':   f'求值失败：{e}',
                    'fix':      f'修正 invariants.derived.{key} 算式或 constants',
                })
                continue
        else:
            value = float(expr)  # 直接声明数值
        ctx[key] = value

        # 扫正文找 keyword 附近数字（剥离 invariants 块，避免自扫）
        kw_list = keywords.get(key, [])
        if not kw_list:
            continue  # 没有 keyword 别名表，跳过正文比对
        occurrences = find_keyword_near_number(body_only, kw_list)
        for line_no, num, kw in occurrences:
            if abs(num - value) / max(abs(value), 1e-9) > 0.01:
                fails.append({
                    'check': 'CONS-derived',
                    'location': f'line {line_no} (near keyword "{kw}")',
                    'expected': f'{value:.4g} (from derived.{key} = {expr})',
                    'actual':   f'{num:.4g}',
                    'fix':      f'修正 line {line_no} 数字为 {value:.4g}，或更新 invariants.derived.{key}',
                })


def check_target_mult(inv: dict, fails: list) -> None:
    """CONS-target-mult: targets.{level}.{low,high} == pe_{low,high} * ctx[eps_var]"""
    constants = inv.get('constants', {})
    derived_exprs = inv.get('derived', {})
    targets = inv.get('targets', {})

    # 构造 eval 上下文（含 derived 重算值）
    ctx = dict(constants)
    for key, expr in derived_exprs.items():
        if isinstance(expr, str):
            try:
                ctx[key] = safe_eval_expr(expr, ctx)
            except Exception:
                pass  # 跳过——CONS-derived 已经报这个错
        else:
            ctx[key] = float(expr)

    for level in ('short', 'mid', 'long'):
        t = targets.get(level)
        if not t:
            fails.append({
                'check': 'CONS-target-mult',
                'location': f'invariants.targets.{level}',
                'expected': 'low/high/pe_low/pe_high/eps_var 5 字段齐全',
                'actual':   '缺失',
                'fix':      f'补齐 invariants.targets.{level}',
            })
            continue
        eps_var = t.get('eps_var')
        eps = ctx.get(eps_var)
        if eps is None:
            fails.append({
                'check': 'CONS-target-mult',
                'location': f'invariants.targets.{level}.eps_var',
                'expected': f'{eps_var} 应在 constants 或 derived 中定义',
                'actual':   f'未找到',
                'fix':      f'在 invariants.constants 中加 {eps_var}',
            })
            continue
        for bound in ('low', 'high'):
            declared = float(t.get(bound, 0))
            pe = float(t.get(f'pe_{bound}', 0))
            expected = pe * eps
            if abs(declared - expected) / max(abs(expected), 1e-9) > 0.01:
                fails.append({
                    'check': 'CONS-target-mult',
                    'location': f'invariants.targets.{level}.{bound}',
                    'expected': f'pe_{bound}({pe}) * {eps_var}({eps}) = {expected:.2f}',
                    'actual':   f'{declared}',
                    'fix':      f'修正 targets.{level}.{bound} 为 {expected:.2f}，或调整 pe_{bound}/{eps_var}',
                })


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
    check_derived(inv, report_md, fails)
    check_target_mult(inv, fails)
    # 后续 task B4-B7 逐步加 check_anomaly_titles / check_baseline_eps / check_score_consistency / expand_explicit_refs

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

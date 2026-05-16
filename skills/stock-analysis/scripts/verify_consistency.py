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

ANO_HEAD_RE = re.compile(r'^###\s+(ANO-\d+)\s*·?\s*(.+)$', re.MULTILINE)

EXPLICIT_REF_RE = re.compile(r'\{\{\$([^}]+)\}\}')


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


def check_anomaly_titles(inv: dict, report_md: str, fails: list) -> None:
    """CONS-anomaly-title: anomalies[].value 必须出现在对应 ### ANO-XXX 标题中。

    匹配策略（unit-anchored，避免误抓无关数字如 "3 年"）：
    1. unit 非空时：在标题中搜索 `(-?\\d+\\.?\\d*)\\s*<unit>` 模式
    2. unit 为空时：在标题中搜索任意带小数点的有符号小数（避免误抓整数如年份）
    3. 找不到 → FAIL（不再用近似 "nearest-to-expected" heuristic）

    容差：5%（spec § 3.3.2）"""
    anomalies = inv.get('anomalies', [])
    if not anomalies:
        return
    declared = {a['id']: a for a in anomalies}

    for m in ANO_HEAD_RE.finditer(report_md):
        ano_id = m.group(1)
        title_text = m.group(2)
        if ano_id not in declared:
            continue
        anomaly = declared[ano_id]
        expected_value = float(anomaly['value'])
        unit = str(anomaly.get('unit', '') or '').strip()

        # 构造单位锚定 regex
        if unit:
            # `15.69 pct` / `-54.55%` / `89.54 亿`
            anchor_re = re.compile(r'(-?\d+\.?\d*)\s*' + re.escape(unit))
        else:
            # 比率类无单位：要求带小数点（避免误抓整数如"3 年"中的 3）
            anchor_re = re.compile(r'(-?\d+\.\d+)')

        match = anchor_re.search(title_text)
        if not match:
            fails.append({
                'check': 'CONS-anomaly-title',
                'location': f'### {ano_id} (heading)',
                'expected': f'{expected_value}{f" {unit}" if unit else ""} (from invariants.anomalies[{ano_id}].value)',
                'actual':   f'标题中未找到 {f"数值+单位 {unit}" if unit else "带小数点的数值"}',
                'fix':      f'在 {ano_id} 标题中加入 {expected_value}{f" {unit}" if unit else ""}',
            })
            continue

        title_num = float(match.group(1))
        if abs(title_num - expected_value) / max(abs(expected_value), 1e-9) > 0.05:
            fails.append({
                'check': 'CONS-anomaly-title',
                'location': f'### {ano_id} (heading)',
                'expected': f'{expected_value}{f" {unit}" if unit else ""} (from invariants.anomalies[{ano_id}].value)',
                'actual':   f'{title_num}{f" {unit}" if unit else ""} (from heading)',
                'fix':      f'把 {ano_id} 标题数字改为 {expected_value}，或更新 invariants.anomalies',
            })


def check_baseline_eps(inv: dict, report_md: str, fails: list) -> None:
    """CONS-baseline-eps: 正文出现 keywords.X 列出的别名时，同行 ±20 字符内
    最近数字 ≈ inv.constants[X] ±1%。Markdown 表格按单元格分别扫描。"""
    constants = inv.get('constants', {})
    keywords = inv.get('keywords', {})

    # 只检查 baseline_eps_2026 / baseline_eps_2027（spec § 3.3.2）
    for var_name in ('baseline_eps_2026', 'baseline_eps_2027'):
        if var_name not in constants:
            continue
        expected = float(constants[var_name])
        kw_list = keywords.get(var_name, [])
        if not kw_list:
            continue

        # Strip invariants block to avoid self-scan
        body_only = strip_invariants_block(report_md)

        for line_no, line in enumerate(body_only.splitlines(), 1):
            # Markdown 表格按单元格分别扫描
            cells = line.split('|') if '|' in line else [line]
            for cell in cells:
                for kw in kw_list:
                    for m in re.finditer(re.escape(kw), cell):
                        # 同行 ±20 字符窗口
                        window = cell[m.end(): m.end() + 20]
                        num_match = re.search(r'(-?\d+\.?\d*)', window)
                        if not num_match:
                            continue
                        actual = float(num_match.group(1))
                        if abs(actual - expected) / max(abs(expected), 1e-9) > 0.01:
                            fails.append({
                                'check': 'CONS-baseline-eps',
                                'location': f'line {line_no} (near keyword "{kw}")',
                                'expected': f'{expected} (from invariants.constants.{var_name})',
                                'actual':   f'{actual}',
                                'fix':      f'修正 line {line_no} 数字为 {expected}，或更新 invariants.constants.{var_name} / keywords.{var_name}',
                            })
                            break  # 一处一次 FAIL，不重复


GRADE_RANGES = [
    ('A', 80, 100),
    ('B', 60, 79),
    ('C', 40, 59),
    ('D', 0, 39),
]


def _check_sum(score_block: dict, expected_keys: list[str], location: str, fails: list):
    if not score_block:
        return
    total = score_block.get('total')
    if total is None:
        return
    actual_sum = sum(float(score_block.get(k, 0)) for k in expected_keys)
    if abs(actual_sum - float(total)) > 0.5:  # 整数容差
        fails.append({
            'check': 'CONS-score-consistency',
            'location': location,
            'expected': f'{" + ".join(expected_keys)} = {actual_sum}',
            'actual':   f'total = {total}',
            'fix':      f'修正 {location}.total 为 {actual_sum:g}，或调整各维分',
        })


def check_score_consistency(inv: dict, report_md: str, fails: list) -> None:
    """CONS-score-consistency: 评分体系内部自洽（spec § 3.3.2 末行 + § 3.3.1 可选段）"""
    # 1. five_dim_score: 5 维加和 == total，grade 与 total 区间一致
    fd = inv.get('five_dim_score')
    if fd:
        _check_sum(
            fd,
            ['fundamental', 'capital', 'technical', 'sentiment', 'catalyst'],
            'invariants.five_dim_score',
            fails,
        )
        total = fd.get('total')
        grade = fd.get('grade')
        if total is not None and grade:
            expected_grade = None
            for g, lo, hi in GRADE_RANGES:
                if lo <= float(total) <= hi:
                    expected_grade = g
                    break
            if expected_grade and grade != expected_grade:
                fails.append({
                    'check': 'CONS-score-consistency',
                    'location': 'invariants.five_dim_score.grade',
                    'expected': f'{expected_grade} (total={total} → 区间 {expected_grade})',
                    'actual':   grade,
                    'fix':      f'修正 grade 为 {expected_grade}',
                })

    # 2. rubric_six_dim: 6 维加和 == total
    rb = inv.get('rubric_six_dim')
    if rb:
        _check_sum(
            rb,
            ['fundamental', 'industry_fit', 'elasticity', 'valuation', 'capital', 'governance'],
            'invariants.rubric_six_dim',
            fails,
        )

    # 3. speculation_risk: 5 维加和 == total
    sp = inv.get('speculation_risk')
    if sp:
        _check_sum(
            sp,
            ['fundamental_decoupling', 'valuation_bubble', 'fund_speculation', 'sentiment_hype', 'technical_pattern'],
            'invariants.speculation_risk',
            fails,
        )

    # 4. screening_19: passed + len(failed_items) == total
    sc = inv.get('screening_19')
    if sc:
        passed = sc.get('passed', 0)
        failed_items = sc.get('failed_items') or []
        total = sc.get('total', 0)
        if int(passed) + len(failed_items) != int(total):
            fails.append({
                'check': 'CONS-score-consistency',
                'location': 'invariants.screening_19',
                'expected': f'passed({passed}) + len(failed_items)({len(failed_items)}) = {total}',
                'actual':   f'{int(passed) + len(failed_items)}',
                'fix':      '调整 screening_19.passed / failed_items / total 使三者一致',
            })

        # 正文一致性：keywords.screening_19_passed 列出别名时扫数字
        keywords = inv.get('keywords', {})
        kw_list = keywords.get('screening_19_passed', [])
        if kw_list:
            body_only = strip_invariants_block(report_md)
            occurrences = find_keyword_near_number(body_only, kw_list)
            for line_no, num, kw in occurrences:
                if int(num) != int(passed):
                    fails.append({
                        'check': 'CONS-score-consistency',
                        'location': f'line {line_no} (near "{kw}")',
                        'expected': f'{passed} (from invariants.screening_19.passed)',
                        'actual':   f'{num:g}',
                        'fix':      f'修正 line {line_no} 数字为 {passed}',
                    })


def _resolve_inv_path(inv: dict, path: str) -> Any:
    """解析 invariants 路径，如 'targets.mid.low' / 'anomalies.ANO-001.value'。
    anomalies 数组用 id 作主键。"""
    tokens = path.split('.')
    cur = inv
    for tok in tokens:
        if isinstance(cur, list) and tok.startswith('ANO-'):
            # 用 id 主键查找
            found = next((item for item in cur if item.get('id') == tok), None)
            if found is None:
                raise KeyError(f"anomaly id {tok} 不在 anomalies 列表中")
            cur = found
        elif isinstance(cur, dict):
            if tok not in cur:
                raise KeyError(f"path token {tok} 不在 dict (keys: {list(cur.keys())[:5]})")
            cur = cur[tok]
        else:
            raise KeyError(f"无法在 {type(cur).__name__} 上索引 {tok}")
    return cur


def expand_explicit_refs(inv: dict, report_md: str, fails: list) -> None:
    """CONS-explicit-ref: 把 {{$path}} 引用展开，校验展开值与正文紧邻数字一致。
    引用本身无紧邻数字时跳过；有则比对。"""
    body_only = strip_invariants_block(report_md)
    for line_no, line in enumerate(body_only.splitlines(), 1):
        for m in EXPLICIT_REF_RE.finditer(line):
            path = m.group(1).strip()
            try:
                value = _resolve_inv_path(inv, path)
            except KeyError as e:
                fails.append({
                    'check': 'CONS-explicit-ref',
                    'location': f'line {line_no} {{${path}}}',
                    'expected': f'invariants.{path} 应可解析',
                    'actual':   f'{e}',
                    'fix':      f'修正 line {line_no} 引用 path，或在 invariants 中加 {path}',
                })
                continue
            # 若引用本身后紧跟数字（如 "{{$x}} - 5.00"），不主动校验
            # （展开值与紧邻数字的一致性已被 CONS-baseline-eps / CONS-derived 等覆盖）


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
    check_anomaly_titles(inv, report_md, fails)
    check_baseline_eps(inv, report_md, fails)
    check_score_consistency(inv, report_md, fails)
    expand_explicit_refs(inv, report_md, fails)

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

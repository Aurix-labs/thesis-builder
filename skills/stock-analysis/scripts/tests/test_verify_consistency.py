"""测试 verify_consistency.py 跨节一致性"""
import subprocess
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SCRIPT = Path(__file__).parent.parent / 'verify_consistency.py'


def _run(report_text: str, data_dict: dict | None = None):
    """辅助：写临时 report.md + data.json 跑 verify_consistency.py"""
    with tempfile.TemporaryDirectory() as td:
        r = Path(td) / 'r.md'
        d = Path(td) / 'd.json'
        r.write_text(report_text)
        d.write_text(json.dumps(data_dict or {}))
        return subprocess.run(
            ['python', str(SCRIPT), '--report', str(r), '--data', str(d)],
            capture_output=True, text=True
        )


INVARIANTS_HEAD = '''<!-- invariants v3.2 -->
```yaml
{yaml_body}
```

# 报告正文
'''


def test_missing_invariants_block_warns_not_fails():
    """UT-14 · 无 invariants 块的旧报告 → WARN，退出码 0"""
    result = _run("# 普通报告\n\n营收 100 亿 [F:foo]")
    assert result.returncode == 0
    assert 'WARN' in result.stdout
    assert 'invariants block' in result.stdout


def test_cons_derived_market_cap_consistent_with_body():
    """UT-06 · 正文出现的 market_cap_yi 数字 = derived 算式重算值 → PASS"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived:
  market_cap_yi: "price * shares"
keywords:
  baseline_eps_2026: ["基准 EPS26"]
  market_cap_yi: ["市值", "总市值"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    body = '当前总市值 3372.29 亿元。'  # 86.87 * 38.82 = 3372.2934 ≈ 3372.29 ±1%
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 0, f"应 PASS 但得到：\n{result.stdout}"


def test_cons_derived_market_cap_mismatch_fails():
    """UT-07 · 正文写错的 market_cap_yi 数字 → FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived:
  market_cap_yi: "price * shares"
keywords:
  baseline_eps_2026: ["基准 EPS26"]
  market_cap_yi: ["市值", "总市值"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    body = '当前总市值 9999.99 亿元。'   # 错的
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1, f"应 FAIL 但得到：\n{result.stdout}"
    assert 'CONS-derived' in result.stdout
    assert 'expected' in result.stdout


def test_cons_derived_handles_zero_division():
    """B2 fix · derived 算式除零应产生 FAIL，而非 crash"""
    yaml_body = '''constants:
  numerator: 10
  zero_const: 0
derived:
  bad: "numerator / zero_const"
keywords:
  bad: ["bad value"]
targets:
  short: {low: 1, high: 1, pe_low: 1, pe_high: 1, eps_var: numerator}
  mid:   {low: 1, high: 1, pe_low: 1, pe_high: 1, eps_var: numerator}
  long:  {low: 1, high: 1, pe_low: 1, pe_high: 1, eps_var: numerator}
anomalies: []
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + 'bad value 999')
    # Expect: returncode 1, contains CONS-derived FAIL, no Python traceback
    assert result.returncode == 1
    assert 'Traceback' not in result.stdout
    assert 'Traceback' not in result.stderr
    assert 'CONS-derived' in result.stdout


def test_cons_derived_skips_invariants_block_when_scanning_body():
    """B2 fix · 正文扫描不应误匹配 invariants 块内字符串"""
    yaml_body = '''constants:
  price: 100
  shares: 10
derived:
  market_cap_yi: "price * shares"
keywords:
  market_cap_yi: ["市值"]
targets:
  short: {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
  mid:   {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
  long:  {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
anomalies: []
'''
    # invariants 区域不应被扫描到；正文里没有"市值 数字"组合
    body = '本报告分析公司业绩。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    # 期望 PASS：正文没有 keyword，derived 算式自洽（1000），但因正文未出现 keyword 别名 → 无比对
    assert result.returncode == 0, f"应 PASS（无正文出现），实际：\n{result.stdout}"


def test_cons_derived_no_duplicate_fails_for_overlapping_aliases():
    """B2 fix · 重叠别名（市值 ⊂ 总市值）不应产生重复 FAIL"""
    yaml_body = '''constants:
  price: 100
  shares: 10
derived:
  market_cap_yi: "price * shares"
keywords:
  market_cap_yi: ["市值", "总市值"]
targets:
  short: {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
  mid:   {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
  long:  {low: 10, high: 10, pe_low: 1, pe_high: 1, eps_var: shares}
anomalies: []
'''
    # 错误的市值，应该报 1 个 FAIL 而非 2 个
    body = '当前总市值 9999 亿元。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1
    # 只应有 1 个 CONS-derived FAIL（不重复）
    cons_count = result.stdout.count('CONS-derived')
    assert cons_count == 1, f"应只有 1 个 CONS-derived FAIL，实际 {cons_count} 个：\n{result.stdout}"


def test_cons_target_mult_passes():
    """UT-08 · targets.mid.low == pe_low * eps_var → PASS"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    # 22 * 5.00 = 110 ✓；25 * 5.00 = 125 ✓
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body))
    assert result.returncode == 0, result.stdout


def test_cons_target_mult_fails():
    """UT-09 · targets.long.low != pe_low * eps_var → FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
anomalies: []
'''
    # long.low=150 vs pe_low(22) * eps(5.00) = 110，不匹配 → FAIL
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body))
    assert result.returncode == 1
    assert 'CONS-target-mult' in result.stdout


def test_cons_anomaly_title_consistent():
    """UT-10 · ANO 标题中的数字 == invariants.anomalies[].value → PASS"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies:
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: pct}
'''
    body = '''### ANO-005 · 资产负债率 3 年累计上升 15.69 pct（HIGH）

- 上升幅度：15.69 pct
- 备注：又写一遍 15.7 pct 应该容差通过
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 0, result.stdout


def test_cons_anomaly_title_mismatch_fails():
    """UT-11 · ANO 标题与 invariants 不一致 → FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies:
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: pct}
'''
    body = '''### ANO-005 · 资产负债率 3 年累计上升 14.3 pct（HIGH）

- 实际上升幅度：15.69 pct
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1
    assert 'CONS-anomaly-title' in result.stdout
    assert 'ANO-005' in result.stdout


def test_cons_anomaly_title_ignores_unrelated_year_numbers():
    """B4 fix · 标题中的年份数字（"3 年"）不应被误抓为 anomaly value"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies:
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: pct}
'''
    # 标题里有"3 年"（年份数字）和"15.69 pct"（真正的 anomaly 值）
    # 错误的实现可能误抓 3.0 而 FAIL；正确实现应锁 pct 单位附近 → 15.69 → PASS
    body = '''### ANO-005 · 资产负债率 3 年累计上升 15.69 pct（HIGH）

- 上升幅度：15.69 pct
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 0, f"应 PASS（unit-anchored），实际：\n{result.stdout}"


def test_cons_anomaly_title_missing_unit_anchor_fails():
    """B4 fix · 标题缺少 unit 锚点 → FAIL（不再用 fallback heuristic）"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies:
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: pct}
'''
    # 标题里没有 "X pct" 模式 → 应该 FAIL（不应 fallback 匹配"3 年"附近的 3.0）
    body = '''### ANO-005 · 资产负债率累计上升（标题写错了，缺少数值和单位）

- 实际：15.69 pct
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1, f"应 FAIL，实际：\n{result.stdout}"
    assert 'CONS-anomaly-title' in result.stdout


def test_cons_anomaly_title_empty_unit():
    """B4 fix · unit 为空时（如比率 -0.11）匹配带小数点的数字"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies:
  - {id: ANO-003, severity: CRITICAL, indicator: 经现金流/营收, period: 2026Q1, value: -0.11, unit: ""}
'''
    body = '''### ANO-003 · 经现金流/营收 2026Q1 转负为 -0.11（首次）

- 数值：-0.11
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 0, f"应 PASS，实际：\n{result.stdout}"


def test_cons_baseline_eps_consistent():
    """UT-12 · 正文 "基准 EPS26" 附近数字 == invariants → PASS"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26", "本框架基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    body = '本框架基准 EPS26 = 5.00 元。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 0, result.stdout


def test_cons_baseline_eps_mismatch_fails():
    """UT-13 · 正文 "基准 EPS26" 附近数字与 invariants 不一致 → FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    body = '本框架基准 EPS26 = 5.50 元（实际应为 5.00）。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1
    assert 'CONS-baseline-eps' in result.stdout


def test_cons_baseline_eps_aliases():
    """UT-16 · keywords 列出多个别名，正文用其中任一别名都应触发检查"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026:
    - "基准 EPS26"
    - "本框架 EPS-2026"
    - "Baseline EPS 2026"
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    body = '本框架 EPS-2026 = 4.50（错值）。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1
    assert 'CONS-baseline-eps' in result.stdout


def _yaml_with_five_dim(fundamental, capital, technical, sentiment, catalyst, total, grade):
    return f'''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {{}}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {{low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}}
  mid:   {{low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}}
  long:  {{low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}}
anomalies: []
five_dim_score:
  fundamental: {fundamental}
  capital: {capital}
  technical: {technical}
  sentiment: {sentiment}
  catalyst: {catalyst}
  total: {total}
  grade: {grade}
'''


def test_cons_five_dim_sum_mismatch_fails():
    """UT-17 · 5 维分加和 != total → FAIL"""
    # 28+12+8+11+6 = 65，但写 total=70
    yaml_body = _yaml_with_five_dim(28, 12, 8, 11, 6, 70, 'B')
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body))
    assert result.returncode == 1
    assert 'CONS-score-consistency' in result.stdout


def test_cons_five_dim_grade_mismatch_fails():
    """UT-18 · grade=B 但 total=55（应为 C） → FAIL"""
    yaml_body = _yaml_with_five_dim(15, 10, 8, 11, 11, 55, 'B')
    # 15+10+8+11+11 = 55 ✓ sum OK，但 55 应 grade=C
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body))
    assert result.returncode == 1
    assert 'CONS-score-consistency' in result.stdout
    assert 'grade' in result.stdout.lower()


def test_cons_screening_19_count_mismatch_fails():
    """UT-19 · screening_19.passed=17 但正文写"通过 18 项" → FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
  screening_19_passed: ["通过项数", "通过"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
screening_19:
  passed: 17
  total: 19
  failed_items: [VAL-01, FUND-01]
'''
    # passed(17) + len(failed_items)(2) = 19 = total ✓ self-consistent
    # 但正文写"通过 18 项" → 关键词扫描应报 FAIL
    body = '19 项快速筛选清单：通过 18 项。'
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body) + body)
    assert result.returncode == 1


def test_cons_five_dim_omitted_skips_check():
    """UT-20 · invariants 不含 five_dim_score → 跳过该检查，0 FAIL"""
    yaml_body = '''constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.97
  baseline_eps_2026: 5.00
derived: {}
keywords:
  baseline_eps_2026: ["基准 EPS26"]
targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22, pe_high: 25, eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 30, pe_high: 36, eps_var: baseline_eps_2026}
anomalies: []
'''
    result = _run(INVARIANTS_HEAD.format(yaml_body=yaml_body))
    assert result.returncode == 0, result.stdout

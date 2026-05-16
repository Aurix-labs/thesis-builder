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

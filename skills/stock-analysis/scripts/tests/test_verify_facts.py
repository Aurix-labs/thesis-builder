"""测试 verify_facts.py 的标签解析"""
import subprocess
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verify_facts import extract_tags

SCRIPT = Path(__file__).parent.parent / 'verify_facts.py'
FIX = Path(__file__).parent / 'fixtures'

def test_extract_all_five_kinds():
    text = Path(__file__).parent / 'fixtures' / 'mini_report.md'
    tags = extract_tags(text.read_text())
    kinds = [t.kind for t in tags]
    assert 'F' in kinds and 'C' in kinds and 'I' in kinds and 'T' in kinds and 'GAP' in kinds

def test_tag_line_number():
    tags = extract_tags("line1\nL2 [F:foo.bar]\nL3 [I:reason]\n")
    assert tags[0].kind == 'F'
    assert tags[0].line_no == 2
    assert tags[1].line_no == 3

def test_payload_preserved():
    tags = extract_tags("¥162.5亿 [C:quote.price * 547887000]")
    assert tags[0].payload == 'quote.price * 547887000'


def test_resolve_path_simple():
    from verify_facts import resolve_path
    data = {"financials": {"2025": {"revenue": 15.89}}}
    assert resolve_path(data, "financials.2025.revenue") == 15.89

def test_resolve_path_array_index():
    from verify_facts import resolve_path
    data = {"kline_daily": [[1,2,3],[4,5,6],[7,8,9]]}
    assert resolve_path(data, "kline_daily[-1][2]") == 9

def test_f_tag_fail_when_value_mismatch(tmp_path):
    """[F:path] 数字与 data.json 不一致 → FAIL，退出码 1"""
    bad_report = tmp_path / 'report.md'
    bad_report.write_text("营收 99.99 亿 [F:financials.2025.revenue]\n")
    data = tmp_path / 'data.json'
    data.write_text(json.dumps({"financials": {"2025": {"revenue": 15.89}}}))

    res = subprocess.run(
        ['python', str(SCRIPT), '--report', str(bad_report), '--data', str(data)],
        capture_output=True, text=True,
    )
    assert res.returncode == 1
    assert 'FAIL' in res.stdout or 'FAIL' in res.stderr


def test_f_tag_pass_when_value_matches(tmp_path):
    good_report = tmp_path / 'report.md'
    good_report.write_text("营收 15.89 亿 [F:financials.2025.revenue]\n")
    data = tmp_path / 'data.json'
    data.write_text(json.dumps({"financials": {"2025": {"revenue": 15.89}}}))

    res = subprocess.run(
        ['python', str(SCRIPT), '--report', str(good_report), '--data', str(data)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0


def test_c_tag_evaluates_formula(tmp_path):
    rep = tmp_path / 'r.md'
    # 直接写 16250000000（不带"亿"），与脚本无归一化匹配
    rep.write_text("market_cap 16250000000 [C:quote.price * quote.total_shares]\n")
    data = tmp_path / 'd.json'
    data.write_text(json.dumps({"quote": {"price": 29.66, "total_shares": 5.479e8}}))
    res = subprocess.run(['python', str(SCRIPT), '--report', str(rep), '--data', str(data)],
                         capture_output=True, text=True)
    # 29.66 × 5.479e8 = 16,250,114,000；MD 标 16,250,000,000 → rel_diff ≈ 0.0007%，PASS
    assert res.returncode == 0, f"应 PASS\n{res.stdout}"


def test_i_tag_fails_when_reason_too_short(tmp_path):
    """[I:] reason 短于 4 字 → FAIL"""
    rep = tmp_path / 'r.md'
    rep.write_text("市占率 60% [I:推断]\n")
    data = tmp_path / 'd.json'
    data.write_text("{}")
    res = subprocess.run(['python', str(SCRIPT), '--report', str(rep), '--data', str(data)],
                         capture_output=True, text=True)
    assert res.returncode == 1


def test_t_tag_warns_without_failure_condition(tmp_path):
    """[T:] 200 字内无"失效条件" → WARN"""
    rep = tmp_path / 'r.md'
    rep.write_text("中期 40 [T:基准EPS×PE]\n（仅此一行）\n")
    data = tmp_path / 'd.json'
    data.write_text("{}")
    res = subprocess.run(['python', str(SCRIPT), '--report', str(rep), '--data', str(data)],
                         capture_output=True, text=True)
    assert res.returncode == 2  # WARN


def test_critical_anomaly_must_appear_in_step_0_5(tmp_path):
    rep = tmp_path / 'r.md'
    rep.write_text("# Report\n\n## Step 1\n...（没提归母净利润）\n")
    data = tmp_path / 'd.json'
    data.write_text("{}")
    anom = tmp_path / 'a.json'
    anom.write_text(json.dumps({"items": [{"id": "A001", "severity": "CRITICAL",
                                           "indicator": "归母净利润", "rule_id": "FIN-001"}]}))
    res = subprocess.run(['python', str(SCRIPT), '--report', str(rep), '--data', str(data),
                          '--anomalies', str(anom), '--mode', 'full'],
                         capture_output=True, text=True)
    assert res.returncode == 1
    assert "Step 0.5" in res.stdout or "Step 0.5" in res.stderr


def test_tag_re_supports_bracket_index():
    """UT-01 · TAG_RE should not truncate at [-1]"""
    tags = extract_tags("¥86.87 [F:blocks.fund_flow[-1].收盘价]")
    assert len(tags) == 1
    assert tags[0].kind == 'F'
    assert tags[0].payload == 'blocks.fund_flow[-1].收盘价'


def test_tag_re_supports_zero_and_positive_index():
    """UT-01b · [0] and [42] should also work"""
    tags = extract_tags("[F:rows[0].name] [F:items[42].val]")
    assert len(tags) == 2
    assert tags[0].payload == 'rows[0].name'
    assert tags[1].payload == 'items[42].val'


def test_formula_independent_minus():
    """UT-02 · Independent - in formula should be operator, not path"""
    from verify_facts import eval_formula
    data = {"a": 10, "b": 5}
    # 10 / 5 - 1 = 1.0
    result = eval_formula("a / b - 1", data)
    assert abs(result - 1.0) < 1e-9


def test_formula_independent_plus_minus_mix():
    """UT-02b · Mixed +/-/*/( ) should all work"""
    from verify_facts import eval_formula
    data = {"x": 100, "y": 25}
    # (100 - 25) * 2 / 25 = 6.0
    result = eval_formula("(x - y) * 2 / y", data)
    assert abs(result - 6.0) < 1e-9


def test_parse_payload_with_unit():
    """UT-03a · parse_payload splits path and |unit"""
    from verify_facts import parse_payload
    assert parse_payload("financials.营业总收入.20251231|亿") == \
        ("financials.营业总收入.20251231", "亿")
    assert parse_payload("financials.毛利率.20251231|%") == \
        ("financials.毛利率.20251231", "%")
    assert parse_payload("simple.path") == ("simple.path", None)


def test_unit_scales_constant():
    """UT-03b · UNIT_SCALES has 7 units"""
    from verify_facts import UNIT_SCALES
    assert UNIT_SCALES["亿"] == 1e8
    assert UNIT_SCALES["万"] == 1e4
    assert UNIT_SCALES["千"] == 1e3
    assert UNIT_SCALES["%"] == 1
    assert UNIT_SCALES["pct"] == 1
    assert UNIT_SCALES["倍"] == 1
    assert UNIT_SCALES["元"] == 1


def test_check_f_tag_with_unit_normalization():
    """UT-03c · [F:path|亿] should divide data by 1e8 before comparing"""
    from verify_facts import check_f_tag, Tag
    data = {"financials": {"营业总收入": {"20251231": 40528509770.23}}}
    tag = Tag(
        kind='F',
        payload='financials.营业总收入.20251231|亿',
        line_no=1,
        line='营收 405.29 亿 [F:financials.营业总收入.20251231|亿]',
        col=len('营收 405.29 亿 ')
    )
    assert check_f_tag(tag, data) is None  # PASS


def test_check_f_tag_unit_mismatch_fails():
    """UT-03d · Unit mismatch should FAIL with readable error"""
    from verify_facts import check_f_tag, Tag
    data = {"x": 40528509770.23}  # actually 405.29 亿
    tag = Tag(
        kind='F',
        payload='x|亿',
        line_no=1,
        line='错误数字 100 亿 [F:x|亿]',
        col=len('错误数字 100 亿 ')
    )
    result = check_f_tag(tag, data)
    assert result is not None
    assert result['kind'] == 'FAIL'

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

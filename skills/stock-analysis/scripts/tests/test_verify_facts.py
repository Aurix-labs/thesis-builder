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

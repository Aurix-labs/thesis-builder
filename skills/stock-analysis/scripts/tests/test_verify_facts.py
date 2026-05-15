"""测试 verify_facts.py 的标签解析"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verify_facts import extract_tags

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

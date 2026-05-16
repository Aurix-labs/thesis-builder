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


def test_missing_invariants_block_warns_not_fails():
    """UT-14 · 无 invariants 块的旧报告 → WARN，退出码 0"""
    result = _run("# 普通报告\n\n营收 100 亿 [F:foo]")
    assert result.returncode == 0
    assert 'WARN' in result.stdout
    assert 'invariants block' in result.stdout

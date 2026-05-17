"""测试 scan_anomalies.py：data.json → anomalies.json + .md"""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'
SCRIPT = Path(__file__).parent.parent / 'lib' / 'scan_anomalies.py'


def test_detects_critical_q1_drop(tmp_path):
    """2026Q1 归母净利同比 -91.7% 必须标记 CRITICAL FIN-001。"""
    data = tmp_path / 'data.json'
    data.write_text((FIXTURES / 'mini_data.json').read_text())
    out_json = tmp_path / 'anomalies.json'
    out_md = tmp_path / 'anomalies.md'

    subprocess.run(
        ['python3', str(SCRIPT), '--data', str(data),
         '--out-json', str(out_json), '--out-md', str(out_md)],
        check=True,
    )

    anoms = json.loads(out_json.read_text())['items']
    crit = [a for a in anoms if a['severity'] == 'CRITICAL']
    assert any(a['rule_id'] == 'FIN-001' and a['indicator'] == '归母净利润' for a in crit), \
        "CRITICAL 必须包含 FIN-001 归母净利润"


def test_anomalies_md_lists_critical_first(tmp_path):
    """anomalies.md 中 CRITICAL 必须排在最前。"""
    data = tmp_path / 'data.json'
    data.write_text((FIXTURES / 'mini_data.json').read_text())
    out_json = tmp_path / 'anomalies.json'
    out_md = tmp_path / 'anomalies.md'

    subprocess.run(
        ['python3', str(SCRIPT), '--data', str(data),
         '--out-json', str(out_json), '--out-md', str(out_md)],
        check=True,
    )
    md = out_md.read_text()
    idx_critical = md.find('## CRITICAL')
    idx_high = md.find('## HIGH')
    assert idx_critical > 0
    if idx_high > 0:
        assert idx_critical < idx_high

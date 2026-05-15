"""测试 verify_content.py：HTML/MD/JSON 三方校验"""
import json, subprocess
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / 'verify_content.py'
FIX = Path(__file__).parent / 'fixtures'


def test_hero_price_must_match_kline_last(tmp_path):
    html = FIX / 'mini_report.html'
    data = tmp_path / 'd.json'
    data.write_text(json.dumps({
        "meta": {"name": "x", "code": "x"},
        "kline_daily": [["2026-05-15", 30, 99.99, 29, 30, 1000]],
        "blocks": {"business": []},
    }))
    md = tmp_path / 'r.md'; md.write_text("")
    res = subprocess.run(['python', str(SCRIPT), '--html', str(html),
                          '--report', str(md), '--data', str(data)],
                         capture_output=True, text=True)
    assert res.returncode == 1
    assert "Latest" in res.stdout or "kline" in res.stdout


def test_hero_price_pass_when_matches(tmp_path):
    html = FIX / 'mini_report.html'
    data = tmp_path / 'd.json'
    data.write_text(json.dumps({
        "meta": {"name": "x", "code": "x"},
        "kline_daily": [["2026-05-15", 30.32, 29.66, 29.33, 30.56, 17889703]],
        "blocks": {"business": []},
    }))
    md = tmp_path / 'r.md'; md.write_text("")
    res = subprocess.run(['python', str(SCRIPT), '--html', str(html),
                          '--report', str(md), '--data', str(data)],
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stdout


def test_pie_data_must_match_blocks_business(tmp_path):
    """HTML 饼图 pieData 必须等于 data.json blocks.business 最新报告期按产品分类"""
    html = tmp_path / 'h.html'
    html.write_text('<script>const rawData = []; const pieData = [{"name":"X","value":50}];</script>')
    data = tmp_path / 'd.json'
    data.write_text(json.dumps({
        "meta": {"name": "x", "code": "x"},
        "kline_daily": [],
        "blocks": {"business": [
            {"报告日期": "2025-12-31", "分类类型": "按产品分类",
             "主营构成": "模锻件产品", "收入比例": 0.92}
        ]}
    }))
    md = tmp_path / 'r.md'; md.write_text("")
    res = subprocess.run(['python', str(SCRIPT), '--html', str(html),
                          '--report', str(md), '--data', str(data)],
                         capture_output=True, text=True)
    assert res.returncode == 1
    assert "pie" in res.stdout.lower() or "饼" in res.stdout

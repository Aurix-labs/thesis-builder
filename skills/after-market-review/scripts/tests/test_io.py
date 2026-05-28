from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.io import stock_output_dir, review_dir, write_json, has_existing_report


def test_review_dir_uses_after_market_review_segment(tmp_path):
    stock_dir = stock_output_dir(tmp_path, "比亚迪", "002594")
    out = review_dir(stock_dir, "2026-05-28")
    assert out == tmp_path / "比亚迪_002594" / "after-market-review" / "2026-05-28"


def test_write_json_preserves_chinese(tmp_path):
    p = tmp_path / "data.json"
    write_json(p, {"name": "比亚迪"})
    raw = p.read_text(encoding="utf-8")
    assert "比亚迪" in raw
    assert json.loads(raw)["name"] == "比亚迪"


def test_has_existing_report(tmp_path):
    d = tmp_path / "review"
    d.mkdir()
    assert has_existing_report(d) is False
    (d / "report.md").write_text("# ok\n", encoding="utf-8")
    assert has_existing_report(d) is True

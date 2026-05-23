"""集成测试：render_html.py 端到端 + 6 个 spec §7.3 用例。"""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pytest

from render_html import render, RenderError
from lib.md_renderer import split_report_sections


SKILL_ROOT = HERE.parent.parent  # skills/stock-analysis/
GOLDEN_INPUT = SKILL_ROOT / "examples" / "比亚迪_002594_input"


def _copy_golden_to_tmp(tmp_path: Path) -> Path:
    """复制金样本输入到 tmp，模拟 report/<ymd>/ 目录布局。"""
    dst = tmp_path / "比亚迪_002594" / "report" / "2026-05-15"
    dst.mkdir(parents=True)
    for name in ["data.json", "report.md", "bear-case.md", "fact-check.md"]:
        shutil.copy(GOLDEN_INPUT / name, dst / name)
    return dst


FIXED_META = {"session_id": "0x3F4A", "time_utc8": "14:32"}


def test_render_writes_html_file(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    assert html_path.exists()
    assert html_path.name == "report.html"
    html = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "比亚迪" in html
    assert "002594.SZ" in html


def test_render_contains_required_sections(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    html = html_path.read_text(encoding="utf-8")
    for sid in ["mission", "macro", "chain", "quality", "elasticity", "risk", "valuation", "compare", "tracking", "conclusion"]:
        assert f'id="{sid}"' in html, f"missing #{sid}"


def test_render_includes_mermaid_block_passthrough(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    html = html_path.read_text(encoding="utf-8")
    assert '<div class="mermaid">' in html
    assert "flowchart LR" in html
    assert "mermaid.initialize" in html
    assert "mermaid@10" in html


def test_render_score_seg_count(tmp_path):
    """6 dimensions × 5 = 30 score-seg。"""
    report_dir = _copy_golden_to_tmp(tmp_path)
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    html = html_path.read_text(encoding="utf-8")
    assert html.count('class="score-seg lit"') + html.count('class="score-seg dim"') == 30


def test_render_bear_case_present_when_file_exists(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    html = html_path.read_text(encoding="utf-8")
    assert 'id="bear-case"' in html
    assert html.count('href="#') >= 14


def test_render_bear_case_absent_drops_section(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    (report_dir / "bear-case.md").unlink()
    html_path = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)
    html = html_path.read_text(encoding="utf-8")
    assert 'id="bear-case"' not in html
    # 13 因为 nav 锚点也少 1 个（href="#bear-case"）
    assert html.count('href="#') == 13


def test_render_missing_required_field_raises(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    data = json.loads((report_dir / "data.json").read_text(encoding="utf-8"))
    del data["rubric"]["summary"]["total"]
    (report_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(RenderError, match="rubric.summary.total"):
        render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)


def test_render_missing_step_section_raises(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    md = (report_dir / "report.md").read_text(encoding="utf-8")
    # 切掉 Step 5
    import re
    md_no5 = re.sub(r"## Step 5 ·.*?(?=## Step 6 ·)", "", md, flags=re.DOTALL)
    (report_dir / "report.md").write_text(md_no5, encoding="utf-8")
    with pytest.raises(RenderError, match="Step 5"):
        render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META)


def test_render_dry_run_does_not_write(tmp_path):
    report_dir = _copy_golden_to_tmp(tmp_path)
    out = render(report_dir.parent.parent, "2026-05-15", fixed_meta=FIXED_META, dry_run=True)
    assert out is None
    assert not (report_dir / "report.html").exists()

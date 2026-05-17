"""测试 compose_report：合并 + 标的速写去重 + manifest 生成。"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from compose_report import compose, dedupe_thesis_snapshots
from lib.module_io import THESIS_SNAPSHOT_START, THESIS_SNAPSHOT_END, update_latest_symlink
from lib.config_loader import ANALYSIS_MODULES


def _write_module_report(tmp_path: Path, module: str, ymd: str, body: str):
    d = tmp_path / module / ymd
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.md").write_text(body, encoding="utf-8")
    update_latest_symlink(tmp_path / module, ymd)


def _make_snapshot(name: str) -> str:
    return f"{THESIS_SNAPSHOT_START}\n## {name} 标的速写\n{THESIS_SNAPSHOT_END}\n"


def test_dedupe_thesis_snapshots_keeps_first():
    md = (
        _make_snapshot("A")
        + "\n# Chain section\n"
        + _make_snapshot("B")
        + "\n# Rubric section\n"
        + _make_snapshot("C")
        + "\n# Elasticity section\n"
    )
    out = dedupe_thesis_snapshots(md)
    # 第一段保留、其余删除
    assert out.count(THESIS_SNAPSHOT_START) == 1
    assert "## A 标的速写" in out
    assert "## B 标的速写" not in out
    assert "## C 标的速写" not in out


def test_compose_writes_merged_report(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-05-17",
                              f"{_make_snapshot(m)}\n# {m} 主体\nbody of {m}\n")

    result = compose(stock_dir=tmp_path, today="2026-05-17")
    merged = Path(result["merged_report_md"])
    assert merged.exists()
    content = merged.read_text(encoding="utf-8")
    for m in ANALYSIS_MODULES:
        assert f"# {m} 主体" in content
        assert f"body of {m}" in content
    # 只剩一段速写
    assert content.count(THESIS_SNAPSHOT_START) == 1


def test_compose_writes_manifest(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-04-30",
                              f"# {m}\n")
    result = compose(stock_dir=tmp_path, today="2026-05-17")
    manifest_path = Path(result["merged_report_md"]).parent / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["today"] == "2026-05-17"
    assert manifest["modules"]["chain"]["ymd"] == "2026-04-30"
    assert manifest["modules"]["peers"]["ymd"] == "2026-04-30"


def test_compose_pending_list(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-05-17", _make_snapshot(m) + f"# {m}\n")
    result = compose(stock_dir=tmp_path, today="2026-05-17")
    assert result["pending"] == ["step_0_task_lock", "step_8_conclusion", "bear_case", "fact_check", "html"]


def test_compose_errors_on_missing_module(tmp_path):
    for m in ANALYSIS_MODULES[:-1]:  # 缺 peers
        _write_module_report(tmp_path, m, "2026-05-17", "# x\n")
    try:
        compose(stock_dir=tmp_path, today="2026-05-17")
        assert False, "应该抛错"
    except FileNotFoundError as e:
        assert "peers" in str(e)

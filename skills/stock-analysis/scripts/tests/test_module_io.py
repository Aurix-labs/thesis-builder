"""测试模块 I/O：data.json 读写、latest 软链管理、标的速写渲染。"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.module_io import (
    write_module_data,
    read_module_data,
    get_latest_ymd,
    update_latest_symlink,
    render_thesis_snapshot,
    THESIS_SNAPSHOT_START,
    THESIS_SNAPSHOT_END,
)


def test_write_module_data_creates_data_json(tmp_path):
    data = {"module": "chain", "ymd": "2026-05-17", "meta": {"name": "比亚迪"}}
    path = write_module_data(tmp_path, "chain", "2026-05-17", data)
    assert path == tmp_path / "chain" / "2026-05-17"
    assert (path / "data.json").exists()
    loaded = json.loads((path / "data.json").read_text(encoding="utf-8"))
    assert loaded == data


def test_write_module_data_updates_latest_symlink(tmp_path):
    write_module_data(tmp_path, "chain", "2026-05-17", {"module": "chain"})
    latest = tmp_path / "chain" / "latest"
    assert latest.is_symlink()
    assert latest.resolve() == (tmp_path / "chain" / "2026-05-17").resolve()


def test_write_module_data_overrides_latest_on_newer_ymd(tmp_path):
    write_module_data(tmp_path, "chain", "2026-02-10", {"module": "chain"})
    write_module_data(tmp_path, "chain", "2026-05-17", {"module": "chain"})
    latest = tmp_path / "chain" / "latest"
    assert latest.resolve() == (tmp_path / "chain" / "2026-05-17").resolve()


def test_read_module_data_by_ymd(tmp_path):
    write_module_data(tmp_path, "chain", "2026-05-17", {"a": 1})
    assert read_module_data(tmp_path, "chain", "2026-05-17") == {"a": 1}


def test_read_module_data_follows_latest_when_ymd_none(tmp_path):
    write_module_data(tmp_path, "chain", "2026-02-10", {"v": "old"})
    write_module_data(tmp_path, "chain", "2026-05-17", {"v": "new"})
    assert read_module_data(tmp_path, "chain") == {"v": "new"}


def test_get_latest_ymd_returns_target(tmp_path):
    write_module_data(tmp_path, "chain", "2026-05-17", {})
    assert get_latest_ymd(tmp_path, "chain") == "2026-05-17"


def test_get_latest_ymd_returns_none_when_missing(tmp_path):
    assert get_latest_ymd(tmp_path, "chain") is None


def test_update_latest_symlink_idempotent(tmp_path):
    module_dir = tmp_path / "chain"
    (module_dir / "2026-05-17").mkdir(parents=True)
    update_latest_symlink(module_dir, "2026-05-17")
    update_latest_symlink(module_dir, "2026-05-17")  # 重复调用不应报错
    assert (module_dir / "latest").resolve() == (module_dir / "2026-05-17").resolve()


def test_render_thesis_snapshot_includes_markers():
    meta = {"name": "比亚迪", "code": "002594", "industry": "汽车整车"}
    quote = {"price": 280.5, "market_cap": 7800e8, "pe": 32.4, "pb": 4.8}
    out = render_thesis_snapshot(meta, quote, core_thesis="新能源车出海 vs 国内价格战")
    assert THESIS_SNAPSHOT_START in out
    assert THESIS_SNAPSHOT_END in out
    assert "比亚迪" in out
    assert "002594" in out
    assert "汽车整车" in out
    assert "280.5" in out
    assert "32.4" in out
    assert "新能源车出海" in out


def test_render_thesis_snapshot_empty_thesis_still_valid():
    meta = {"name": "X", "code": "000001", "industry": "Y"}
    quote = {"price": 10, "market_cap": 1e9, "pe": 20, "pb": 2}
    out = render_thesis_snapshot(meta, quote)
    assert THESIS_SNAPSHOT_START in out
    assert THESIS_SNAPSHOT_END in out

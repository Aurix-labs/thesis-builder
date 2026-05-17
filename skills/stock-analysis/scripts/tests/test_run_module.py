"""测试 run_module.py 入口。"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from run_module import expand_modules, process_one, parse_args
from lib.config_loader import load_config


def test_expand_modules_report_expands_to_seven():
    cfg = load_config()
    out = expand_modules(["report"], cfg)
    assert out == ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]


def test_expand_modules_dedup():
    cfg = load_config()
    out = expand_modules(["chain", "产业链", "valuation"], cfg)
    assert out == ["chain", "valuation"]


def test_expand_modules_preserves_user_order():
    cfg = load_config()
    out = expand_modules(["valuation", "chain"], cfg)
    assert out == ["valuation", "chain"]


def test_expand_modules_report_with_extras_dedup():
    cfg = load_config()
    out = expand_modules(["valuation", "report"], cfg)
    # valuation 已在 report 展开里出现，去重后保留首位
    assert out[0] == "valuation"
    assert "chain" in out
    assert len([m for m in out if m == "valuation"]) == 1


def test_process_one_returns_reuse_when_ttl_hit(tmp_path):
    """模拟 latest 软链已存在且在 TTL 内时，应返回 reuse。"""
    from lib.module_io import update_latest_symlink
    (tmp_path / "valuation" / "2026-05-17").mkdir(parents=True)
    update_latest_symlink(tmp_path / "valuation", "2026-05-17")

    cfg = load_config()
    result = process_one(
        code="002594", name="比亚迪",
        stock_dir=tmp_path, module="valuation",
        today="2026-05-17", force=False, config=cfg,
        fetch_dispatcher=lambda *a, **k: pytest_fail_if_called(),
    )
    assert result["status"] == "reuse"
    assert result["module"] == "valuation"
    assert result["ymd"] == "2026-05-17"


def pytest_fail_if_called(*args, **kwargs):
    raise AssertionError("不应该调用 fetch_dispatcher（命中 TTL）")


def test_process_one_force_overrides_ttl(tmp_path):
    """传 force=True 时即使 TTL 命中也应重新拉。"""
    from lib.module_io import update_latest_symlink
    (tmp_path / "valuation" / "2026-05-17").mkdir(parents=True)
    update_latest_symlink(tmp_path / "valuation", "2026-05-17")

    called = []
    def dispatcher(module, code, name, stock_dir, today):
        called.append(module)
        (stock_dir / module / today).mkdir(parents=True, exist_ok=True)
        update_latest_symlink(stock_dir / module, today)
        return {"module": module}

    cfg = load_config()
    result = process_one(
        code="002594", name="比亚迪",
        stock_dir=tmp_path, module="valuation",
        today="2026-05-17", force=True, config=cfg,
        fetch_dispatcher=dispatcher,
    )
    assert called == ["valuation"]
    assert result["status"] == "data_ready"
    assert result["needs_report_md"] is True


def test_parse_args_basic():
    args = parse_args(["002594", "valuation"])
    assert args.code_or_name == "002594"
    assert args.modules == ["valuation"]
    assert args.force is False


def test_parse_args_multiple_modules_and_force():
    args = parse_args(["002594", "valuation", "flow-tech", "--force"])
    assert args.modules == ["valuation", "flow-tech"]
    assert args.force is True


def test_parse_args_default_module_is_report():
    args = parse_args(["002594"])
    assert args.modules == ["report"]

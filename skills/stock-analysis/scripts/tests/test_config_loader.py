"""测试 config.yaml 加载 + 别名归一化。"""
from pathlib import Path
import pytest
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.config_loader import (
    load_config,
    build_alias_map,
    resolve_module_name,
    get_ttl,
    ANALYSIS_MODULES,
)


def test_analysis_modules_constant():
    assert ANALYSIS_MODULES == [
        "chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers",
    ]


def test_load_config_default_path():
    cfg = load_config()
    assert "modules" in cfg
    assert "defaults" in cfg
    for m in ANALYSIS_MODULES:
        assert m in cfg["modules"]
    assert "report" in cfg["modules"]


def test_load_config_explicit_path(tmp_path):
    yml = tmp_path / "c.yaml"
    yml.write_text("modules:\n  chain:\n    ttl_days: 7\n    aliases: [产业链]\ndefaults:\n  default_module: chain\n", encoding="utf-8")
    cfg = load_config(yml)
    assert cfg["modules"]["chain"]["ttl_days"] == 7


def test_build_alias_map_covers_zh_en():
    cfg = load_config()
    amap = build_alias_map(cfg)
    assert amap["chain"] == "chain"
    assert amap["产业链"] == "chain"
    assert amap["industry"] == "chain"
    assert amap["估值"] == "valuation"
    assert amap["target"] == "valuation"
    assert amap["报告"] == "report"
    assert amap["all"] == "report"


def test_resolve_module_name_canonical():
    cfg = load_config()
    amap = build_alias_map(cfg)
    assert resolve_module_name("chain", amap) == "chain"
    assert resolve_module_name("产业链", amap) == "chain"
    assert resolve_module_name("CHAIN", amap) == "chain"
    assert resolve_module_name("估值", amap) == "valuation"


def test_resolve_module_name_unknown_raises():
    cfg = load_config()
    amap = build_alias_map(cfg)
    with pytest.raises(ValueError):
        resolve_module_name("不存在的模块", amap)


def test_get_ttl_returns_int_for_analysis_modules():
    cfg = load_config()
    assert get_ttl("chain", cfg) == 90
    assert get_ttl("flow-tech", cfg) == 1
    assert get_ttl("valuation", cfg) == 7


def test_get_ttl_returns_none_for_report():
    cfg = load_config()
    assert get_ttl("report", cfg) is None

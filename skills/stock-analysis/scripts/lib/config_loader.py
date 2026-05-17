"""config.yaml 加载 + 模块别名归一化。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ANALYSIS_MODULES = ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """加载 config.yaml。path=None 时使用 skill 内置默认。"""
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_alias_map(config: dict) -> dict[str, str]:
    """构造 {alias_lower: canonical_name} 映射，包含主名自身。"""
    amap: dict[str, str] = {}
    for canon, body in config.get("modules", {}).items():
        amap[canon.lower()] = canon
        for alias in body.get("aliases", []) or []:
            amap[str(alias).lower()] = canon
    return amap


def resolve_module_name(name_or_alias: str, alias_map: dict[str, str]) -> str:
    """归一化为主名。未知抛 ValueError。"""
    key = str(name_or_alias).strip().lower()
    if key not in alias_map:
        raise ValueError(f"未知模块名或别名：{name_or_alias!r}")
    return alias_map[key]


def get_ttl(module: str, config: dict) -> int | None:
    """返回模块的 ttl_days。report 模块无 TTL 返回 None。"""
    body = config.get("modules", {}).get(module, {})
    return body.get("ttl_days")

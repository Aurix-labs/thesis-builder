"""config.yaml 加载 + 模块别名归一化。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REVIEW_MODULES = ["index", "sentiment", "mainline", "capital", "variables", "combatmap"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_alias_map(config: dict) -> dict[str, str]:
    amap: dict[str, str] = {}
    for canon, body in config.get("modules", {}).items():
        amap[canon.lower()] = canon
        for alias in body.get("aliases", []) or []:
            amap[str(alias).lower()] = canon
    return amap


def resolve_module_name(name_or_alias: str, alias_map: dict[str, str]) -> str:
    key = str(name_or_alias).strip().lower()
    if key not in alias_map:
        raise ValueError(f"未知模块名或别名：{name_or_alias!r}")
    return alias_map[key]


def get_ttl(module: str, config: dict) -> int | None:
    body = config.get("modules", {}).get(module, {})
    return body.get("ttl_days")

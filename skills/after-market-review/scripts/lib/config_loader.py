from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    large = cfg.get("large_order", {})
    amount_min = large.get("amount_min")
    top_quantile = large.get("top_quantile")
    window_minutes = large.get("window_minutes")
    if not isinstance(amount_min, (int, float)) or amount_min <= 0:
        raise ValueError("large_order.amount_min must be positive")
    if not isinstance(top_quantile, (int, float)) or not 0 < float(top_quantile) < 1:
        raise ValueError("large_order.top_quantile must be between 0 and 1")
    if not isinstance(window_minutes, int) or window_minutes <= 0:
        raise ValueError("large_order.window_minutes must be a positive integer")

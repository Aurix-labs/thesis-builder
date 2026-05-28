from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.config_loader import load_config, validate_config


def test_load_config_has_large_order_defaults():
    cfg = load_config()
    assert cfg["large_order"]["amount_min"] == 1_000_000
    assert cfg["large_order"]["top_quantile"] == 0.95
    assert cfg["large_order"]["window_minutes"] == 10


def test_validate_config_rejects_bad_quantile():
    cfg = load_config()
    cfg["large_order"]["top_quantile"] = 1.4
    try:
        validate_config(cfg)
    except ValueError as exc:
        assert "top_quantile" in str(exc)
    else:
        raise AssertionError("validate_config should reject top_quantile > 1")

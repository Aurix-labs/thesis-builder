from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_tick_trade import analyze_tick_rows


def test_large_order_uses_amount_min_or_top_quantile():
    rows = [
        {"ticktime": "09:30:01", "price": 10.0, "volume": 10_000, "kind": "U"},
        {"ticktime": "09:31:01", "price": 10.1, "volume": 200_000, "kind": "U"},
        {"ticktime": "09:32:01", "price": 10.0, "volume": 30_000, "kind": "D"},
        {"ticktime": "09:33:01", "price": 10.2, "volume": 40_000, "kind": "U"},
    ]
    cfg = {"amount_min": 1_000_000, "top_quantile": 0.75, "window_minutes": 10, "include_call_auction": True}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_count"] == 2
    assert out["summary"]["large_sell_count"] == 0
    assert out["summary"]["large_buy_amount"] == 2_428_000
    assert out["summary"]["net_large_amount"] == 2_428_000


def test_tail_behavior_detects_tail_buying():
    rows = [
        {"ticktime": "14:51:00", "price": 9.9, "volume": 200_000, "kind": "U"},
        {"ticktime": "14:55:00", "price": 10.0, "volume": 220_000, "kind": "U"},
        {"ticktime": "14:56:00", "price": 10.0, "volume": 20_000, "kind": "D"},
    ]
    cfg = {"amount_min": 500_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": True}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["tail_behavior"] == "尾盘大单净买入"


def test_include_call_auction_false_filters_early_rows():
    rows = [
        {"ticktime": "09:25:00", "price": 10.0, "volume": 500_000, "kind": "U"},
        {"ticktime": "09:31:00", "price": 10.0, "volume": 20_000, "kind": "D"},
    ]
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": False}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_count"] == 0
    assert out["summary"]["large_sell_count"] == 1

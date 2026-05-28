from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_tick_trade import analyze_tick_rows, fetch


def test_large_order_uses_amount_min_or_top_quantile():
    rows = [
        {"ticktime": "09:30:01", "price": 10.0, "volume": 10_000, "kind": "U"},
        {"ticktime": "09:31:01", "price": 10.1, "volume": 200_000, "kind": "U"},
        {"ticktime": "09:32:01", "price": 10.0, "volume": 30_000, "kind": "D"},
        {"ticktime": "09:33:01", "price": 10.2, "volume": 40_000, "kind": "U"},
    ]
    cfg = {"amount_min": 400_000, "top_quantile": 0.75, "window_minutes": 10, "include_call_auction": True}
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


def test_top_quantile_selects_only_top_five_percent_row():
    rows = [
        {"ticktime": f"09:30:{i:02d}", "price": 1.0, "volume": i + 1, "kind": "U"}
        for i in range(20)
    ]
    cfg = {
        "amount_min": 1_000_000,
        "top_quantile": 0.95,
        "window_minutes": 10,
        "include_call_auction": True,
    }
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_count"] == 1
    assert out["summary"]["large_buy_amount"] == 20


def test_include_call_auction_false_filters_closing_auction_rows():
    rows = [
        {"ticktime": "14:56:00", "price": 10.0, "volume": 20_000, "kind": "U"},
        {"ticktime": "14:58:00", "price": 10.0, "volume": 500_000, "kind": "U"},
    ]
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": False}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_count"] == 1
    assert out["summary"]["large_buy_amount"] == 200_000


def test_empty_row_summary_has_required_fields():
    out = analyze_tick_rows([], {"include_call_auction": True})
    assert set(out["summary"]) == {
        "large_buy_count",
        "large_sell_count",
        "large_buy_amount",
        "large_sell_amount",
        "net_large_amount",
        "peak_buy_windows",
        "peak_sell_windows",
        "tail_behavior",
    }


def test_neutral_side_does_not_count_as_buy_or_sell():
    rows = [{"ticktime": "09:31:00", "price": 10.0, "volume": 500_000, "kind": "M"}]
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": True}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_count"] == 0
    assert out["summary"]["large_sell_count"] == 0
    assert out["summary"]["net_large_amount"] == 0


def test_chinese_volume_amount_conversion_multiplies_by_one_hundred():
    rows = [{"ticktime": "09:31:00", "成交价": 10.0, "成交量": 200, "性质": "买盘"}]
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": True}
    out = analyze_tick_rows(rows, cfg)
    assert out["summary"]["large_buy_amount"] == 200_000


class FakeAkshareNoRows:
    def __init__(self):
        self.tencent_called = False

    def stock_intraday_sina(self, *, symbol, date):
        return []

    def stock_zh_a_tick_tx_js(self, *, symbol):
        self.tencent_called = True
        return [{"ticktime": "09:31:00", "price": 10.0, "volume": 20_000, "kind": "U"}]


def test_fetch_does_not_call_latest_fallback_by_default():
    fake = FakeAkshareNoRows()
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": True}
    out = fetch("000001", "2026-05-28", cfg, akshare_module=fake)
    assert out["status"] == "unavailable"
    assert fake.tencent_called is False
    assert "latest-only fallback disabled" in out["errors"][-1]


def test_fetch_calls_latest_fallback_when_allowed():
    fake = FakeAkshareNoRows()
    cfg = {"amount_min": 100_000, "top_quantile": 0.95, "window_minutes": 10, "include_call_auction": True}
    out = fetch(
        "000001",
        "2026-05-28",
        cfg,
        akshare_module=fake,
        allow_latest_fallback=True,
    )
    assert out["status"] == "ok"
    assert fake.tencent_called is True
    assert out["data"]["summary"]["large_buy_count"] == 1

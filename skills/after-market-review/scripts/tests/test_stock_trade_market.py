from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_market import fetch as fetch_market
from fetch_stock_trade import _intraday_pattern, fetch as fetch_stock_trade


class FakeStockAkshare:
    def stock_zh_a_hist(self, *, symbol, period, start_date, end_date, adjust):
        assert symbol == "002594"
        assert period == "daily"
        assert adjust == "qfq"
        assert start_date < end_date
        return [
            {
                "日期": "2026-05-27",
                "开盘": "99",
                "最高": "101",
                "最低": "98",
                "收盘": "100",
                "成交量": "1000",
                "成交额": "100000",
                "换手率": "1.2",
            },
            {
                "日期": "2026-05-28",
                "开盘": "100",
                "最高": "112",
                "最低": "96",
                "收盘": "110",
                "成交量": "2000",
                "成交额": "220000",
                "换手率": "2.3",
            },
        ]

    def stock_zh_a_hist_min_em(self, *, symbol, start_date, end_date, period, adjust):
        assert symbol == "002594"
        assert start_date == "2026-05-28 09:30:00"
        assert end_date == "2026-05-28 15:00:00"
        assert period == "1"
        assert adjust == ""
        return [
            {"时间": "2026-05-28 09:30:00", "收盘": "100"},
            {"时间": "2026-05-28 10:30:00", "收盘": "98"},
            {"时间": "2026-05-28 13:30:00", "收盘": "99"},
            {"时间": "2026-05-28 15:00:00", "收盘": "105"},
        ]


class FakeStockAkshareNoDaily:
    def stock_zh_a_hist(self, **kwargs):
        return []


def test_stock_trade_fetch_returns_daily_and_intraday_facts():
    out = fetch_stock_trade("002594", "2026-05-28", akshare_module=FakeStockAkshare())

    assert out["status"] == "ok"
    assert out["errors"] == []
    assert out["data"]["trade_date"] == "2026-05-28"
    assert out["data"]["daily"]["close"] == 110
    assert out["data"]["daily"]["prev_close"] == 100
    assert out["data"]["daily"]["change_pct"] == 10
    assert out["data"]["daily"]["turnover"] == 2.3
    assert len(out["data"]["recent_daily"]) == 2
    assert len(out["data"]["minute_rows"]) == 4
    assert out["data"]["intraday_pattern"] == "盘中回落后修复"


def test_stock_trade_empty_daily_is_error():
    out = fetch_stock_trade("002594", "2026-05-28", akshare_module=FakeStockAkshareNoDaily())

    assert out["status"] == "error"
    assert out["data"] == {}
    assert out["errors"] == ["stock_zh_a_hist returned no rows"]


def test_intraday_pattern_detects_basic_shapes():
    assert _intraday_pattern(
        [{"close": 10}, {"close": 11}, {"close": 12}, {"close": 13}]
    ) == "震荡上行"
    assert _intraday_pattern(
        [{"close": 10}, {"close": 9}, {"close": 8}, {"close": 7}]
    ) == "震荡下行"
    assert _intraday_pattern([{"close": 10}, {"close": 10}, {"close": 10}]) == "分钟线不足"


class FakeMarketAkshare:
    def stock_zh_index_daily_em(self, *, symbol, start_date, end_date):
        if symbol == "sz399001":
            raise RuntimeError("temporary outage")
        return [
            {"date": "2026-05-27", "close": "3000", "amount": "100000", "volume": "1000"},
            {"date": "2026-05-28", "close": "3060", "amount": "120000", "volume": "1200"},
            {"date": "2026-05-29", "close": "9999", "amount": "999999", "volume": "9999"},
        ]


def test_market_fetch_is_partial_when_one_index_fails():
    cfg = {
        "market_indices": [
            {"code": "sh000001", "name": "上证指数"},
            {"code": "sz399001", "name": "深证成指"},
        ]
    }

    out = fetch_market("2026-05-28", cfg, akshare_module=FakeMarketAkshare())

    assert out["status"] == "partial"
    assert out["errors"] == ["sz399001 failed: temporary outage"]
    assert out["data"]["indices"] == [
        {
            "code": "sh000001",
            "name": "上证指数",
            "date": "2026-05-28",
            "close": 3060,
            "change_pct": 2,
            "amount": 120000,
            "volume": 1200,
        }
    ]

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_events import fetch as fetch_events
from fetch_funds import fetch as fetch_funds
from fetch_sector import fetch as fetch_sector
from fetch_sentiment import fetch as fetch_sentiment


class FakeSectorAkshare:
    def stock_individual_info_em(self, *, symbol):
        assert symbol == "002594"
        return [
            {"item": "股票简称", "value": "比亚迪"},
            {"item": "所属行业", "value": "汽车整车"},
        ]

    def stock_board_industry_name_em(self):
        return [
            {"板块名称": "电池", "涨跌幅": 1.1},
            {"板块名称": "汽车整车", "涨跌幅": 2.5},
        ]


class FakeSectorAkshareInfoFails(FakeSectorAkshare):
    def stock_individual_info_em(self, *, symbol):
        raise RuntimeError("info outage")


def test_sector_fetch_is_partial_with_industry_and_board_rank():
    out = fetch_sector("002594", "比亚迪", "2026-05-28", akshare_module=FakeSectorAkshare())

    assert out["status"] == "partial"
    assert out["errors"] == []
    assert out["data"]["industry"] == "汽车整车"
    assert out["data"]["industry_rank"]["rank"] == 1
    assert out["data"]["industry_rank"]["row"]["板块名称"] == "汽车整车"


def test_sector_fetch_degrades_to_unavailable_and_keeps_errors():
    out = fetch_sector(
        "002594",
        "比亚迪",
        "2026-05-28",
        akshare_module=FakeSectorAkshareInfoFails(),
    )

    assert out["status"] == "unavailable"
    assert out["data"]["industry"] is None
    assert out["data"]["industry_rank"] is None
    assert out["errors"] == ["stock_individual_info_em failed: info outage"]


class FakeFundsAkshare:
    def stock_individual_fund_flow(self, *, stock, market):
        assert stock == "600519"
        assert market == "sh"
        return [{"日期": "2026-05-28", "主力净流入": "1000"}]

    def stock_margin_detail_sse(self, *, date):
        assert date == "20260528"
        return [
            {"标的证券代码": "600519", "融资余额": "2000"},
            {"标的证券代码": "600000", "融资余额": "1"},
        ]


class FakeFundsAkshareAllFail:
    def stock_individual_fund_flow(self, *, stock, market):
        raise RuntimeError("flow outage")

    def stock_margin_detail_szse(self, *, date):
        raise RuntimeError("margin outage")


def test_funds_fetch_is_partial_when_flow_or_margin_exists():
    out = fetch_funds("600519", "2026-05-28", akshare_module=FakeFundsAkshare())

    assert out["status"] == "partial"
    assert out["errors"] == []
    assert out["data"]["market"] == "sh"
    assert out["data"]["fund_flow"] == [{"日期": "2026-05-28", "主力净流入": "1000"}]
    assert out["data"]["margin"] == [{"标的证券代码": "600519", "融资余额": "2000"}]


def test_funds_fetch_is_unavailable_when_optional_sources_fail():
    out = fetch_funds("000001", "2026-05-28", akshare_module=FakeFundsAkshareAllFail())

    assert out["status"] == "unavailable"
    assert out["data"]["market"] == "sz"
    assert out["data"]["fund_flow"] == []
    assert out["data"]["margin"] == []
    assert out["errors"] == [
        "stock_individual_fund_flow failed: flow outage",
        "stock_margin_detail_szse failed: margin outage",
    ]


class FakeEventsAkshare:
    def stock_news_em(self, *, symbol):
        assert symbol == "002594"
        return [
            {"发布时间": "2026-05-27 18:00:00", "新闻标题": "前日新闻"},
            {"发布时间": "2026-05-28 14:59:00", "新闻标题": "盘中新闻"},
            {"发布时间": "2026-05-28 15:01:00", "新闻标题": "盘后新闻"},
            {"发布时间": "2026-05-29 09:00:00", "新闻标题": "未来新闻"},
            {"发布时间": "", "新闻标题": "无日期新闻"},
            {"新闻标题": "缺日期新闻"},
        ]


class FakeEventsAkshareFails:
    def stock_news_em(self, *, symbol):
        raise RuntimeError("news outage")


def test_events_fetch_filters_news_by_trade_date_and_caps_catalysts():
    out = fetch_events(
        "002594",
        "比亚迪",
        "2026-05-28",
        {"sources": {"enable_web_news": True}},
        akshare_module=FakeEventsAkshare(),
    )

    assert out["status"] == "ok"
    assert out["errors"] == []
    assert [row["新闻标题"] for row in out["data"]["raw_news"]] == ["前日新闻", "盘中新闻"]
    assert out["data"]["possible_catalyst"] == [
        {"发布时间": "2026-05-27 18:00:00", "新闻标题": "前日新闻"},
        {"发布时间": "2026-05-28 14:59:00", "新闻标题": "盘中新闻"},
    ]
    assert out["data"]["verified_driver"] == []
    assert out["data"]["unsupported_rumor"] == []


def test_events_fetch_unavailable_when_news_source_fails():
    out = fetch_events(
        "002594",
        "比亚迪",
        "2026-05-28",
        {"sources": {"enable_web_news": True}},
        akshare_module=FakeEventsAkshareFails(),
    )

    assert out["status"] == "unavailable"
    assert out["data"]["raw_news"] == []
    assert out["errors"] == ["stock_news_em failed: news outage"]


class FakeSentimentAkshare:
    def stock_hot_rank_em(self):
        return [{"代码": "002594", "排名": 3}, {"代码": "000001", "排名": 4}]

    def stock_hot_keyword_em(self, *, symbol):
        assert symbol == "SZ002594"
        return [{"关键词": "新能源"}]

    def stock_lhb_detail_daily_sina(self, *, date):
        assert date == "20260528"
        return [{"股票代码": "002594", "营业部": "机构专用"}, {"股票代码": "000001", "营业部": "其他"}]


class FakeSentimentAkshareFails:
    def stock_hot_rank_em(self):
        raise RuntimeError("rank outage")

    def stock_hot_keyword_em(self, *, symbol):
        raise RuntimeError("keyword outage")

    def stock_lhb_detail_daily_sina(self, *, date):
        raise RuntimeError("lhb outage")


def test_sentiment_fetch_respects_toggles_and_filters_by_code():
    out = fetch_sentiment(
        "002594",
        "2026-05-28",
        {"sources": {"enable_sentiment": True, "enable_lhb": True}},
        akshare_module=FakeSentimentAkshare(),
    )

    assert out["status"] == "partial"
    assert out["errors"] == []
    assert out["data"]["hot_rank"] == [{"代码": "002594", "排名": 3}]
    assert out["data"]["hot_keywords"] == [{"关键词": "新能源"}]
    assert out["data"]["lhb"] == [{"股票代码": "002594", "营业部": "机构专用"}]


class FakeSentimentShanghaiAkshare:
    def stock_hot_rank_em(self):
        return []

    def stock_hot_keyword_em(self, *, symbol):
        assert symbol == "SH600519"
        return [{"关键词": "白酒"}]


def test_sentiment_fetch_uses_shanghai_prefixed_keyword_symbol():
    out = fetch_sentiment(
        "600519",
        "2026-05-28",
        {"sources": {"enable_sentiment": True, "enable_lhb": False}},
        akshare_module=FakeSentimentShanghaiAkshare(),
    )

    assert out["status"] == "partial"
    assert out["errors"] == []
    assert out["data"]["hot_keywords"] == [{"关键词": "白酒"}]


def test_sentiment_fetch_unavailable_when_disabled_without_errors():
    out = fetch_sentiment(
        "002594",
        "2026-05-28",
        {"sources": {"enable_sentiment": False, "enable_lhb": False}},
        akshare_module=FakeSentimentAkshareFails(),
    )

    assert out["status"] == "unavailable"
    assert out["data"] == {"hot_rank": [], "hot_keywords": [], "lhb": []}
    assert out["errors"] == []

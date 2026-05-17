"""测试 fetch_risk + anomalies.md 生成。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_risk import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪"}, {"item": "行业", "value": "汽车整车"}]
    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]
    def stock_financial_abstract(self, symbol):
        return [{"指标": "营业收入", "20250331": 1500, "20240331": 1200}]
    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        return [{"日期": "2026-05-15", "开盘": 280, "收盘": 280.5, "最高": 282, "最低": 278, "成交量": 1e7}]
    def stock_notice_report(self, symbol, date):
        return [{"代码": "002594", "公告标题": "关于股东减持的公告"}]
    def stock_news_em(self, symbol):
        return [{"标题": "比亚迪汉 EV", "发布时间": "2026-05-15"}]


def test_module_name():
    assert MODULE_NAME == "risk"


def test_fetch_writes_data_and_anomalies(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk())
    for k in ("meta", "quote", "financial_abstract", "kline_daily", "notice", "news"):
        assert k in data
    out_dir = tmp_path / "risk" / "2026-05-17"
    assert (out_dir / "data.json").exists()
    assert (out_dir / "anomalies.md").exists()
    assert (out_dir / "anomalies.json").exists()

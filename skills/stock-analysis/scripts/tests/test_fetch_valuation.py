"""测试 fetch_valuation。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_valuation import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪"}, {"item": "行业", "value": "汽车整车"}]
    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]
    def stock_financial_abstract(self, symbol):
        return [{"指标": "营业收入", "20250331": 1500}]
    def stock_research_report_em(self, symbol):
        return [{"机构": "国泰君安", "目标价": "320", "日期": "2026-05-10"}]
    def stock_institute_recommend(self, symbol):
        return [{"代码": "002594", "推荐评级": "买入"}]
    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        return [{"日期": "2026-05-15", "收盘": 280.5}]


def test_module_name():
    assert MODULE_NAME == "valuation"


def test_fetch_writes_data(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk())
    for k in ("meta", "quote", "financial_abstract", "research", "recommend", "kline_daily"):
        assert k in data
    assert (tmp_path / "valuation" / "2026-05-17" / "data.json").exists()

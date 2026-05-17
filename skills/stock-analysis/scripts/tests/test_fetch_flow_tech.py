"""测试 fetch_flow_tech。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_flow_tech import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪"}, {"item": "行业", "value": "汽车整车"}]
    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]
    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        return [{"日期": "2026-05-15", "开盘": 280, "收盘": 280.5, "最高": 282, "最低": 278, "成交量": 1e7}]
    def stock_gdfx_top_10_em(self, symbol, date=None):
        return [{"股东名称": "比亚迪集团", "持股比例": "29.5%"}]
    def stock_individual_fund_flow(self, stock, market):
        return [{"日期": "2026-05-15", "主力净流入": 2e8}]
    def stock_margin_detail_szse(self, date=None):
        return [{"代码": "002594", "融资余额": 12.5e8}]
    def stock_margin_detail_sse(self, date=None):
        return []


def test_module_name():
    assert MODULE_NAME == "flow-tech"


def test_fetch_writes_data(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk())
    for k in ("meta", "quote", "kline_daily", "top_holders", "fund_flow", "margin"):
        assert k in data
    assert (tmp_path / "flow-tech" / "2026-05-17" / "data.json").exists()
    assert len(data["kline_daily"]) > 0

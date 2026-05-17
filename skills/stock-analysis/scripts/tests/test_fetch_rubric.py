"""测试 fetch_rubric。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_rubric import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪"}, {"item": "行业", "value": "汽车整车"}]

    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]

    def stock_financial_abstract(self, symbol):
        return [{"指标": "营业收入", "20250331": 1500, "20240331": 1200}]

    def stock_gdfx_top_10_em(self, symbol, date=None):
        return [{"股东名称": "比亚迪集团", "持股数量": "29亿", "持股比例": "29.5%"}]

    def stock_margin_detail_sse(self, date=None):
        return []
    def stock_margin_detail_szse(self, date=None):
        return [{"代码": "002594", "融资余额": 12.5e8}]


def test_module_name():
    assert MODULE_NAME == "rubric"


def test_fetch_writes_data_with_required_fields(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk())
    for k in ("meta", "quote", "financial_abstract", "top_holders", "margin"):
        assert k in data, f"missing field {k}"
    assert (tmp_path / "rubric" / "2026-05-17" / "data.json").exists()
    assert (tmp_path / "rubric" / "latest").resolve() == (tmp_path / "rubric" / "2026-05-17").resolve()

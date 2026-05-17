"""测试 fetch_elasticity。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_elasticity import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪"}, {"item": "行业", "value": "汽车整车"}]
    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]
    def stock_financial_abstract(self, symbol):
        return [{"指标": "营业收入", "20250331": 1500}]
    def stock_zygc_em(self, symbol):
        return [{"分类": "新能源汽车", "营收占比": "78%"}]


def test_module_name():
    assert MODULE_NAME == "elasticity"


def test_fetch_writes_data(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk())
    for k in ("meta", "quote", "financial_abstract", "business_segments"):
        assert k in data
    assert (tmp_path / "elasticity" / "2026-05-17" / "data.json").exists()

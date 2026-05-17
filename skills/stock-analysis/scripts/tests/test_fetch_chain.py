"""测试 fetch_chain：用 fake akshare 模块替代真实网络。"""
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_chain import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [
            {"item": "股票简称", "value": "比亚迪"},
            {"item": "行业", "value": "汽车整车"},
        ]

    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8}]

    def stock_zygc_em(self, symbol):
        return [{"分类": "新能源汽车", "营收占比": "78%", "毛利率": "20.5%"}]

    def stock_news_em(self, symbol):
        return [{"标题": "比亚迪汉 EV 销量创新高", "发布时间": "2026-05-15"}]


def test_module_name():
    assert MODULE_NAME == "chain"


def test_fetch_writes_data_json_and_latest(tmp_path):
    fake = FakeAk()
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=fake)
    assert data["module"] == "chain"
    assert data["ymd"] == "2026-05-17"
    assert "meta" in data
    assert "quote" in data
    assert "business_segments" in data
    assert "news" in data

    out_dir = tmp_path / "chain" / "2026-05-17"
    assert (out_dir / "data.json").exists()
    assert (tmp_path / "chain" / "latest").resolve() == out_dir.resolve()


def test_fetch_meta_extracted(tmp_path):
    fake = FakeAk()
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=fake)
    assert data["meta"]["name"] == "比亚迪"
    assert data["meta"]["code"] == "002594"
    assert data["meta"]["industry"] == "汽车整车"


def test_fetch_quote_extracted(tmp_path):
    fake = FakeAk()
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=fake)
    assert data["quote"]["price"] == 280.5
    assert data["quote"]["pe"] == 32.4

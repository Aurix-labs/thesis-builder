from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.stock_resolver import detect_market, prefixed_code, resolve_from_output, resolve_stock
from lib.trade_calendar import latest_completed_trade_date


def test_detect_market():
    assert detect_market("600519") == "sh"
    assert detect_market("688001") == "sh"
    assert detect_market("000001") == "sz"
    assert detect_market("300750") == "sz"


def test_prefixed_code():
    assert prefixed_code("600519") == "sh600519"
    assert prefixed_code("002594") == "sz002594"


def test_resolve_from_output_by_name(tmp_path):
    (tmp_path / "比亚迪_002594").mkdir()
    code, name, stock_dir = resolve_from_output("比亚迪", tmp_path)
    assert code == "002594"
    assert name == "比亚迪"
    assert stock_dir == tmp_path / "比亚迪_002594"


class FakeAkshare:
    @staticmethod
    def stock_individual_info_em(symbol):
        return [
            {"item": "股票简称", "value": "比亚迪"},
            {"item": "行业", "value": "汽车整车"},
        ]


def test_resolve_stock_fetches_name_for_first_code_call(tmp_path):
    code, name, stock_dir = resolve_stock("002594", tmp_path, akshare_module=FakeAkshare)
    assert code == "002594"
    assert name == "比亚迪"
    assert stock_dir == tmp_path / "比亚迪_002594"


def test_latest_completed_trade_date_from_daily_rows():
    rows = [
        {"日期": "2026-05-26", "收盘": 10.0},
        {"日期": "2026-05-27", "收盘": 10.2},
        {"日期": "2026-05-28", "收盘": 10.5},
    ]
    assert latest_completed_trade_date(rows) == "2026-05-28"

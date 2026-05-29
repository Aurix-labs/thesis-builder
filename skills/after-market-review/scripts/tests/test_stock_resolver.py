from pathlib import Path
import sys

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.stock_resolver import detect_market, prefixed_code, resolve_from_output, resolve_stock
from lib.trade_calendar import latest_completed_trade_date


def test_detect_market():
    assert detect_market("600519") == "sh"
    assert detect_market("688001") == "sh"
    assert detect_market("000001") == "sz"
    assert detect_market("300750") == "sz"


def test_detect_market_unsupported_prefix_raises():
    with pytest.raises(ValueError, match="unsupported A-share code"):
        detect_market("123456")


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


class FakeAkshareDataFrame:
    @staticmethod
    def stock_individual_info_em(symbol):
        return pd.DataFrame(
            [
                {"item": "股票简称", "value": "比亚迪"},
                {"item": "行业", "value": "汽车整车"},
            ]
        )


def test_resolve_stock_fetches_name_from_dataframe_for_first_code_call(tmp_path):
    code, name, stock_dir = resolve_stock("002594", tmp_path, akshare_module=FakeAkshareDataFrame)
    assert code == "002594"
    assert name == "比亚迪"
    assert stock_dir == tmp_path / "比亚迪_002594"


class FakeAkshareCodeName:
    @staticmethod
    def stock_info_a_code_name():
        return [
            {"code": "002594", "name": "比亚迪"},
            {"code": "600519", "name": "贵州茅台"},
        ]


def test_resolve_stock_fetches_code_for_first_name_call(tmp_path):
    code, name, stock_dir = resolve_stock("比亚迪", tmp_path, akshare_module=FakeAkshareCodeName)
    assert code == "002594"
    assert name == "比亚迪"
    assert stock_dir == tmp_path / "比亚迪_002594"


class FakeAkshareAmbiguousName:
    @staticmethod
    def stock_info_a_code_name():
        return [
            {"code": "111111", "name": "测试股份"},
            {"code": "222222", "name": "测试股份"},
        ]


def test_resolve_stock_ambiguous_name_from_akshare_raises(tmp_path):
    with pytest.raises(ValueError) as excinfo:
        resolve_stock("测试股份", tmp_path, akshare_module=FakeAkshareAmbiguousName)

    message = str(excinfo.value)
    assert "ambiguous" in message
    assert "测试股份_111111" in message
    assert "测试股份_222222" in message


class FakeAkshareNoNameMatch:
    @staticmethod
    def stock_info_a_code_name():
        return [{"code": "002594", "name": "比亚迪"}]


def test_resolve_stock_unknown_name_without_output_dir_raises_clear_error(tmp_path):
    with pytest.raises(ValueError, match="未能通过 stock_info_a_code_name 解析"):
        resolve_stock("不存在公司", tmp_path, akshare_module=FakeAkshareNoNameMatch)


def test_resolve_from_output_ambiguous_name_raises_with_candidates(tmp_path):
    (tmp_path / "比亚迪_002594").mkdir()
    (tmp_path / "比亚迪_099999").mkdir()
    (tmp_path / "比亚迪_notes").mkdir()

    with pytest.raises(ValueError) as excinfo:
        resolve_from_output("比亚迪", tmp_path)

    message = str(excinfo.value)
    assert "ambiguous" in message
    assert "6-digit code" in message
    assert "比亚迪_002594" in message
    assert "比亚迪_099999" in message
    assert "比亚迪_notes" not in message


def test_resolve_from_output_ambiguous_code_raises_with_candidates(tmp_path):
    (tmp_path / "A公司_002594").mkdir()
    (tmp_path / "比亚迪_002594").mkdir()

    with pytest.raises(ValueError) as excinfo:
        resolve_from_output("002594", tmp_path)

    message = str(excinfo.value)
    assert "ambiguous" in message
    assert "6-digit code" in message
    assert "A公司_002594" in message
    assert "比亚迪_002594" in message


def test_latest_completed_trade_date_from_daily_rows():
    rows = [
        {"日期": "2026-05-26", "收盘": 10.0},
        {"日期": "2026-05-27", "收盘": 10.2},
        {"日期": "2026-05-28", "收盘": 10.5},
    ]
    assert latest_completed_trade_date(rows) == "2026-05-28"


def test_latest_completed_trade_date_handles_unsorted_rows():
    rows = [
        {"日期": "2026-05-28", "收盘": 10.5},
        {"日期": "2026-05-26", "收盘": 10.0},
        {"日期": "2026-05-27", "收盘": 10.2},
    ]
    assert latest_completed_trade_date(rows) == "2026-05-28"


def test_latest_completed_trade_date_empty_rows_raises():
    with pytest.raises(ValueError, match="daily rows contain no trade date"):
        latest_completed_trade_date([])

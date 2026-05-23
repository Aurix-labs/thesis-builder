"""测试 render_schema：merged data.json 必填字段校验。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import pytest
from lib.render_schema import RenderError, validate_schema


def _minimal_valid_data() -> dict:
    """构造一份满足 schema 的最小 data.json，供测试改单字段触发失败。"""
    return {
        "meta": {
            "stock_code": "002594",
            "stock_name": "比亚迪",
            "stock_dir": "比亚迪_002594",
            "ymd": "2026-05-15",
            "time_utc8": "14:32",
            "session_id": "0x3f4a",
            "data_as_of": "2026-05-15",
            "research_status": "持续跟踪",
        },
        "chain": {"summary": {"industry_phase": "复苏中", "thesis_one_liner": "x"}},
        "rubric": {
            "summary": {
                "total": 72,
                "passed": 14,
                "dimensions": [
                    {"name": "基本面", "points_max": 30, "points_got": 18},
                    {"name": "产业匹配", "points_max": 20, "points_got": 16},
                    {"name": "业绩弹性", "points_max": 20, "points_got": 14},
                    {"name": "估值与位置", "points_max": 15, "points_got": 12},
                    {"name": "资金交易", "points_max": 10, "points_got": 7},
                    {"name": "治理风险", "points_max": 5, "points_got": 5},
                ],
                "financials_table": [
                    {"year": 2023, "revenue": 6023.15, "net_profit": 300.41, "gross_margin": 0.20, "roe": 0.21},
                    {"year": 2024, "revenue": 7773.34, "net_profit": 402.54, "gross_margin": 0.21, "roe": 0.22},
                    {"year": 2025, "revenue": 8500.00, "net_profit": 500.00, "gross_margin": 0.22, "roe": 0.23},
                ],
                "revenue_breakdown": [
                    {"name": "汽车", "value": 7800, "percent": 0.79},
                    {"name": "电池外供", "value": 1200, "percent": 0.12},
                ],
            }
        },
        "elasticity": {
            "summary": {
                "tree_children": [
                    {"name": "整车", "ratio": "55%", "margin": "20%", "factor": "1.8x", "is_core": True},
                    {"name": "电池外供", "ratio": "12%", "margin": "15%", "factor": "1.2x", "is_core": False},
                ]
            }
        },
        "risk": {"summary": {"level": "中"}},
        "valuation": {
            "summary": {
                "targets": {
                    "short": 240.0,
                    "mid": 290.0,
                    "long": 350.0,
                    "mid_change_pct": 15.9,
                    "base_date": "2026-05-15",
                },
                "rr": 2.8,
            }
        },
        "flow_tech": {
            "kline_daily": [["2025-11-13", 230.0, 232.5, 228.0, 233.0, 1000] for _ in range(120)]
        },
        "peers": {"summary": {"list": [{"code": "601127", "name": "赛力斯", "highlight": "新势力对标"}]}},
    }


def test_minimal_valid_data_passes():
    validate_schema(_minimal_valid_data())  # no exception


def test_missing_meta_field_raises():
    d = _minimal_valid_data()
    del d["meta"]["stock_code"]
    with pytest.raises(RenderError, match="meta.stock_code"):
        validate_schema(d)


def test_missing_rubric_total_raises():
    d = _minimal_valid_data()
    del d["rubric"]["summary"]["total"]
    with pytest.raises(RenderError, match="rubric.summary.total"):
        validate_schema(d)


def test_rubric_total_wrong_type_raises():
    d = _minimal_valid_data()
    d["rubric"]["summary"]["total"] = "70"
    with pytest.raises(RenderError, match="rubric.summary.total"):
        validate_schema(d)


def test_rubric_dimensions_wrong_count_raises():
    d = _minimal_valid_data()
    d["rubric"]["summary"]["dimensions"] = d["rubric"]["summary"]["dimensions"][:5]
    with pytest.raises(RenderError, match="rubric.summary.dimensions"):
        validate_schema(d)


def test_elasticity_tree_children_empty_raises():
    d = _minimal_valid_data()
    d["elasticity"]["summary"]["tree_children"] = []
    with pytest.raises(RenderError, match="elasticity.summary.tree_children"):
        validate_schema(d)


def test_risk_level_invalid_value_raises():
    d = _minimal_valid_data()
    d["risk"]["summary"]["level"] = "毁灭"
    with pytest.raises(RenderError, match="risk.summary.level"):
        validate_schema(d)


def test_valuation_targets_missing_mid_raises():
    d = _minimal_valid_data()
    del d["valuation"]["summary"]["targets"]["mid"]
    with pytest.raises(RenderError, match="valuation.summary.targets.mid"):
        validate_schema(d)


def test_flow_tech_kline_too_short_raises():
    d = _minimal_valid_data()
    d["flow_tech"]["kline_daily"] = d["flow_tech"]["kline_daily"][:30]
    with pytest.raises(RenderError, match="flow_tech.kline_daily"):
        validate_schema(d)


def test_missing_nested_field_in_list_item_raises():
    """`*` fanout 应能在列表元素的缺字段时定位到 [i].field。"""
    d = _minimal_valid_data()
    del d["rubric"]["summary"]["dimensions"][2]["points_max"]
    with pytest.raises(RenderError, match=r"rubric\.summary\.dimensions\[2\]\.points_max"):
        validate_schema(d)


def test_bool_rejected_for_numeric_tuple_field():
    """bool 不能蒙混过 (int, float) 类型字段（True 是 int 子类）。"""
    d = _minimal_valid_data()
    d["rubric"]["summary"]["financials_table"][0]["revenue"] = True
    with pytest.raises(RenderError, match=r"financials_table\[0\]\.revenue.*bool"):
        validate_schema(d)


def test_top_level_non_dict_raises():
    with pytest.raises(RenderError, match="顶层不是 dict"):
        validate_schema([])  # type: ignore

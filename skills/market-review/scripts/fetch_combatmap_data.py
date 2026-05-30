"""M6 combatmap · 从前五模块 data.json 提取关键参数。

本模块不从 akshare 拉数据，只读前五模块的 data.json，
提取结构化的关键参数写入 market_data.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from lib.module_io import write_module_data, read_module_data, _MarketEncoder

MODULE_NAME = "combatmap"
PREREQ_MODULES = ["index", "sentiment", "mainline", "capital", "variables"]


def _safe_read(output_root: Path, ymd: str, module: str) -> dict:
    try:
        return read_module_data(output_root, ymd, module)
    except (FileNotFoundError, KeyError):
        return {}


def _extract_index_params(index_data: dict) -> dict:
    """从模块一提取大盘参数"""
    result = {"trends": {}, "total_amount_yi": index_data.get("total_amount_yi")}
    idx_map = index_data.get("index_data", {})
    for code, info in idx_map.items():
        name = info.get("name", code)
        result["trends"][name] = info.get("trend", "未知")
    result["breadth"] = index_data.get("breadth", {})
    return result


def _extract_sentiment_params(sentiment_data: dict) -> dict:
    """从模块二提取情绪参数"""
    return {
        "limit_up_count": sentiment_data.get("limit_up_count", 0),
        "limit_down_count": sentiment_data.get("limit_down_count", 0),
        "max_consecutive_board": sentiment_data.get("max_consecutive_board", 0),
        "board_gradient": sentiment_data.get("board_gradient", {}),
        "bomb_rate_pct": sentiment_data.get("bomb_rate_pct", 0),
        "big_noodle_count": sentiment_data.get("big_noodle_count", 0),
    }


def _extract_mainline_params(mainline_data: dict) -> dict:
    """从模块三提取主线参数"""
    return {
        "limit_up_by_sector": mainline_data.get("limit_up_by_sector", {}),
        "sector_flow_top10": mainline_data.get("sector_flow_top20", [])[:10],
    }


def _extract_capital_params(capital_data: dict) -> dict:
    """从模块四提取资金参数"""
    nb = capital_data.get("northbound", {})
    return {
        "northbound_today_net": nb.get("today_net"),
        "northbound_3d": capital_data.get("northbound_3d", []),
        "lhb_count": capital_data.get("lhb_count", 0),
    }


def _extract_variables_params(variables_data: dict) -> dict:
    """从模块五提取变量参数"""
    us = variables_data.get("us_market", {})
    hk = variables_data.get("hk_market", {})
    comm = variables_data.get("commodities", {})
    return {
        "us_market_summary": {
            k: v[-1] if v else None
            for k, v in us.items()
        },
        "hk_market_summary": {
            k: v[-1] if v else None
            for k, v in hk.items()
        },
        "commodities_summary": {
            k: v[-1] if v else None
            for k, v in comm.items()
        },
    }


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    output_root = Path(output_root)

    index_d = _safe_read(output_root, today, "index")
    sentiment_d = _safe_read(output_root, today, "sentiment")
    mainline_d = _safe_read(output_root, today, "mainline")
    capital_d = _safe_read(output_root, today, "capital")
    variables_d = _safe_read(output_root, today, "variables")

    market_data = {
        "date": today,
        "index": _extract_index_params(index_d),
        "sentiment": _extract_sentiment_params(sentiment_d),
        "mainline": _extract_mainline_params(mainline_d),
        "capital": _extract_capital_params(capital_d),
        "variables": _extract_variables_params(variables_d),
        "_prereq_status": {
            "index": "ok" if index_d else "missing",
            "sentiment": "ok" if sentiment_d else "missing",
            "mainline": "ok" if mainline_d else "missing",
            "capital": "ok" if capital_d else "missing",
            "variables": "ok" if variables_d else "missing",
        },
    }

    # 写入两个文件：data.json（内部用）+ market_data.json（供 stock-review 消费）
    write_module_data(output_root, MODULE_NAME, today, market_data)
    market_data_path = output_root / today / MODULE_NAME / "market_data.json"
    market_data_path.write_text(
        json.dumps(market_data, ensure_ascii=False, indent=2, cls=_MarketEncoder),
        encoding="utf-8",
    )
    return market_data

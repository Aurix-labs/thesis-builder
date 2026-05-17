"""M1 chain · 产业链与趋势 数据采集。

字段：meta、quote、industry（meta 内）、business_segments、news
覆盖 Step 1 宏观 + Step 2 产业链
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data


MODULE_NAME = "chain"
FIELDS = ["meta", "quote", "business_segments", "news"]


def _extract_meta(info_records: list[dict], code: str) -> dict:
    out: dict[str, Any] = {"code": code}
    for row in info_records or []:
        item = row.get("item")
        value = row.get("value")
        if item == "股票简称" or item == "名称":
            out["name"] = str(value).strip() if value else None
        elif item == "行业":
            out["industry"] = str(value).strip() if value else None
    return out


def _extract_quote(spot_records: list[dict], code: str) -> dict:
    for row in spot_records or []:
        row_code = str(row.get("代码", "")).strip()
        if row_code == code:
            return {
                "price": row.get("最新价"),
                "market_cap": row.get("总市值"),
                "pe": row.get("市盈率-动态"),
                "pb": row.get("市净率"),
            }
    return {"price": None, "market_cap": None, "pe": None, "pb": None}


def fetch(
    code: str,
    name: str,
    stock_dir: Path,
    today: str,
    *,
    akshare_module=None,
) -> dict:
    """采集 chain 模块所需数据并写 data.json + 更新 latest 软链。

    Args:
        akshare_module: 注入测试用 fake；默认 None 时 import 真 akshare
    """
    if akshare_module is None:
        import akshare as akshare_module  # noqa

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    segments = cached_call(stock_dir, today, "stock_zygc_em",
                           akshare_module.stock_zygc_em, symbol=code)
    news = cached_call(stock_dir, today, "stock_news_em",
                       akshare_module.stock_news_em, symbol=code)

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name
    quote = _extract_quote(spot, code)

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": quote,
        "business_segments": segments,
        "news": news,
    }
    write_module_data(stock_dir, MODULE_NAME, today, data)
    return data

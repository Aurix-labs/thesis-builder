"""M2 rubric · 公司质地 数据采集。

字段：meta、quote、financial_abstract、top_holders、margin
覆盖 Step 3 Rubric 100 分评分
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from fetch_chain import _extract_meta, _extract_quote


MODULE_NAME = "rubric"
FIELDS = ["meta", "quote", "financial_abstract", "top_holders", "margin"]


def _detect_market(code: str) -> str:
    """返回 'sh'/'sz'/'bj'。"""
    if code.startswith(("60", "68", "11", "12", "5")):
        return "sh"
    if code.startswith(("00", "30", "20", "15", "16", "18")):
        return "sz"
    return "bj"


def _last_trade_day(today: str) -> str:
    d = dt.date.fromisoformat(today) - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


def fetch(code: str, name: str, stock_dir: Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    market = _detect_market(code)
    prefixed = f"{market}{code}"
    last_trade = _last_trade_day(today)

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    fa = cached_call(stock_dir, today, "stock_financial_abstract",
                     akshare_module.stock_financial_abstract, symbol=code)
    holders = cached_call(stock_dir, today, "stock_gdfx_top_10_em",
                          akshare_module.stock_gdfx_top_10_em, symbol=prefixed, date=last_trade)
    if market == "sh":
        margin = cached_call(stock_dir, today, "stock_margin_detail_sse",
                             akshare_module.stock_margin_detail_sse, date=last_trade)
    else:
        margin = cached_call(stock_dir, today, "stock_margin_detail_szse",
                             akshare_module.stock_margin_detail_szse, date=last_trade)
    margin_self = [r for r in (margin or []) if str(r.get("代码", "")).strip().endswith(code)]

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "financial_abstract": fa,
        "top_holders": holders,
        "margin": margin_self,
    }
    write_module_data(stock_dir, MODULE_NAME, today, data)
    return data

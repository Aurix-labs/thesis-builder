"""M5 valuation · 估值与赔率 数据采集。

字段：meta、quote、financial_abstract、research、recommend、kline_daily（近 30 天）
覆盖 Step 6 估值与赔率（不含 6a+/6a++）
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from fetch_chain import _extract_meta, _extract_quote


MODULE_NAME = "valuation"
FIELDS = ["meta", "quote", "financial_abstract", "research", "recommend", "kline_daily"]


def _filter_by_code(records: list[dict], code: str) -> list[dict]:
    if not records:
        return []
    out = []
    for r in records:
        for col in ("代码", "股票代码", "证券代码"):
            v = str(r.get(col, "")).strip()
            if v == code or v.endswith(code):
                out.append(r)
                break
    return out


def fetch(code: str, name: str, stock_dir: Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    today_d = dt.date.fromisoformat(today)
    today_s = today_d.strftime("%Y%m%d")
    start_s = (today_d - dt.timedelta(days=30)).strftime("%Y%m%d")

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    fa = cached_call(stock_dir, today, "stock_financial_abstract",
                     akshare_module.stock_financial_abstract, symbol=code)
    research = cached_call(stock_dir, today, "stock_research_report_em",
                           akshare_module.stock_research_report_em, symbol=code)
    recommend_all = cached_call(stock_dir, today, "stock_institute_recommend",
                                akshare_module.stock_institute_recommend, symbol="股票综合评级")
    recommend = _filter_by_code(recommend_all, code)
    kline = cached_call(stock_dir, today, "stock_zh_a_hist",
                        akshare_module.stock_zh_a_hist,
                        symbol=code, period="daily",
                        start_date=start_s, end_date=today_s, adjust="qfq")

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "financial_abstract": fa,
        "research": research,
        "recommend": recommend,
        "kline_daily": kline,
    }
    write_module_data(stock_dir, MODULE_NAME, today, data)
    return data

"""M6 flow-tech · 资金与技术面 数据采集。

字段：meta、quote、kline_daily（近 1 年）、top_holders、fund_flow、margin
覆盖 Step 6a+ 资金面 + Step 6a++ 技术面
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from fetch_chain import _extract_meta, _extract_quote
from fetch_rubric import _detect_market, _last_trade_day


MODULE_NAME = "flow-tech"
FIELDS = ["meta", "quote", "kline_daily", "top_holders", "fund_flow", "margin"]


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
    start_s = (today_d - dt.timedelta(days=365)).strftime("%Y%m%d")
    last_trade = _last_trade_day(today)
    market = _detect_market(code)
    prefixed = f"{market}{code}"

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    kline = cached_call(stock_dir, today, "stock_zh_a_hist",
                        akshare_module.stock_zh_a_hist,
                        symbol=code, period="daily",
                        start_date=start_s, end_date=today_s, adjust="qfq")
    holders = cached_call(stock_dir, today, "stock_gdfx_top_10_em",
                          akshare_module.stock_gdfx_top_10_em,
                          symbol=prefixed, date=last_trade)
    fund_flow = cached_call(stock_dir, today, "stock_individual_fund_flow",
                            akshare_module.stock_individual_fund_flow,
                            stock=code, market=market)
    if market == "sh":
        margin = cached_call(stock_dir, today, "stock_margin_detail_sse",
                             akshare_module.stock_margin_detail_sse, date=last_trade)
    else:
        margin = cached_call(stock_dir, today, "stock_margin_detail_szse",
                             akshare_module.stock_margin_detail_szse, date=last_trade)
    margin_self = _filter_by_code(margin, code)

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "kline_daily": kline,
        "top_holders": holders,
        "fund_flow": fund_flow,
        "margin": margin_self,
    }
    write_module_data(stock_dir, MODULE_NAME, today, data)
    return data

"""M3 elasticity · 业绩弹性 数据采集。

字段：meta、quote、financial_abstract、business_segments
覆盖 Step 4 弹性测算
"""
from __future__ import annotations

from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from fetch_chain import _extract_meta, _extract_quote


MODULE_NAME = "elasticity"
FIELDS = ["meta", "quote", "financial_abstract", "business_segments"]


def fetch(code: str, name: str, stock_dir: Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    fa = cached_call(stock_dir, today, "stock_financial_abstract",
                     akshare_module.stock_financial_abstract, symbol=code)
    segments = cached_call(stock_dir, today, "stock_zygc_em",
                           akshare_module.stock_zygc_em, symbol=code)

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "financial_abstract": fa,
        "business_segments": segments,
    }
    write_module_data(stock_dir, MODULE_NAME, today, data)
    return data

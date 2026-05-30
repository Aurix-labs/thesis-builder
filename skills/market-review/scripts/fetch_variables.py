"""M5 variables · 盘后变量汇总 数据采集。

仅拉海外市场收盘数据。新闻/政策部分留给 Agent WebSearch。
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "variables"


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    # 美股三大指数
    us_market = {}
    try:
        df_dji = ak.index_us_stock_sina(symbol=".DJI")
        if df_dji is not None and not df_dji.empty:
            recs = df_dji.to_dict(orient="records") if hasattr(df_dji, "to_dict") else list(df_dji)
            us_market["dji"] = recs[-5:] if recs else []
    except Exception:
        us_market["dji"] = []

    try:
        df_ixic = ak.index_us_stock_sina(symbol=".IXIC")
        if df_ixic is not None and not df_ixic.empty:
            recs = df_ixic.to_dict(orient="records") if hasattr(df_ixic, "to_dict") else list(df_ixic)
            us_market["nasdaq"] = recs[-5:] if recs else []
    except Exception:
        us_market["nasdaq"] = []

    try:
        df_spx = ak.index_us_stock_sina(symbol=".INX")
        if df_spx is not None and not df_spx.empty:
            recs = df_spx.to_dict(orient="records") if hasattr(df_spx, "to_dict") else list(df_spx)
            us_market["sp500"] = recs[-5:] if recs else []
    except Exception:
        us_market["sp500"] = []

    # 港股恒生
    hk_market = {}
    try:
        df_hsi = ak.stock_hk_index_daily_sina(symbol="HSI")
        if df_hsi is not None and not df_hsi.empty:
            recs = df_hsi.to_dict(orient="records") if hasattr(df_hsi, "to_dict") else list(df_hsi)
            hk_market["hsi"] = recs[-5:] if recs else []
    except Exception:
        hk_market["hsi"] = []

    # 大宗商品（原油、黄金）
    commodities = {}
    try:
        df_oil = ak.futures_foreign_hist(symbol="原油")
        if df_oil is not None and not df_oil.empty:
            recs = df_oil.to_dict(orient="records") if hasattr(df_oil, "to_dict") else list(df_oil)
            commodities["crude_oil"] = recs[-3:] if recs else []
    except Exception:
        commodities["crude_oil"] = []

    try:
        df_gold = ak.futures_foreign_hist(symbol="黄金")
        if df_gold is not None and not df_gold.empty:
            recs = df_gold.to_dict(orient="records") if hasattr(df_gold, "to_dict") else list(df_gold)
            commodities["gold"] = recs[-3:] if recs else []
    except Exception:
        commodities["gold"] = []

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "us_market": us_market,
        "hk_market": hk_market,
        "commodities": commodities,
        "_note": "新闻/政策部分由 Agent 通过 WebSearch 获取并直接写入 report.md",
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

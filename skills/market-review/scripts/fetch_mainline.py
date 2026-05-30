"""M3 mainline · 主线与支线识别 数据采集。

字段：sector_flow, sector_limit_up, mainline_candidates
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "mainline"


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    # 概念板块资金流向
    # 盘后东方财富 API 可能拒绝"今日"维度的请求，依次尝试多个参数组合
    sector_flow = []
    for indicator in ["今日", "3日", "5日"]:
        for sector_type in ["概念资金流", "行业资金流", "地域资金流"]:
            try:
                df = ak.stock_sector_fund_flow_rank(indicator=indicator, sector_type=sector_type)
                if df is not None and not df.empty:
                    sector_flow = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
                    break
            except Exception:
                continue
        if sector_flow:
            break

    # 涨停股按板块归类（需结合 sentiment 数据——这里先独立拉取涨停再归类）
    limit_up_by_sector: dict[str, int] = {}
    try:
        today_s = today_d.strftime("%Y%m%d")
        df_up = ak.stock_zt_pool_em(date=today_s)
        if df_up is not None and not df_up.empty:
            records = df_up.to_dict(orient="records") if hasattr(df_up, "to_dict") else list(df_up)
            for r in records:
                sector = str(r.get("所属行业", "") or r.get("板块", "") or "").strip()
                if sector:
                    limit_up_by_sector[sector] = limit_up_by_sector.get(sector, 0) + 1
    except Exception:
        pass

    # 按涨停家数排序，取前 10 板块
    top_sectors = sorted(limit_up_by_sector.items(), key=lambda x: x[1], reverse=True)[:10]

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "sector_flow_top20": sector_flow[:20],
        "limit_up_by_sector": dict(top_sectors),
        "sector_count": len(sector_flow),
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

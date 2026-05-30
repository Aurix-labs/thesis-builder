"""M4 capital · 资金行为监测 数据采集。

字段：northbound_flow, northbound_3d, lhb_list
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data, read_module_data

MODULE_NAME = "capital"


def _fetch_northbound(ak, today_d: dt.date) -> dict:
    """拉北向资金当日数据"""
    result = {"today_net": None, "recent_10d": []}
    try:
        # 沪股通
        df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
        # 深股通
        df_sz = ak.stock_hsgt_hist_em(symbol="深股通")

        if df_sh is not None and not df_sh.empty:
            sh_records = df_sh.to_dict(orient="records") if hasattr(df_sh, "to_dict") else list(df_sh)
            result["recent_10d"] = sh_records[-10:]

        if df_sz is not None and not df_sz.empty:
            sz_records = df_sz.to_dict(orient="records") if hasattr(df_sz, "to_dict") else list(df_sz)
            result["sz_recent_10d"] = sz_records[-10:]

        # 计算当日净买卖（最近一条记录）
        # 字段名：东方财富 A 股为 "当日成交净买额"，港股通可能不同
        sh_last = result.get("recent_10d", [])
        sz_last = result.get("sz_recent_10d", [])
        def _get_net(rec: dict) -> float:
            v = rec.get("当日成交净买额") or rec.get("净买额") or 0
            try:
                f = float(v)
                return 0.0 if (f != f) else f  # NaN → 0
            except (ValueError, TypeError):
                return 0.0
        sh_net = _get_net(sh_last[-1]) if sh_last else 0
        sz_net = _get_net(sz_last[-1]) if sz_last else 0
        if sh_net or sz_net:
            result["today_net"] = round(sh_net + sz_net, 2)
    except Exception:
        pass
    return result


def _fetch_lhb(ak, today_d: dt.date) -> list[dict]:
    """拉龙虎榜当日数据"""
    today_s = today_d.strftime("%Y%m%d")
    try:
        df = ak.stock_sina_lhb_detail_daily(trade_date=today_s)
        if df is not None and not df.empty:
            return df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
    except Exception:
        pass
    return []


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    northbound = _fetch_northbound(ak, today_d)
    lhb = _fetch_lhb(ak, today_d)

    # 尝试读前两日北向数据算 3 日流向
    nb_3d = [northbound.get("today_net")]
    for offset in (1, 2):
        prev_d = today_d - dt.timedelta(days=offset)
        try:
            prev_data = read_module_data(output_root, prev_d.isoformat(), MODULE_NAME)
            prev_nb = prev_data.get("northbound", {})
            nb_3d.append(prev_nb.get("today_net"))
        except (FileNotFoundError, KeyError):
            nb_3d.append(None)

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "northbound": northbound,
        "northbound_3d": nb_3d,
        "lhb_count": len(lhb),
        "lhb_sample": lhb[:30],
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

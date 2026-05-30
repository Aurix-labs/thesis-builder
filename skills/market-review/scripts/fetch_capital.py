"""M4 capital · 资金行为监测 数据采集。

数据源（按时效分级）：
  盘后立即可用：stock_market_fund_flow（全市场主力/散户资金流向）
  延迟 ~3h：    stock_hsgt_hist_em（北向资金净买卖额，约 18:00 后）
  延迟 ~1h：    stock_sina_lhb_detail_daily（龙虎榜，约 16:30 后陆续公布）
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data, read_module_data

MODULE_NAME = "capital"


def _fetch_market_fund_flow(ak) -> list[dict]:
    """拉全市场资金流向（主力/超大单/大单/中单/小单）。
    此接口盘后立即可用，数据可追溯到 120 个交易日。
    """
    try:
        df = ak.stock_market_fund_flow()
        if df is not None and not df.empty:
            return df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
    except Exception:
        pass
    return []


def _fetch_northbound(ak) -> dict:
    """拉北向资金数据。
    注意：'当日成交净买额' 等字段约 18:00 后才由东方财富更新，
    15:30 调用时通常为 NaN。但日期、上证指数、领涨股等字段可用。
    """
    result = {"today_net": None, "recent_10d": []}
    try:
        df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
        df_sz = ak.stock_hsgt_hist_em(symbol="深股通")

        if df_sh is not None and not df_sh.empty:
            sh_records = df_sh.to_dict(orient="records") if hasattr(df_sh, "to_dict") else list(df_sh)
            result["recent_10d"] = sh_records[-10:]

        if df_sz is not None and not df_sz.empty:
            sz_records = df_sz.to_dict(orient="records") if hasattr(df_sz, "to_dict") else list(df_sz)
            result["sz_recent_10d"] = sz_records[-10:]

        # 尝试提取净买额（盘后 3h 内通常为 NaN）
        sh_last = result.get("recent_10d", [])
        sz_last = result.get("sz_recent_10d", [])
        def _get_net(rec: dict) -> float | None:
            v = rec.get("当日成交净买额") or rec.get("净买额") or 0
            try:
                f = float(v)
                return None if (f != f) else None  # NaN → None
            except (ValueError, TypeError):
                return None
        sh_net = _get_net(sh_last[-1]) if sh_last else None
        sz_net = _get_net(sz_last[-1]) if sz_last else None
        if sh_net is not None and sz_net is not None:
            result["today_net"] = round(sh_net + sz_net, 2)
    except Exception:
        pass
    return result


def _fetch_lhb(ak, today_d: dt.date) -> list[dict]:
    """拉龙虎榜当日数据。约 16:30 后交易所陆续公布，15:30 调用通常返回空。"""
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

    # 1. 全市场资金流向（盘后立即可用）
    fund_flow = _fetch_market_fund_flow(ak)
    # 提取最近 5 日
    fund_flow_recent = fund_flow[-5:] if fund_flow else []
    # 提取当日
    fund_flow_today = fund_flow_recent[-1] if fund_flow_recent else {}

    # 2. 北向资金（约 18:00 后才有净买卖数据）
    northbound = _fetch_northbound(ak)

    # 3. 龙虎榜（约 16:30 后）
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

    # 数据时效说明
    timing_notes = []
    if not lhb:
        timing_notes.append("龙虎榜约 16:30 后公布，当前数据为空。建议 --force --module capital 重跑")
    if northbound.get("today_net") is None:
        timing_notes.append("北向资金净买卖额约 18:00 后更新，当前为 null。领涨股、上证指数等参考字段可用")

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "fund_flow": {
            "today": fund_flow_today,
            "recent_5d": fund_flow_recent,
            "available": len(fund_flow) > 0,
        },
        "northbound": northbound,
        "northbound_3d": nb_3d,
        "lhb_count": len(lhb),
        "lhb_sample": lhb[:30],
        "_timing_notes": timing_notes,
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

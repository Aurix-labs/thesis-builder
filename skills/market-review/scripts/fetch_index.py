"""M1 index · 大盘环境诊断 数据采集。

字段：index_quotes, breadth, volume_stage
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "index"
INDEX_CODES = {
    "sh000001": "上证指数",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000852": "中证1000",
    "sz399006": "创业板指",
}


def _get_close(r: dict) -> float:
    """akshare 返回的字段名可能是英文 'close' 或中文 '收盘'。"""
    return float(r.get("close", 0) or r.get("收盘", 0) or 0)


def _classify_trend(kline_records: list[dict]) -> str:
    """基于最近 20 条日 K 判断 MA5/MA20 方向。"""
    if len(kline_records) < 20:
        return "数据不足"
    closes = [_get_close(r) for r in kline_records[-20:]]
    if not closes or closes[-1] == 0:
        return "数据不足"
    ma5 = sum(closes[-5:]) / min(5, len(closes[-5:]))
    ma20 = sum(closes[-20:]) / min(20, len(closes[-20:]))
    prev_ma5 = sum(closes[-6:-1]) / min(5, len(closes[-6:-1])) if len(closes) >= 6 else ma5
    prev_ma20 = sum(closes[-21:-1]) / min(20, len(closes[-21:-1])) if len(closes) >= 21 else ma20

    if ma5 > ma20 and prev_ma5 > prev_ma20:
        return "多头排列"
    elif ma5 < ma20 and prev_ma5 < prev_ma20:
        return "空头排列"
    else:
        return "震荡"


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    today_d = dt.date.fromisoformat(today)
    today_s = today_d.strftime("%Y%m%d")
    start_s = (today_d - dt.timedelta(days=60)).strftime("%Y%m%d")

    output_root = Path(output_root)

    # 拉各指数日 K
    index_data = {}
    for code, name in INDEX_CODES.items():
        try:
            if code.startswith("sh"):
                symbol = code[2:]
                df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            else:
                symbol = code[2:]
                df = ak.stock_zh_index_daily(symbol=f"sz{symbol}")
        except Exception:
            try:
                df = ak.stock_zh_index_daily(symbol=code)
            except Exception:
                index_data[code] = {"name": name, "error": "fetch_failed", "kline": []}
                continue

        if df is not None and not df.empty:
            records = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
            # akshare 返回的列名可能是英文或中文
            index_data[code] = {
                "name": name,
                "kline": records[-30:],  # 最近 30 天
                "trend": _classify_trend(records),
            }
        else:
            index_data[code] = {"name": name, "error": "empty_data", "kline": []}

    # 涨跌家数（从全 A 指数成分推算或直接取东方财富接口）
    breadth = {"up": 0, "down": 0, "up_pct5": 0, "down_pct5": 0}
    try:
        # 尝试获取全市场涨跌统计
        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is not None and not spot_df.empty:
            records = spot_df.to_dict(orient="records") if hasattr(spot_df, "to_dict") else list(spot_df)
            for r in records:
                pct = float(r.get("涨跌幅", 0) or 0)
                if pct > 0:
                    breadth["up"] += 1
                elif pct < 0:
                    breadth["down"] += 1
                if pct > 5:
                    breadth["up_pct5"] += 1
                elif pct < -5:
                    breadth["down_pct5"] += 1
    except Exception:
        pass

    # 计算全市场总成交额
    # 注意：stock_zh_index_daily 对指数来说 'volume' 字段是成交额（元）
    total_amount = 0.0
    for code_data in index_data.values():
        kline = code_data.get("kline", [])
        if kline:
            last = kline[-1]
            amount = float(last.get("volume", 0) or last.get("成交额", 0) or 0)
            total_amount += amount

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "index_data": index_data,
        "breadth": breadth,
        "total_amount_yi": round(total_amount / 1e8, 2) if total_amount > 0 else None,
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

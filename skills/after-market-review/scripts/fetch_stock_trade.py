from __future__ import annotations

import datetime as dt
from typing import Any

from lib.normalize import pct_change, to_float
from lib.status import ERROR, OK, layer_result
from lib.trade_calendar import latest_completed_trade_date


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _last_n(rows: list[dict], n: int) -> list[dict]:
    return rows[-n:] if len(rows) >= n else rows


def _daily_summary(rows: list[dict]) -> dict:
    last = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else {}
    close = to_float(last.get("收盘") or last.get("close"))
    prev_close = to_float(prev.get("收盘") or prev.get("close"))
    volume = to_float(last.get("成交量") or last.get("volume"))
    amount = to_float(last.get("成交额") or last.get("amount"))
    return {
        "date": str(last.get("日期") or last.get("date"))[:10],
        "open": to_float(last.get("开盘") or last.get("open")),
        "high": to_float(last.get("最高") or last.get("high")),
        "low": to_float(last.get("最低") or last.get("low")),
        "close": close,
        "prev_close": prev_close,
        "change_pct": pct_change(close, prev_close),
        "volume": volume,
        "amount": amount,
        "turnover": to_float(last.get("换手率") or last.get("turnover")),
    }


def _intraday_pattern(minute_rows: list[dict]) -> str:
    if len(minute_rows) < 4:
        return "分钟线不足"
    first = to_float(minute_rows[0].get("收盘") or minute_rows[0].get("close"))
    mid_row = minute_rows[len(minute_rows) // 2]
    mid = to_float(mid_row.get("收盘") or mid_row.get("close"))
    last = to_float(minute_rows[-1].get("收盘") or minute_rows[-1].get("close"))
    if first is None or mid is None or last is None:
        return "分钟线价格字段不足"
    if mid < first and last > mid:
        return "盘中回落后修复"
    if mid > first and last > mid:
        return "震荡上行"
    if mid < first and last < mid:
        return "震荡下行"
    return "横盘震荡"


def fetch(code: str, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    try:
        today_d = dt.date.fromisoformat(today)
        start = (today_d - dt.timedelta(days=60)).strftime("%Y%m%d")
        end = today_d.strftime("%Y%m%d")
        daily_rows = _records(
            akshare_module.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="qfq",
            )
        )
        if not daily_rows:
            return layer_result(ERROR, {}, ["stock_zh_a_hist returned no rows"])

        trade_date = latest_completed_trade_date(daily_rows)
        minute_start = f"{trade_date} 09:30:00"
        minute_end = f"{trade_date} 15:00:00"
        minute_rows = _records(
            akshare_module.stock_zh_a_hist_min_em(
                symbol=code,
                start_date=minute_start,
                end_date=minute_end,
                period="1",
                adjust="",
            )
        )
        data = {
            "trade_date": trade_date,
            "daily": _daily_summary(daily_rows),
            "recent_daily": _last_n(daily_rows, 20),
            "minute_rows": minute_rows,
            "intraday_pattern": _intraday_pattern(minute_rows),
        }
        return layer_result(OK, data, [])
    except Exception as exc:
        return layer_result(ERROR, {}, [f"stock_trade failed: {exc}"])

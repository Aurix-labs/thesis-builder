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


def _row_date(row: dict) -> str:
    return str(row.get("日期") or row.get("date") or "")[:10]


def _sorted_daily_rows(rows: list[dict], today: str) -> list[dict]:
    return sorted(
        [row for row in rows if _row_date(row) and _row_date(row) <= today],
        key=_row_date,
    )


def _close(row: dict) -> float | None:
    if "收盘" in row:
        return to_float(row.get("收盘"))
    return to_float(row.get("close"))


def _daily_summary(rows: list[dict]) -> dict:
    last = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else {}
    close = _close(last)
    prev_close = _close(prev)
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
    closes = [_close(row) for row in minute_rows]
    valid_closes = [close for close in closes if close is not None]
    if len(valid_closes) < 4:
        return "分钟线不足"
    first = valid_closes[0]
    mid = valid_closes[len(valid_closes) // 2]
    last = valid_closes[-1]
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

        daily_rows = _sorted_daily_rows(daily_rows, today)
        if not daily_rows:
            return layer_result(ERROR, {}, ["stock_zh_a_hist returned no completed daily rows"])

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

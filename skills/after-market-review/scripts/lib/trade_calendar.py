from __future__ import annotations

from typing import Iterable


def latest_completed_trade_date(daily_rows: Iterable[dict]) -> str:
    dates: list[str] = []
    for row in daily_rows:
        value = row.get("日期") or row.get("date")
        if value:
            dates.append(str(value)[:10])
    if not dates:
        raise ValueError("daily rows contain no trade date")
    return sorted(dates)[-1]

"""交易日辅助：获取最近交易日。"""
from __future__ import annotations

import datetime as dt


def last_trade_day(today: str | None = None) -> str:
    """推算最近交易日（简单规则：跳过周末；不含节假日判断）。"""
    d = dt.date.fromisoformat(today) if today else dt.date.today()
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= dt.timedelta(days=1)
    return d.isoformat()

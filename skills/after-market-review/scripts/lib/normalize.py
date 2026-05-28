from __future__ import annotations

import datetime as dt
import math
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    if isinstance(value, int):
        return float(value)
    s = str(value).strip().replace(",", "")
    if s in {"", "-", "--", "nan", "None"}:
        return None
    if s.endswith("%"):
        s = s[:-1]
    try:
        out = float(s)
    except ValueError:
        return None
    if math.isnan(out):
        return None
    return out


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / previous * 100


def bucket_time(time_text: str, window_minutes: int) -> str:
    parsed = dt.datetime.strptime(time_text[:8], "%H:%M:%S")
    if parsed.time() == dt.time(hour=15):
        parsed -= dt.timedelta(microseconds=1)
    t = parsed.time()
    start_minute = (t.minute // window_minutes) * window_minutes
    start = dt.time(hour=t.hour, minute=start_minute)
    end_dt = dt.datetime.combine(dt.date(2000, 1, 1), start) + dt.timedelta(minutes=window_minutes)
    end = end_dt.time()
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"

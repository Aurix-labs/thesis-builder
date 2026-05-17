"""TTL 命中判定。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .module_io import get_latest_ymd


def days_between(ymd_start: str, ymd_end: str) -> int:
    """返回 (ymd_end - ymd_start) 的天数。"""
    s = dt.date.fromisoformat(ymd_start)
    e = dt.date.fromisoformat(ymd_end)
    return (e - s).days


def is_within_ttl(stock_dir: Path, module: str, today: str, ttl_days: int) -> tuple[bool, str | None]:
    """返回 (是否命中 TTL, latest ymd)。无 latest 时返回 (False, None)。"""
    latest = get_latest_ymd(stock_dir, module)
    if latest is None:
        return False, None
    delta = days_between(latest, today)
    return delta <= ttl_days, latest

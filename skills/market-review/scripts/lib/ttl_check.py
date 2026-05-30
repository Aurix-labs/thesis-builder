"""TTL 命中判定。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .module_io import get_latest_ymd


def days_between(ymd_start: str, ymd_end: str) -> int:
    s = dt.date.fromisoformat(ymd_start)
    e = dt.date.fromisoformat(ymd_end)
    return (e - s).days


def is_within_ttl(output_root: Path, module: str, today: str, ttl_days: int) -> tuple[bool, str | None]:
    latest = get_latest_ymd(output_root, module)
    if latest is None:
        return False, None
    delta = days_between(latest, today)
    return delta <= ttl_days, latest

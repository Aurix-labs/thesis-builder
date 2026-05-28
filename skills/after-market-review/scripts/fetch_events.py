from __future__ import annotations

import datetime as dt
from typing import Any

from lib.status import OK, PARTIAL, UNAVAILABLE, layer_result


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _published_at(row: dict) -> str:
    for key in ("发布时间", "发布日期", "时间", "date", "datetime"):
        value = row.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _date_part(value: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text[:10].replace("/", "-")
    try:
        return dt.date.fromisoformat(candidate).isoformat()
    except ValueError:
        return None


def _news_on_or_before(rows: list[dict], trade_date: str) -> list[dict]:
    kept: list[dict] = []
    for row in rows:
        row_date = _date_part(_published_at(row))
        if row_date is not None and row_date <= trade_date:
            kept.append(row)
    return kept


def fetch(code: str, name: str, trade_date: str, cfg: dict, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    errors: list[str] = []
    raw_news: list[dict] = []

    if not cfg.get("sources", {}).get("enable_web_news", True):
        data = {
            "code": code,
            "name": name,
            "raw_news": [],
            "possible_catalyst": [],
            "verified_driver": [],
            "unsupported_rumor": [],
        }
        return layer_result(UNAVAILABLE, data, [])

    try:
        rows = _records(akshare_module.stock_news_em(symbol=code))
        raw_news = _news_on_or_before(rows, trade_date)[:30]
    except Exception as exc:
        errors.append(f"stock_news_em failed: {exc}")

    data = {
        "code": code,
        "name": name,
        "raw_news": raw_news,
        "possible_catalyst": raw_news[:10],
        "verified_driver": [],
        "unsupported_rumor": [],
    }
    if raw_news:
        return layer_result(PARTIAL if errors else OK, data, errors)
    return layer_result(UNAVAILABLE, data, errors)

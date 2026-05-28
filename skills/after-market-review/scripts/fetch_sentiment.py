from __future__ import annotations

from typing import Any

from lib.status import PARTIAL, UNAVAILABLE, layer_result


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _row_code(row: dict) -> str:
    for key in ("代码", "股票代码", "证券代码", "symbol", "code"):
        value = row.get(key)
        if value is not None:
            return str(value).strip().zfill(6)[-6:]
    return ""


def _filter_code(rows: list[dict], code: str) -> list[dict]:
    return [row for row in rows if _row_code(row) == code]


def fetch(code: str, trade_date: str, cfg: dict, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    sources = cfg.get("sources", {})
    enable_sentiment = bool(sources.get("enable_sentiment", True))
    enable_lhb = bool(sources.get("enable_lhb", True))
    errors: list[str] = []
    hot_rank: list[dict] = []
    hot_keyword: list[dict] = []
    lhb_daily: list[dict] = []

    if enable_sentiment:
        try:
            hot_rank = _filter_code(_records(akshare_module.stock_hot_rank_em()), code)
        except Exception as exc:
            errors.append(f"stock_hot_rank_em failed: {exc}")

        try:
            hot_keyword = _records(akshare_module.stock_hot_keyword_em(symbol=code))
        except Exception as exc:
            errors.append(f"stock_hot_keyword_em failed: {exc}")

    if enable_lhb:
        try:
            lhb_rows = _records(akshare_module.stock_lhb_detail_daily_sina(date=trade_date))
            lhb_daily = _filter_code(lhb_rows, code)
        except Exception as exc:
            errors.append(f"stock_lhb_detail_daily_sina failed: {exc}")

    data = {"hot_rank": hot_rank, "hot_keyword": hot_keyword, "lhb_daily": lhb_daily}
    status = PARTIAL if hot_rank or hot_keyword or lhb_daily else UNAVAILABLE
    return layer_result(status, data, errors)

from __future__ import annotations

from typing import Any

from lib.normalize import pct_change, to_float
from lib.status import OK, PARTIAL, layer_result


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _index_summary(rows: list[dict], code: str, name: str, trade_date: str) -> dict:
    usable = [
        row
        for row in rows
        if str(row.get("date") or row.get("日期"))[:10] <= trade_date
    ]
    if not usable:
        return {"code": code, "name": name, "status": "unavailable"}

    last = usable[-1]
    prev = usable[-2] if len(usable) >= 2 else {}
    close = to_float(last.get("close") or last.get("收盘"))
    prev_close = to_float(prev.get("close") or prev.get("收盘"))
    return {
        "code": code,
        "name": name,
        "date": str(last.get("date") or last.get("日期"))[:10],
        "close": close,
        "change_pct": pct_change(close, prev_close),
        "amount": to_float(last.get("amount") or last.get("成交额")),
        "volume": to_float(last.get("volume") or last.get("成交量")),
    }


def fetch(trade_date: str, cfg: dict, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    indices: list[dict] = []
    errors: list[str] = []
    for item in cfg.get("market_indices", []):
        code = item["code"]
        name = item["name"]
        try:
            rows = _records(
                akshare_module.stock_zh_index_daily_em(
                    symbol=code,
                    start_date="19900101",
                    end_date=trade_date.replace("-", ""),
                )
            )
            indices.append(_index_summary(rows, code, name, trade_date))
        except Exception as exc:
            errors.append(f"{code} failed: {exc}")

    status = PARTIAL if errors else OK
    return layer_result(status, {"indices": indices}, errors)

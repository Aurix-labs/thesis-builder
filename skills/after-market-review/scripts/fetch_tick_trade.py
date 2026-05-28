from __future__ import annotations

import datetime as dt
import math
from typing import Any

from lib.normalize import bucket_time, to_float
from lib.status import OK, PARTIAL, UNAVAILABLE, layer_result
from lib.stock_resolver import prefixed_code


def _kind_side(kind: Any) -> str:
    text = str(kind or "").strip()
    if text in {"U", "买盘", "B", "买"}:
        return "buy"
    if text in {"D", "卖盘", "S", "卖"}:
        return "sell"
    return "neutral"


def _row_time(row: dict) -> str:
    return str(row.get("ticktime") or row.get("成交时间") or row.get("时间") or "")[:8]


def _parse_time(time_text: str) -> dt.time | None:
    try:
        return dt.datetime.strptime(time_text[:8], "%H:%M:%S").time()
    except ValueError:
        return None


def _first_present(row: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _row_amount(row: dict) -> float:
    amount = to_float(_first_present(row, ("amount", "成交额")))
    if amount is not None:
        return amount

    price = to_float(_first_present(row, ("price", "成交价格", "成交价"))) or 0
    volume = to_float(_first_present(row, ("volume", "成交量", "手数"))) or 0
    if "volume" in row:
        return price * volume
    return price * volume * 100


def _filter_call_auction(rows: list[dict], include_call_auction: bool) -> list[dict]:
    if include_call_auction:
        return rows

    start = dt.time(hour=9, minute=30)
    end = dt.time(hour=14, minute=57)
    filtered: list[dict] = []
    for row in rows:
        parsed = _parse_time(_row_time(row))
        if parsed is not None and start <= parsed < end:
            filtered.append(row)
    return filtered


def analyze_tick_rows(rows: list[dict], cfg: dict) -> dict:
    filtered = _filter_call_auction(rows, bool(cfg.get("include_call_auction", True)))
    enriched: list[dict] = []

    for row in filtered:
        time_text = _row_time(row)
        amount = _row_amount(row)
        side = _kind_side(row.get("kind") or row.get("性质") or row.get("买卖盘性质"))
        if time_text and amount > 0:
            enriched.append({"time": time_text, "amount": amount, "side": side, "raw": row})

    if not enriched:
        return {
            "config": cfg,
            "summary": {
                "large_buy_count": 0,
                "large_sell_count": 0,
                "large_buy_amount": 0,
                "large_sell_amount": 0,
                "net_large_amount": 0,
                "peak_buy_windows": [],
                "peak_sell_windows": [],
                "tail_behavior": "无可用分笔数据",
            },
            "large_orders_sample": [],
        }

    amounts = [item["amount"] for item in enriched]
    quantile = float(cfg.get("top_quantile", 0.95))
    top_count = max(1, math.ceil(len(amounts) * (1 - quantile) - 1e-12))
    quantile_threshold = sorted(amounts, reverse=True)[top_count - 1]
    amount_min = float(cfg.get("amount_min", 1_000_000))
    large_orders = [
        item
        for item in enriched
        if item["amount"] >= amount_min or item["amount"] >= quantile_threshold
    ]

    buy_orders = [item for item in large_orders if item["side"] == "buy"]
    sell_orders = [item for item in large_orders if item["side"] == "sell"]
    buy_amount = round(sum(item["amount"] for item in buy_orders), 2)
    sell_amount = round(sum(item["amount"] for item in sell_orders), 2)

    window_minutes = int(cfg.get("window_minutes", 10))
    windows: dict[str, dict[str, float]] = {}
    for item in large_orders:
        key = bucket_time(item["time"], window_minutes)
        if key not in windows:
            windows[key] = {"buy": 0.0, "sell": 0.0}
        if item["side"] in {"buy", "sell"}:
            windows[key][item["side"]] += item["amount"]

    peak_buy_windows = [
        {"window": key, "amount": round(value["buy"], 2)}
        for key, value in sorted(windows.items())
        if value["buy"] > 0
    ]
    peak_sell_windows = [
        {"window": key, "amount": round(value["sell"], 2)}
        for key, value in sorted(windows.items())
        if value["sell"] > 0
    ]

    tail_buy = sum(
        item["amount"]
        for item in large_orders
        if item["time"] >= "14:50:00" and item["side"] == "buy"
    )
    tail_sell = sum(
        item["amount"]
        for item in large_orders
        if item["time"] >= "14:50:00" and item["side"] == "sell"
    )
    if tail_buy > tail_sell * 1.2 and tail_buy > 0:
        tail_behavior = "尾盘大单净买入"
    elif tail_sell > tail_buy * 1.2 and tail_sell > 0:
        tail_behavior = "尾盘大单净卖出"
    else:
        tail_behavior = "尾盘大单中性"

    return {
        "config": cfg,
        "summary": {
            "large_buy_count": len(buy_orders),
            "large_sell_count": len(sell_orders),
            "large_buy_amount": buy_amount,
            "large_sell_amount": sell_amount,
            "net_large_amount": round(buy_amount - sell_amount, 2),
            "peak_buy_windows": peak_buy_windows,
            "peak_sell_windows": peak_sell_windows,
            "tail_behavior": tail_behavior,
        },
        "large_orders_sample": [
            {"time": item["time"], "amount": round(item["amount"], 2), "side": item["side"]}
            for item in large_orders[:50]
        ],
    }


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def fetch(
    code: str,
    trade_date: str,
    cfg: dict,
    *,
    akshare_module=None,
    allow_latest_fallback: bool = False,
) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    errors: list[str] = []
    rows: list[dict] = []
    symbol = prefixed_code(code)

    try:
        df = akshare_module.stock_intraday_sina(
            symbol=symbol,
            date=trade_date.replace("-", ""),
        )
        rows = _records(df)
    except Exception as exc:
        errors.append(f"stock_intraday_sina failed: {exc}")

    if not rows and allow_latest_fallback:
        try:
            df = akshare_module.stock_zh_a_tick_tx_js(symbol=symbol)
            rows = _records(df)
        except Exception as exc:
            errors.append(f"stock_zh_a_tick_tx_js failed: {exc}")

    if not rows and not allow_latest_fallback:
        errors.append("latest-only fallback disabled for date safety")

    if not rows:
        return layer_result(UNAVAILABLE, {"summary": analyze_tick_rows([], cfg)["summary"]}, errors)

    status = PARTIAL if errors else OK
    return layer_result(status, analyze_tick_rows(rows, cfg), errors)

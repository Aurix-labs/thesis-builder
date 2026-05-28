from __future__ import annotations

from typing import Any

from lib.status import PARTIAL, UNAVAILABLE, layer_result
from lib.stock_resolver import detect_market


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _row_code(row: dict) -> str:
    for key in ("股票代码", "证券代码", "标的证券代码", "code", "股票代码"):
        value = row.get(key)
        if value is not None:
            return str(value).strip().zfill(6)[-6:]
    return ""


def _margin_method_name(market: str) -> str | None:
    if market == "sh":
        return "stock_margin_detail_sse"
    if market == "sz":
        return "stock_margin_detail_szse"
    return None


def fetch(code: str, trade_date: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    errors: list[str] = []
    fund_flow: list[dict] = []
    margin: list[dict] = []

    try:
        market = detect_market(code)
    except Exception as exc:
        return layer_result(
            UNAVAILABLE,
            {"market": None, "fund_flow": [], "margin": []},
            [f"detect_market failed: {exc}"],
        )

    try:
        fund_flow = _records(akshare_module.stock_individual_fund_flow(stock=code, market=market))
    except Exception as exc:
        errors.append(f"stock_individual_fund_flow failed: {exc}")

    margin_method_name = _margin_method_name(market)
    if margin_method_name is None:
        errors.append(f"margin detail unsupported for market: {market}")
    else:
        try:
            margin_method = getattr(akshare_module, margin_method_name)
            rows = _records(margin_method(date=trade_date.replace("-", "")))
            margin = [row for row in rows if _row_code(row) == code]
        except Exception as exc:
            errors.append(f"{margin_method_name} failed: {exc}")

    data = {"market": market, "fund_flow": fund_flow, "margin": margin}
    status = PARTIAL if fund_flow or margin else UNAVAILABLE
    return layer_result(status, data, errors)

from __future__ import annotations

from typing import Any

from lib.normalize import to_float
from lib.status import PARTIAL, UNAVAILABLE, layer_result


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _pick(row: dict, *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return None


def _industry_from_info(rows: list[dict]) -> str | None:
    for row in rows:
        item = str(row.get("item") or row.get("项目") or "").strip()
        if item in {"行业", "所属行业"}:
            value = str(row.get("value") or row.get("值") or "").strip()
            if value:
                return value
    return None


def _industry_name(row: dict) -> str:
    return str(_pick(row, "板块名称", "行业", "名称", "name") or "").strip()


def _industry_change(row: dict) -> float:
    value = to_float(_pick(row, "涨跌幅", "涨幅", "change_pct", "pct_change"))
    return value if value is not None else float("-inf")


def _rank_industry(rows: list[dict], industry: str | None) -> dict | None:
    if not industry:
        return None
    sorted_rows = sorted(rows, key=_industry_change, reverse=True)
    for index, row in enumerate(sorted_rows, start=1):
        if _industry_name(row) == industry:
            return {"industry": industry, "rank": index, "row": row}
    return None


def fetch(code: str, name: str, trade_date: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    errors: list[str] = []
    industry: str | None = None
    board_rows: list[dict] = []

    try:
        info_rows = _records(akshare_module.stock_individual_info_em(symbol=code))
        industry = _industry_from_info(info_rows)
    except Exception as exc:
        errors.append(f"stock_individual_info_em failed: {exc}")

    try:
        board_rows = _records(akshare_module.stock_board_industry_name_em())
    except Exception as exc:
        errors.append(f"stock_board_industry_name_em failed: {exc}")

    industry_rank = _rank_industry(board_rows, industry)
    data = {
        "code": code,
        "name": name,
        "trade_date": trade_date,
        "industry": industry,
        "industry_rank": industry_rank,
        "board_ranking": board_rows,
    }
    status = PARTIAL if industry or industry_rank else UNAVAILABLE
    return layer_result(status, data, errors)

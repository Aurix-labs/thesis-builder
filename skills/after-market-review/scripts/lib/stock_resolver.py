from __future__ import annotations

from pathlib import Path
from typing import Any


def detect_market(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688")):
        return "sh"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return "sz"
    if code.startswith(("430", "8", "920")):
        return "bj"
    raise ValueError(f"unsupported A-share code: {code}")


def prefixed_code(code: str) -> str:
    return f"{detect_market(code)}{code}"


def _records(df_or_rows: Any) -> list[dict]:
    if hasattr(df_or_rows, "to_dict"):
        return df_or_rows.to_dict(orient="records")
    return list(df_or_rows or [])


def _fetch_name(code: str, akshare_module: Any | None) -> str | None:
    if akshare_module is None:
        try:
            import akshare as akshare_module
        except Exception:
            return None
    try:
        rows = _records(akshare_module.stock_individual_info_em(symbol=code))
    except Exception:
        return None
    for row in rows:
        if row.get("item") in {"股票简称", "名称"}:
            value = str(row.get("value", "")).strip()
            return value or None
    return None


def resolve_from_output(code_or_name: str, output_root: Path) -> tuple[str, str, Path]:
    if code_or_name.isdigit() and len(code_or_name) == 6:
        code = code_or_name
        if output_root.exists():
            for sub in output_root.iterdir():
                if sub.is_dir() and sub.name.endswith(f"_{code}"):
                    return code, sub.name[: -(len(code) + 1)], sub
        return code, code, output_root / f"{code}_{code}"

    name = code_or_name
    if output_root.exists():
        for sub in output_root.iterdir():
            if sub.is_dir() and sub.name.startswith(f"{name}_"):
                code = sub.name.split("_", 1)[1]
                return code, name, sub
    raise ValueError(f"公司名 {name!r} 未在 output/ 下找到对应目录；请先用 6 位代码调用一次")


def resolve_stock(
    code_or_name: str,
    output_root: Path,
    akshare_module: Any | None = None,
) -> tuple[str, str, Path]:
    if code_or_name.isdigit() and len(code_or_name) == 6:
        code, name, stock_dir = resolve_from_output(code_or_name, output_root)
        if name == code:
            fetched = _fetch_name(code, akshare_module)
            if fetched:
                name = fetched
                stock_dir = output_root / f"{name}_{code}"
        return code, name, stock_dir
    return resolve_from_output(code_or_name, output_root)

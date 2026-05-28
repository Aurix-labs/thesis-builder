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


def _ambiguity_error(query: str, candidates: list[Path]) -> ValueError:
    candidate_names = ", ".join(sub.name for sub in candidates)
    return ValueError(
        f"ambiguous stock lookup for {query!r}: {candidate_names}; "
        "please use a 6-digit code"
    )


def _code_from_name_dir(dir_name: str, name: str) -> str | None:
    prefix = f"{name}_"
    if not dir_name.startswith(prefix):
        return None
    code = dir_name[len(prefix) :]
    if code.isdigit() and len(code) == 6:
        return code
    return None


def resolve_from_output(code_or_name: str, output_root: Path) -> tuple[str, str, Path]:
    if code_or_name.isdigit() and len(code_or_name) == 6:
        code = code_or_name
        if output_root.exists():
            matches = sorted(
                (
                    sub
                    for sub in output_root.iterdir()
                    if sub.is_dir() and sub.name.endswith(f"_{code}")
                ),
                key=lambda path: path.name,
            )
            if len(matches) > 1:
                raise _ambiguity_error(code, matches)
            if len(matches) == 1:
                sub = matches[0]
                return code, sub.name[: -(len(code) + 1)], sub
        return code, code, output_root / f"{code}_{code}"

    name = code_or_name
    if output_root.exists():
        matches = sorted(
            (
                sub
                for sub in output_root.iterdir()
                if sub.is_dir() and _code_from_name_dir(sub.name, name) is not None
            ),
            key=lambda path: path.name,
        )
        if len(matches) > 1:
            raise _ambiguity_error(name, matches)
        if len(matches) == 1:
            sub = matches[0]
            code = _code_from_name_dir(sub.name, name)
            if code is not None:
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

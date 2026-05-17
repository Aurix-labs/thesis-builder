"""akshare 接口当日缓存（按 ymd + func_name + args hash 去重）。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable


def _make_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """缓存键（稳定 hash）。"""
    payload = json.dumps(
        {"f": func_name, "a": list(args), "k": dict(sorted(kwargs.items()))},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _to_records(obj: Any) -> Any:
    """DataFrame → list-of-dicts；其他类型原样返回。"""
    if obj is None:
        return None
    if hasattr(obj, "to_dict") and hasattr(obj, "columns"):
        try:
            return obj.to_dict(orient="records")
        except Exception:
            return None
    return obj


def cached_call(
    stock_dir: Path,
    ymd: str,
    func_name: str,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """调用 func(*args, **kwargs)，结果按 (ymd, func_name, args hash) 缓存到 stock_dir/.cache/。

    Args:
        stock_dir: 股票目录（output/<股票名>_<代码>/）
        ymd: 缓存日（通常是 today）
        func_name: 用于缓存路径命名的函数名（人类可读）
        func: 实际调用的可调用对象（注入便于测试）
        *args, **kwargs: 传给 func 的参数
    Returns:
        函数返回值（DataFrame 已转 records）
    """
    cache_dir = stock_dir / ".cache" / ymd
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _make_cache_key(func_name, args, kwargs)
    cache_file = cache_dir / f"{func_name}_{key}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    raw = func(*args, **kwargs)
    result = _to_records(raw)
    cache_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return result

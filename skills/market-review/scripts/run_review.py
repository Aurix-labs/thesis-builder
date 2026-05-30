"""market-review 模块执行入口（数据层操作，不写 report.md）。

用法：
  python run_review.py [--force] [--module <m>] [--date <YYYY-MM-DD>]
输出（stdout）：
  每个模块一行 JSON，含 status (reuse/data_ready) + 路径
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Callable

from lib.config_loader import (
    REVIEW_MODULES, load_config, build_alias_map, resolve_module_name, get_ttl,
)
from lib.ttl_check import is_within_ttl

_FETCH_REGISTRY: dict[str, Callable] = {}


def _register_fetchers():
    global _FETCH_REGISTRY
    if _FETCH_REGISTRY:
        return
    from fetch_index import fetch as f_index
    from fetch_sentiment import fetch as f_sentiment
    from fetch_mainline import fetch as f_mainline
    from fetch_capital import fetch as f_capital
    from fetch_variables import fetch as f_variables
    from fetch_combatmap_data import fetch as f_combatmap
    _FETCH_REGISTRY = {
        "index": f_index,
        "sentiment": f_sentiment,
        "mainline": f_mainline,
        "capital": f_capital,
        "variables": f_variables,
        "combatmap": f_combatmap,
    }


def expand_modules(user_modules: list[str], config: dict) -> list[str]:
    """归一化别名 + 展开 review → 全部 6 个模块。返回有序清单。"""
    amap = build_alias_map(config)
    canonical = [resolve_module_name(m, amap) for m in user_modules]
    out: list[str] = []
    for m in canonical:
        if m == "review":
            for rm in REVIEW_MODULES:
                if rm not in out:
                    out.append(rm)
        else:
            if m not in out:
                out.append(m)
    # 确保 combatmap 在最后（依赖前五模块）
    if "combatmap" in out:
        out.remove("combatmap")
        out.append("combatmap")
    return out


def process_one(
    *,
    output_root: Path,
    module: str,
    today: str,
    force: bool,
    config: dict,
) -> dict[str, Any]:
    """处理一个模块。返回状态 dict。"""
    ttl = get_ttl(module, config)
    if ttl is None:
        raise ValueError(f"模块 {module} 无 TTL 配置")

    within, latest = is_within_ttl(output_root, module, today, ttl)
    if within and latest and not force:
        return {
            "module": module,
            "status": "reuse",
            "ymd": latest,
            "data_json": str(output_root / latest / module / "data.json"),
            "report_md": str(output_root / latest / module / "report.md"),
            "needs_report_md": False,
        }

    _register_fetchers()
    fn = _FETCH_REGISTRY[module]
    # combatmap 不需要 akshare 引用
    fn(output_root=output_root, today=today)

    ymd_dir = output_root / today / module
    return {
        "module": module,
        "status": "data_ready",
        "ymd": today,
        "data_json": str(ymd_dir / "data.json"),
        "report_md": str(ymd_dir / "report.md"),
        "needs_report_md": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_review.py",
        description="market-review 模块执行入口（数据层）",
    )
    p.add_argument("--force", action="store_true", help="覆盖 TTL，强制重跑")
    p.add_argument("--module", default="review", help="模块名/别名（默认 review=全部）")
    p.add_argument("--date", default=None, help="交易日（YYYY-MM-DD，默认今天）")
    p.add_argument("--output-dir", default="output", help="输出根目录（默认 ./output）")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    today = args.date or dt.date.today().isoformat()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    config = load_config()
    try:
        modules = expand_modules([args.module], config)
    except ValueError as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1

    errors = 0
    for m in modules:
        try:
            r = process_one(
                output_root=output_root,
                module=m,
                today=today,
                force=args.force,
                config=config,
            )
            print(json.dumps(r, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"module": m, "status": "error", "error": str(e)}, ensure_ascii=False))
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

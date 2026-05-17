"""agent 调用的唯一入口（数据层操作，不写 report.md）。

用法：
  python run_module.py <code_or_name> <module1> [<module2> ...] [--force]
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
    ANALYSIS_MODULES, load_config, build_alias_map, resolve_module_name, get_ttl,
)
from lib.module_io import get_latest_ymd
from lib.ttl_check import is_within_ttl


def expand_modules(user_modules: list[str], config: dict) -> list[str]:
    """归一化别名 + 展开 report → 7 个分析模块。返回去重后保序的清单。"""
    amap = build_alias_map(config)
    canonical = [resolve_module_name(m, amap) for m in user_modules]
    out: list[str] = []
    for m in canonical:
        if m == "report":
            for am in ANALYSIS_MODULES:
                if am not in out:
                    out.append(am)
        else:
            if m not in out:
                out.append(m)
    return out


_FETCH_REGISTRY: dict[str, Callable] = {}


def _register_fetchers():
    """惰性 import 所有 fetcher（避免 run_module 启动时全部 import akshare）。"""
    global _FETCH_REGISTRY
    if _FETCH_REGISTRY:
        return
    from fetch_chain import fetch as f_chain
    from fetch_rubric import fetch as f_rubric
    from fetch_elasticity import fetch as f_elasticity
    from fetch_risk import fetch as f_risk
    from fetch_valuation import fetch as f_valuation
    from fetch_flow_tech import fetch as f_flow_tech
    from fetch_peers import fetch as f_peers
    _FETCH_REGISTRY = {
        "chain": f_chain,
        "rubric": f_rubric,
        "elasticity": f_elasticity,
        "risk": f_risk,
        "valuation": f_valuation,
        "flow-tech": f_flow_tech,
        "peers": f_peers,
    }


def _default_dispatcher(module: str, code: str, name: str, stock_dir: Path, today: str) -> dict:
    _register_fetchers()
    fn = _FETCH_REGISTRY[module]
    return fn(code, name, stock_dir, today)


def process_one(
    *,
    code: str,
    name: str,
    stock_dir: Path,
    module: str,
    today: str,
    force: bool,
    config: dict,
    fetch_dispatcher: Callable = _default_dispatcher,
) -> dict[str, Any]:
    """处理一个模块。返回状态 dict。"""
    ttl = get_ttl(module, config)
    if ttl is None:
        raise ValueError(f"模块 {module} 无 TTL 配置（仅 report 是无 TTL 但 report 不应直接进入 process_one）")

    within, latest = is_within_ttl(stock_dir, module, today, ttl)
    if within and not force:
        return {
            "module": module,
            "status": "reuse",
            "ymd": latest,
            "report_md": str(stock_dir / module / latest / "report.md"),
            "data_json": str(stock_dir / module / latest / "data.json"),
            "needs_report_md": False,
        }

    # data_ready 路径
    fetch_dispatcher(module, code, name, stock_dir, today)
    return {
        "module": module,
        "status": "data_ready",
        "ymd": today,
        "data_json": str(stock_dir / module / today / "data.json"),
        "report_md": str(stock_dir / module / today / "report.md"),
        "needs_report_md": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_module.py",
        description="stock-analysis v4.0 模块执行入口（数据层）",
    )
    p.add_argument("code_or_name", help="6 位 A 股代码 或 公司中文简称")
    p.add_argument("modules", nargs="*", default=["report"], help="模块名/别名（默认 report）")
    p.add_argument("--force", action="store_true", help="覆盖 TTL，强制重跑")
    p.add_argument("--today", default=None, help="指定 today（YYYY-MM-DD，默认系统日期，主要供测试）")
    p.add_argument("--output-dir", default=None, help="输出根目录（默认 ./output）")
    return p.parse_args(argv)


def _resolve_stock(code_or_name: str, output_root: Path) -> tuple[str, str, Path]:
    """返回 (code, name, stock_dir)。
    code_or_name 是 6 位数字时按代码处理，否则当作公司名。
    优先在 output/ 下找已存在的 <name>_<code>/ 目录复用名称。
    """
    if code_or_name.isdigit() and len(code_or_name) == 6:
        code = code_or_name
        # 找现有目录
        name = None
        if output_root.exists():
            for sub in output_root.iterdir():
                if sub.is_dir() and sub.name.endswith(f"_{code}"):
                    name = sub.name[: -(len(code) + 1)]
                    break
        if name is None:
            # 用 akshare 拉名字
            try:
                import akshare as ak
                df = ak.stock_individual_info_em(symbol=code)
                if hasattr(df, "to_dict"):
                    rows = df.to_dict(orient="records")
                else:
                    rows = df or []
                for row in rows:
                    if row.get("item") in ("股票简称", "名称"):
                        name = str(row.get("value", "")).strip()
                        break
            except Exception as e:
                print(f"[!] fetch stock name failed: {e}", file=sys.stderr)
            if not name:
                name = code  # fallback
        return code, name, output_root / f"{name}_{code}"

    # 否则按公司名找
    name = code_or_name
    if output_root.exists():
        for sub in output_root.iterdir():
            if sub.is_dir() and sub.name.startswith(f"{name}_"):
                code = sub.name.split("_", 1)[1]
                return code, name, sub
    raise ValueError(f"公司名 {name!r} 未在 output/ 下找到对应目录；请先用 6 位代码调用一次以建立目录")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    today = args.today or dt.date.today().isoformat()
    output_root = Path(args.output_dir) if args.output_dir else Path.cwd() / "output"
    output_root.mkdir(parents=True, exist_ok=True)

    config = load_config()
    try:
        code, name, stock_dir = _resolve_stock(args.code_or_name, output_root)
        modules = expand_modules(args.modules, config)
    except ValueError as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1

    for m in modules:
        try:
            r = process_one(
                code=code, name=name, stock_dir=stock_dir,
                module=m, today=today, force=args.force, config=config,
            )
            print(json.dumps(r, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"module": m, "status": "error", "error": str(e)}, ensure_ascii=False))
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

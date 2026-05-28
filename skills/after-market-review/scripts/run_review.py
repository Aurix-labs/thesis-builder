from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from lib.config_loader import load_config
from lib.io import has_existing_report, review_dir, write_json
from lib.status import ERROR, VALID_STATUSES
from lib.stock_resolver import resolve_stock


LAYERS = [
    "market_context",
    "sector_context",
    "stock_trade",
    "tick_trade",
    "funds_context",
    "event_context",
    "sentiment_context",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_review.py")
    parser.add_argument("code_or_name")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--today", default=None)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args(argv)


def build_artifacts(
    code: str,
    name: str,
    trade_date: str,
    force: bool,
    layers: dict[str, dict],
) -> tuple[dict, dict]:
    data_status: dict[str, str] = {}
    data: dict[str, Any] = {
        "skill": "after-market-review",
        "code": code,
        "name": name,
        "trade_date": trade_date,
        "generated_at": dt.datetime.now(
            dt.timezone(dt.timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "data_status": data_status,
        "derived": {},
    }
    errors: list[dict[str, str]] = []
    sources: list[dict[str, str]] = []

    for layer in LAYERS:
        result = layers.get(
            layer,
            {"status": ERROR, "data": {}, "errors": [f"{layer} did not run"]},
        )
        status = result.get("status", ERROR)
        if status not in VALID_STATUSES:
            status = ERROR
        data_status[layer] = status
        data[layer] = result.get("data", {})
        sources.append({"layer": layer, "status": status})
        for message in result.get("errors", []):
            errors.append({"layer": layer, "message": str(message)})

    stock_trade = data.get("stock_trade", {})
    sector_context = data.get("sector_context", {})
    data["derived"] = {
        "intraday_pattern": stock_trade.get("intraday_pattern", "交易节奏未识别"),
        "relative_strength": sector_context.get("relative_strength", "相对强弱未识别"),
        "volume_price_signal": "等待报告层综合判断",
        "event_match_level": "unknown",
        "sentiment_heat": "unknown",
    }

    manifest = {
        "skill": "after-market-review",
        "code": code,
        "name": name,
        "trade_date": trade_date,
        "force": force,
        "sources": sources,
        "errors": errors,
        "generated_files": ["data.json", "manifest.json"],
    }
    return data, manifest


def _print(obj: dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def _import_fetchers() -> dict[str, Any]:
    import fetch_events
    import fetch_funds
    import fetch_market
    import fetch_sector
    import fetch_sentiment
    import fetch_stock_trade
    import fetch_tick_trade

    return {
        "events": fetch_events,
        "funds": fetch_funds,
        "market": fetch_market,
        "sector": fetch_sector,
        "sentiment": fetch_sentiment,
        "stock_trade": fetch_stock_trade,
        "tick_trade": fetch_tick_trade,
    }


def _default_output_root() -> Path:
    return Path(__file__).resolve().parents[2] / "output"


def _print_reuse(code: str, name: str, trade_date: str, out_dir: Path) -> None:
    _print(
        {
            "status": "reuse",
            "code": code,
            "name": name,
            "trade_date": trade_date,
            "report_md": str(out_dir / "report.md"),
            "data_json": str(out_dir / "data.json"),
            "manifest_json": str(out_dir / "manifest.json"),
        }
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config()
    today = args.today or dt.date.today().isoformat()
    output_root = Path(args.output_dir) if args.output_dir else _default_output_root()

    code, name, stock_dir = resolve_stock(args.code_or_name, output_root)

    cached_dir = review_dir(stock_dir, today)
    reuse_cache = bool(cfg.get("cache", {}).get("reuse_existing_report", True))
    if reuse_cache and not args.force and has_existing_report(cached_dir):
        _print_reuse(code, name, today, cached_dir)
        return 0

    fetchers = _import_fetchers()
    stock_trade = fetchers["stock_trade"].fetch(code, today)
    if stock_trade.get("status") == ERROR:
        out_dir = review_dir(stock_dir, today)
        data, manifest = build_artifacts(
            code,
            name,
            today,
            args.force,
            {"stock_trade": stock_trade},
        )
        write_json(out_dir / "data.json", data)
        write_json(out_dir / "manifest.json", manifest)
        _print(
            {
                "status": "error",
                "error": "stock_trade failed",
                "manifest_json": str(out_dir / "manifest.json"),
            }
        )
        return 1

    trade_date = stock_trade.get("data", {}).get("trade_date", today)
    out_dir = review_dir(stock_dir, trade_date)
    if reuse_cache and not args.force and has_existing_report(out_dir):
        _print_reuse(code, name, trade_date, out_dir)
        return 0

    layers = {
        "stock_trade": stock_trade,
        "market_context": fetchers["market"].fetch(trade_date, cfg),
        "sector_context": fetchers["sector"].fetch(code, name, trade_date),
        "tick_trade": fetchers["tick_trade"].fetch(code, trade_date, cfg["large_order"]),
        "funds_context": fetchers["funds"].fetch(code, trade_date),
        "event_context": fetchers["events"].fetch(code, name, trade_date, cfg),
        "sentiment_context": fetchers["sentiment"].fetch(code, trade_date, cfg),
    }
    data, manifest = build_artifacts(code, name, trade_date, args.force, layers)
    write_json(out_dir / "data.json", data)
    write_json(out_dir / "manifest.json", manifest)
    _print(
        {
            "status": "data_ready",
            "code": code,
            "name": name,
            "trade_date": trade_date,
            "data_json": str(out_dir / "data.json"),
            "manifest_json": str(out_dir / "manifest.json"),
            "report_md": str(out_dir / "report.md"),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

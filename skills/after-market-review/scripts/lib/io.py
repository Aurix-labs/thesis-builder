from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def stock_output_dir(output_root: Path, name: str, code: str) -> Path:
    return output_root / f"{name}_{code}"


def review_dir(stock_dir: Path, trade_date: str) -> Path:
    return stock_dir / "after-market-review" / trade_date


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return obj


def has_existing_report(path: Path) -> bool:
    report = path / "report.md"
    return report.exists() and report.stat().st_size > 0

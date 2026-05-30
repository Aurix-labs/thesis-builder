"""模块数据读写 + latest 软链管理。"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any


class _MarketEncoder(json.JSONEncoder):
    """处理 akshare 返回的 date/datetime/Timestamp 等不可序列化类型。"""

    def default(self, obj):
        if isinstance(obj, (dt.datetime, dt.date)):
            return obj.isoformat()
        # pandas Timestamp
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        # numpy types
        if hasattr(obj, "item"):
            return obj.item()
        return super().default(obj)


def _sanitize(obj: Any) -> Any:
    """递归替换 NaN/Infinity 为 None，确保产出合法 JSON。"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _to_json(data: dict) -> str:
    return json.dumps(_sanitize(data), ensure_ascii=False, indent=2, cls=_MarketEncoder)


def write_module_data(output_root: Path, module: str, ymd: str, data: dict) -> Path:
    ymd_dir = output_root / ymd / module
    ymd_dir.mkdir(parents=True, exist_ok=True)
    (ymd_dir / "data.json").write_text(
        _to_json(data),
        encoding="utf-8",
    )
    update_latest_symlink(output_root / ymd, module)
    return ymd_dir


def read_module_data(output_root: Path, ymd: str, module: str) -> dict:
    path = output_root / ymd / module / "data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_latest_ymd(output_root: Path, module: str) -> str | None:
    """在所有 ymd 目录中找包含此模块 latest 软链的最新日期。"""
    if not output_root.exists():
        return None
    best = None
    for child in sorted(output_root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        latest = child / module / "latest"
        if latest.is_symlink():
            target = latest.readlink()
            target_abs = (latest.parent / target) if not target.is_absolute() else target
            if target_abs.exists():
                best = child.name
                break
    return best


def update_latest_symlink(ymd_dir: Path, module: str) -> None:
    """在 <ymd_dir>/<module>/ 下创建 latest -> <ymd_dir.name> 软链。"""
    module_dir = ymd_dir / module
    module_dir.mkdir(parents=True, exist_ok=True)
    latest = module_dir / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(ymd_dir.name, target_is_directory=True)

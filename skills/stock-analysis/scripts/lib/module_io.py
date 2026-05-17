"""模块数据读写 + latest 软链管理 + 标的速写渲染。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


THESIS_SNAPSHOT_START = "<!-- THESIS_SNAPSHOT_START -->"
THESIS_SNAPSHOT_END = "<!-- THESIS_SNAPSHOT_END -->"


def write_module_data(stock_dir: Path, module: str, ymd: str, data: dict) -> Path:
    """写 <stock_dir>/<module>/<ymd>/data.json 并更新 latest 软链。返回 ymd 目录路径。"""
    ymd_dir = stock_dir / module / ymd
    ymd_dir.mkdir(parents=True, exist_ok=True)
    (ymd_dir / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    update_latest_symlink(stock_dir / module, ymd)
    return ymd_dir


def read_module_data(stock_dir: Path, module: str, ymd: str | None = None) -> dict:
    """读 data.json。ymd=None 时跟 latest 软链。"""
    if ymd is None:
        ymd = get_latest_ymd(stock_dir, module)
        if ymd is None:
            raise FileNotFoundError(f"模块 {module} 在 {stock_dir} 下无任何快照")
    path = stock_dir / module / ymd / "data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_latest_ymd(stock_dir: Path, module: str) -> str | None:
    """返回 latest 软链指向的 ymd 字符串，不存在返回 None。"""
    latest = stock_dir / module / "latest"
    if not latest.is_symlink() and not latest.exists():
        return None
    target = latest.readlink() if latest.is_symlink() else None
    if target is None:
        return None
    return target.name


def update_latest_symlink(module_dir: Path, ymd: str) -> None:
    """强制设 <module_dir>/latest -> <ymd>。"""
    module_dir.mkdir(parents=True, exist_ok=True)
    latest = module_dir / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(ymd, target_is_directory=True)


def render_thesis_snapshot(meta: dict[str, Any], quote: dict[str, Any], core_thesis: str = "") -> str:
    """渲染标的速写段（5-10 行），用 marker 包裹。"""
    name = meta.get("name", "?")
    code = meta.get("code", "?")
    industry = meta.get("industry", "?")
    price = quote.get("price", "?")
    market_cap = quote.get("market_cap", 0)
    pe = quote.get("pe", "?")
    pb = quote.get("pb", "?")
    if isinstance(market_cap, (int, float)) and market_cap > 0:
        mc_str = f"{market_cap / 1e8:.1f} 亿"
    else:
        mc_str = "?"
    thesis_line = f"- 核心矛盾：{core_thesis}" if core_thesis else "- 核心矛盾：[I: 待 chain 模块输出]"

    return "\n".join([
        THESIS_SNAPSHOT_START,
        "## 标的速写",
        f"- **{name}（{code}）** · {industry}",
        f"- 现价：{price} | 市值：{mc_str} | PE：{pe} | PB：{pb}",
        thesis_line,
        THESIS_SNAPSHOT_END,
        "",
    ])

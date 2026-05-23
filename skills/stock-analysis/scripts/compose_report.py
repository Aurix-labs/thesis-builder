"""合成层：合并 7 个模块的 latest report.md → report/<today>/report.md。

用法：
  python compose_report.py <code_or_name> [--today YYYY-MM-DD]
输出（stdout）：
  JSON {"merged_report_md": "...", "manifest": "...", "pending": [...]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path

from lib.config_loader import ANALYSIS_MODULES
from lib.module_io import THESIS_SNAPSHOT_START, THESIS_SNAPSHOT_END, get_latest_ymd, read_module_data


_SNAPSHOT_RE = re.compile(
    re.escape(THESIS_SNAPSHOT_START) + r".*?" + re.escape(THESIS_SNAPSHOT_END) + r"\n?",
    re.DOTALL,
)


def dedupe_thesis_snapshots(md: str) -> str:
    """保留第一段 THESIS_SNAPSHOT，其余整段删除。"""
    matches = list(_SNAPSHOT_RE.finditer(md))
    if len(matches) <= 1:
        return md
    keep = matches[0]
    # 倒序删除剩余段，避免下标偏移
    out = md
    for m in reversed(matches[1:]):
        out = out[: m.start()] + out[m.end() :]
    return out


def _module_to_namespace(module: str) -> str:
    """模块名 → data.json 顶层 namespace（连字符转下划线）。"""
    return module.replace("-", "_")


def _has_history_reports(stock_dir: Path, today: str) -> bool:
    """是否存在 report/<ymd>/ 历史快照（不含 today）。"""
    report_root = stock_dir / "report"
    if not report_root.exists():
        return False
    for sub in report_root.iterdir():
        if sub.is_dir() and sub.name != today and (sub / "report.md").exists():
            return True
    return False


def merge_data_json(
    stock_dir: Path,
    today: str,
    stock_code: str = "",
    stock_name: str = "",
) -> dict:
    """合并 7 个模块的 latest data.json + 注入 meta。返回合并后的 dict。"""
    merged: dict = {"meta": {}}
    ymds: list[str] = []
    for m in ANALYSIS_MODULES:
        latest_ymd = get_latest_ymd(stock_dir, m)
        if latest_ymd is None:
            raise FileNotFoundError(f"模块 {m} 没有 latest 快照，无法合并 data.json")
        d = read_module_data(stock_dir, m, latest_ymd)
        ns = _module_to_namespace(m)
        merged[ns] = d
        ymds.append(latest_ymd)

    now = dt.datetime.now()
    merged["meta"] = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "stock_dir": stock_dir.name,
        "ymd": today,
        "time_utc8": now.strftime("%H:%M"),
        "session_id": "0x" + uuid.uuid4().hex[:4],
        "data_as_of": max(ymds),
        "research_status": "持续跟踪" if _has_history_reports(stock_dir, today) else "首次覆盖",
    }
    return merged


def compose(stock_dir: Path, today: str, stock_code: str = "", stock_name: str = "") -> dict:
    """合并 7 个模块的 latest report.md。"""
    report_dir = stock_dir / "report" / today
    report_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"today": today, "modules": {}}
    bodies: list[str] = []
    for m in ANALYSIS_MODULES:
        latest_ymd = get_latest_ymd(stock_dir, m)
        if latest_ymd is None:
            raise FileNotFoundError(f"模块 {m} 没有 latest 快照，无法合成 report")
        md_path = stock_dir / m / latest_ymd / "report.md"
        if not md_path.exists():
            raise FileNotFoundError(f"模块 {m} 的 report.md 不存在：{md_path}")
        manifest["modules"][m] = {"ymd": latest_ymd, "path": str(md_path)}
        bodies.append(md_path.read_text(encoding="utf-8"))

    merged = "\n\n".join(bodies)
    merged = dedupe_thesis_snapshots(merged)
    merged_path = report_dir / "report.md"
    merged_path.write_text(merged, encoding="utf-8")

    manifest_path = report_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    merged_data = merge_data_json(stock_dir, today, stock_code=stock_code, stock_name=stock_name)
    data_path = report_dir / "data.json"
    data_path.write_text(json.dumps(merged_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "merged_report_md": str(merged_path),
        "merged_data_json": str(data_path),
        "manifest": str(manifest_path),
        "pending": ["step_0_task_lock", "step_8_conclusion", "bear_case", "fact_check", "html"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="compose_report.py")
    p.add_argument("code_or_name")
    p.add_argument("--today", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    today = args.today or dt.date.today().isoformat()
    output_root = Path(args.output_dir) if args.output_dir else Path.cwd() / "output"

    from run_module import _resolve_stock
    try:
        _code, _name, stock_dir = _resolve_stock(args.code_or_name, output_root)
        result = compose(stock_dir, today, stock_code=_code, stock_name=_name)
    except (FileNotFoundError, ValueError) as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

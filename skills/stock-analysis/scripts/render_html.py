"""HTML 渲染器 v5。

输入：output/<stock>/report/<ymd>/{data.json, report.md, bear-case.md?, fact-check.md?}
输出：output/<stock>/report/<ymd>/report.html

用法：
    python render_html.py <stock> <ymd> [--dry-run] [--fixed-meta '{"session_id":"0xtest",...}']
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib.md_renderer import MdRenderer, split_report_sections
from lib.render_schema import RenderError, validate_schema


SKILL_ROOT = Path(__file__).resolve().parent.parent  # skills/stock-analysis/
TEMPLATE_DIR = SKILL_ROOT / "templates"


def _build_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    return env


def _extract_kline_summary(kline_daily: list) -> dict:
    """从 fetch 原始 kline 行（date, open, close, low, high, vol）抽取统计。"""
    highs = [row[4] for row in kline_daily]
    lows = [row[3] for row in kline_daily]
    last_close = kline_daily[-1][2]
    return {
        "high": max(highs),
        "low": min(lows),
        "last_close": last_close,
    }


def _kline_to_echarts(kline_daily: list) -> list:
    """fetch 原始 [date, open, close, low, high, vol] → ECharts [open, close, low, high]。"""
    return [[row[1], row[2], row[3], row[4]] for row in kline_daily]


def _build_sparkline(kline_daily: list, n: int = 30) -> tuple[list, str, float]:
    """从 kline 末尾抽 n 个收盘价。返回 (closes, direction, pct_change)。"""
    closes = [row[2] for row in kline_daily[-n:]]
    if not closes:
        return [], "up", 0.0
    pct = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] else 0.0
    direction = "up" if pct >= 0 else "down"
    return closes, direction, pct


def _read_optional(path: Path) -> str:
    """读可选文件，不存在返回空串。"""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _inject_meta(data: dict, fixed_meta: Optional[dict]) -> None:
    """合并 fixed_meta 到 data['meta']（用于测试固定 session_id/time）。"""
    if fixed_meta is None:
        return
    data.setdefault("meta", {})
    data["meta"].update(fixed_meta)


def render(stock_dir: Path, ymd: str, fixed_meta: Optional[dict] = None, dry_run: bool = False) -> Optional[Path]:
    """渲染 report.html。fail-hard。

    stock_dir: output/<stock>/   （含 report/<ymd>/ 子目录）
    ymd: YYYY-MM-DD
    fixed_meta: 测试用，注入固定 session_id/time_utc8
    dry_run: 只跑 schema + 切段，不写 HTML，返回 None
    """
    report_dir = stock_dir / "report" / ymd
    if not report_dir.exists():
        raise RenderError(f"report 目录不存在：{report_dir}")

    data_path = report_dir / "data.json"
    md_path = report_dir / "report.md"
    bear_path = report_dir / "bear-case.md"

    if not data_path.exists():
        raise RenderError(f"data.json 不存在：{data_path}")
    if not md_path.exists():
        raise RenderError(f"report.md 不存在：{md_path}")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    _inject_meta(data, fixed_meta)
    validate_schema(data)

    md_text = md_path.read_text(encoding="utf-8")
    sections = split_report_sections(md_text)

    if dry_run:
        return None

    bear_md = _read_optional(bear_path)
    md_renderer = MdRenderer()
    bear_case_html = md_renderer.render(bear_md) if bear_md else ""

    # 派生展示字段
    closes, direction, pct = _build_sparkline(data["flow_tech"]["kline_daily"])
    kline_stats = _extract_kline_summary(data["flow_tech"]["kline_daily"])
    kline_echarts_data = _kline_to_echarts(data["flow_tech"]["kline_daily"])
    pie_data = [
        {"name": item["name"], "value": item["value"]}
        for item in data["rubric"]["summary"]["revenue_breakdown"]
    ]

    # 静态展示字段（chain.summary 提供 thesis；公司画像/近期动态走 chain fetch 原料的轻量化抽取）
    chain_summary = data.get("chain", {}).get("summary", {})
    company_profile_text = chain_summary.get(
        "company_profile",
        f"{data['meta']['stock_name']}（{data['meta']['stock_code']}）—— 见任务卡。",
    )
    recent_news = chain_summary.get("recent_news", [])

    env = _build_jinja_env()
    # markdown 渲染作为 Jinja2 全局函数暴露
    env.globals["md_to_html"] = md_renderer.render

    template = env.get_template("report.html.j2")
    html = template.render(
        meta=data["meta"],
        chain=data["chain"],
        rubric=data["rubric"],
        elasticity=data["elasticity"],
        risk=data["risk"],
        valuation=data["valuation"],
        flow_tech=data["flow_tech"],
        peers=data["peers"],
        sections=sections,
        bear_case_html=bear_case_html,
        sparkline_points=closes,
        sparkline_direction=direction,
        sparkline_pct=pct,
        kline_stats=kline_stats,
        kline_echarts_data=kline_echarts_data,
        pie_data=pie_data,
        hero_lead=chain_summary.get("thesis_one_liner", ""),
        company_profile_text=company_profile_text,
        recent_news=recent_news,
        final_conclusion=chain_summary.get("final_conclusion", "见 #tracking 卡。"),
    )

    out = report_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def _resolve_stock_dir(code_or_name: str, output_root: Path) -> Path:
    """同 run_module/compose_report 风格：用 code 或 name 找 output/<dir>。"""
    code_or_name = code_or_name.strip()
    if not output_root.exists():
        raise RenderError(f"output 根目录不存在：{output_root}")
    candidates = [d for d in output_root.iterdir() if d.is_dir()]
    for c in candidates:
        if c.name.endswith(f"_{code_or_name}") or c.name == code_or_name or code_or_name in c.name:
            return c
    raise RenderError(f"未找到 {code_or_name} 对应的 output 目录")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="render_html.py")
    p.add_argument("code_or_name")
    p.add_argument("ymd", help="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fixed-meta", default=None, help='JSON 字符串：{"session_id":"0xtest","time_utc8":"00:00"}')
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_root = Path(args.output_dir) if args.output_dir else Path.cwd() / "output"
    fixed_meta = json.loads(args.fixed_meta) if args.fixed_meta else None
    try:
        stock_dir = _resolve_stock_dir(args.code_or_name, output_root)
        result = render(stock_dir, args.ymd, fixed_meta=fixed_meta, dry_run=args.dry_run)
    except (RenderError, FileNotFoundError) as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1
    if result is not None:
        print(json.dumps({"report_html": str(result)}, ensure_ascii=False))
    else:
        print(json.dumps({"dry_run": "passed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

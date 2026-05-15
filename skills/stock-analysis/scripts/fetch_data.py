"""
个股数据采集脚本（Phase 1 参考实现）
====================================
- 默认数据源：akshare
- 输出：output/<股票名>_<代码>/<YYYY-MM-DD>/data.json
- 同时维护 output/<股票名>_<代码>/latest 软链指向最新日期

用法：
  python fetch_data.py 002594
  python fetch_data.py 002594 --date 2026-04-22
  python fetch_data.py 002594 --output-dir /tmp/research
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ============================================================
#  路径与 CLI 模块（pure / 可测试，不依赖网络）
# ============================================================

def detect_market(code: str) -> tuple[str, str]:
    """返回 (prefixed, market)，如 ('sh600519','sh')。"""
    code = code.strip().lstrip("sh").lstrip("sz").lstrip("bj")
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"非法的 A 股代码：{code}")
    if code.startswith(("60", "68", "11", "12", "5")):
        return f"sh{code}", "sh"
    if code.startswith(("00", "30", "20", "15", "16", "18")):
        return f"sz{code}", "sz"
    if code.startswith(("4", "8", "92")):
        return f"bj{code}", "bj"
    return f"sh{code}", "sh"


def resolve_default_output_root() -> Path:
    """默认输出根目录：用户当前工作目录下的 output/。
    用户可以在 thesis-builder/ 仓库根跑，得到 thesis-builder/output/...
    """
    return Path.cwd() / "output"


def build_output_dir(
    root: Path,
    name: str,
    code: str,
    date: str,
    create: bool = False,
) -> Path:
    """构造 <root>/<name>_<code>/<date>/，create=True 时同时创建并更新 latest 软链。"""
    stock_dir = root / f"{name}_{code}"
    date_dir = stock_dir / date
    if create:
        date_dir.mkdir(parents=True, exist_ok=True)
        latest = stock_dir / "latest"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(date, target_is_directory=True)
    return date_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="fetch_data.py",
        description="A 股个股数据采集（Phase 1）",
    )
    p.add_argument("code", help="6 位 A 股代码（如 002594）")
    p.add_argument("--date", help="数据截止日 YYYY-MM-DD（默认今日）", default=None)
    p.add_argument("--output-dir", help="输出根目录（默认 ./output）", default=None)
    p.add_argument("--max-kline-years", type=int, default=3, help="K 线年限（默认 3）")
    return p.parse_args(argv)


import traceback
from typing import Callable

try:
    import pandas as pd  # type: ignore
except ImportError:
    print("[X] 未安装 pandas，请先 pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

try:
    import akshare as ak  # type: ignore
except ImportError:
    print("[X] 未安装 akshare，请先 pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def _last_trade_day(d: dt.date) -> dt.date:
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def _filter_by_code(df, code: str):
    """按代码列过滤行；找不到代码列则原样返回。"""
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()
    candidate = ["代码", "股票代码", "证券代码", "symbol", "code"]
    col = next((c for c in candidate if c in df.columns), None)
    if col is None:
        return df
    s = df[col].astype(str).str.strip()
    return df[(s == code) | s.str.endswith(code)].reset_index(drop=True)


def _df_to_records(df) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


def _safe_call(fn: Callable, *args, label: str = "", **kwargs):
    """调 akshare 接口，失败返回 None 且打 warning，不中断。"""
    try:
        result = fn(*args, **kwargs)
        if label:
            n = len(result) if hasattr(result, "__len__") else 0
            print(f"  · {label}: {n} 行")
        return result
    except Exception as e:
        print(f"  · {label}: 失败（{type(e).__name__}: {e}）", file=sys.stderr)
        return None


# ============================================================
#  akshare 数据采集（有网络副作用，Task 9 实现）
# ============================================================

def collect_blocks(code: str, max_kline_years: int = 3) -> dict[str, Any]:
    """采集 akshare 全维度数据。返回 dict，key 为 block 名（kline/financial/holder/...）。"""
    prefixed, market = detect_market(code)
    blocks: dict[str, Any] = {}

    today = dt.date.today()
    today_s = today.strftime("%Y%m%d")
    last_trade_prev = _last_trade_day(today)
    last_trade_prev_s = last_trade_prev.strftime("%Y%m%d")

    # 基本信息
    print("[1/13] 基本信息")
    df = _safe_call(ak.stock_individual_info_em, symbol=code, label="个股信息")
    blocks["info"] = _df_to_records(df)

    # K 线
    print(f"[2/13] 日 K 线（{max_kline_years} 年）")
    start = (today - dt.timedelta(days=int(max_kline_years * 365))).strftime("%Y%m%d")
    df = _safe_call(
        ak.stock_zh_a_hist,
        symbol=code,
        period="daily",
        start_date=start,
        end_date=today_s,
        adjust="qfq",
        label=f"日 K（前复权 {start}~{today_s}）",
    )
    blocks["kline_daily"] = _df_to_records(df)

    # 主营业务
    print("[3/13] 主营业务构成")
    df = _safe_call(ak.stock_zygc_em, symbol=prefixed, label="主营构成")
    blocks["business"] = _df_to_records(df)

    # 财务摘要
    print("[4/13] 财务摘要")
    df = _safe_call(ak.stock_financial_abstract, symbol=code, label="财务摘要")
    blocks["financial_abstract"] = _df_to_records(df)

    # 股东
    print("[5/13] 十大股东")
    df = _safe_call(ak.stock_gdfx_top_10_em, symbol=prefixed, date=last_trade_prev_s, label="十大股东")
    blocks["top_holders"] = _df_to_records(df)

    # 资金流向
    print("[6/13] 资金流向（个股）")
    df = _safe_call(ak.stock_individual_fund_flow, stock=code, market=market, label="资金流向")
    blocks["fund_flow"] = _df_to_records(df)

    # 公告
    print("[7/13] 公告")
    df = _safe_call(ak.stock_notice_report, symbol="全部", date=today_s, label=f"当日公告({today_s})")
    blocks["notice"] = _df_to_records(_filter_by_code(df, code))

    # 新闻
    print("[8/13] 个股新闻")
    df = _safe_call(ak.stock_news_em, symbol=code, label="个股新闻")
    blocks["news"] = _df_to_records(df)

    # 研报
    print("[9/13] 研究报告")
    df = _safe_call(ak.stock_research_report_em, symbol=code, label="研报")
    blocks["research"] = _df_to_records(df)

    # 机构推荐
    print("[10/13] 机构推荐评级")
    df = _safe_call(ak.stock_institute_recommend, symbol="股票综合评级", label="机构推荐")
    blocks["recommend"] = _df_to_records(_filter_by_code(df, code))

    # 业绩预告
    print("[11/13] 业绩预告")
    df = _safe_call(ak.stock_yjbb_em, date=last_trade_prev_s, label=f"业绩预告({last_trade_prev_s})")
    blocks["earnings_forecast"] = _df_to_records(_filter_by_code(df, code))

    # 融资融券
    print("[12/13] 融资融券")
    if market == "sh":
        df = _safe_call(ak.stock_margin_detail_sse, date=last_trade_prev_s, label="上交所融资融券")
    else:
        df = _safe_call(ak.stock_margin_detail_szse, date=last_trade_prev_s, label="深交所融资融券")
    blocks["margin"] = _df_to_records(_filter_by_code(df, code))

    # 行情快照
    print("[13/13] 实时行情")
    df = _safe_call(ak.stock_zh_a_spot_em, label="A 股实时行情")
    blocks["quote_snapshot"] = _df_to_records(_filter_by_code(df, code))

    return blocks


def fetch_stock_name(code: str) -> str:
    """通过 akshare 获取股票中文简称。失败时返回代码本身作为 fallback。"""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        if df is None or df.empty:
            return code
        row = df[df["item"] == "股票简称"]
        if not row.empty:
            return str(row.iloc[0]["value"]).strip()
        row = df[df["item"] == "名称"]
        if not row.empty:
            return str(row.iloc[0]["value"]).strip()
    except Exception as e:
        print(f"[!] fetch_stock_name 失败：{e}", file=sys.stderr)
    return code


# ============================================================
#  CLI 入口
# ============================================================

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        prefixed, market = detect_market(args.code)
    except ValueError as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1

    date_str = args.date or dt.date.today().isoformat()
    root = Path(args.output_dir) if args.output_dir else resolve_default_output_root()

    print(f"📊 采集 {args.code}（{prefixed}, {market.upper()}）数据 · as_of={date_str}")
    try:
        name = fetch_stock_name(args.code)
        blocks = collect_blocks(args.code, max_kline_years=args.max_kline_years)
    except NotImplementedError:
        print("[!] akshare 采集尚未实现（待 Task 9）", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[X] 采集失败：{e}", file=sys.stderr)
        return 1

    out_dir = build_output_dir(root, name=name, code=args.code, date=date_str, create=True)
    payload = {
        "meta": {
            "code": args.code,
            "name": name,
            "exchange": market.upper(),
            "as_of": date_str,
            "source": "akshare",
        },
        "blocks": blocks,
    }
    json_path = out_dir / "data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str)
    print(f"✅ 已保存：{json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

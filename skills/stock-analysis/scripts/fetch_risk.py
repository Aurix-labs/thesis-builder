"""M4 risk · 风险与止损 数据采集 + 异常扫描。

字段：meta、quote、financial_abstract、kline_daily、notice、news
额外产物：<ymd>/anomalies.md + anomalies.json
覆盖 Step 5 风险清单 + Step 0.5 核心异常分析
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from lib.scan_anomalies import scan_financial, render_md
from fetch_chain import _extract_meta, _extract_quote


MODULE_NAME = "risk"
FIELDS = ["meta", "quote", "financial_abstract", "kline_daily", "notice", "news"]


def _filter_by_code(records: list[dict], code: str) -> list[dict]:
    if not records:
        return []
    out = []
    for r in records:
        for col in ("代码", "股票代码", "证券代码"):
            v = str(r.get(col, "")).strip()
            if v == code or v.endswith(code):
                out.append(r)
                break
    return out


def fetch(code: str, name: str, stock_dir: Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    today_d = dt.date.fromisoformat(today)
    today_s = today_d.strftime("%Y%m%d")
    start_s = (today_d - dt.timedelta(days=180)).strftime("%Y%m%d")

    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    fa = cached_call(stock_dir, today, "stock_financial_abstract",
                     akshare_module.stock_financial_abstract, symbol=code)
    kline = cached_call(stock_dir, today, "stock_zh_a_hist",
                        akshare_module.stock_zh_a_hist,
                        symbol=code, period="daily",
                        start_date=start_s, end_date=today_s, adjust="qfq")
    notice = cached_call(stock_dir, today, "stock_notice_report",
                         akshare_module.stock_notice_report, symbol="全部", date=today_s)
    notice_self = _filter_by_code(notice, code)
    news = cached_call(stock_dir, today, "stock_news_em",
                       akshare_module.stock_news_em, symbol=code)

    meta = _extract_meta(info, code)
    if name and "name" not in meta:
        meta["name"] = name

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "financial_abstract": fa,
        "kline_daily": kline,
        "notice": notice_self,
        "news": news,
    }
    ymd_dir = write_module_data(stock_dir, MODULE_NAME, today, data)

    # 跑 anomaly 扫描，输出 anomalies.json + anomalies.md
    anomalies = scan_financial(fa or [])
    # 给每条 anomaly 加 id（render_md 需要 id 字段；scan_financial 返回的 dict 也有 indicator 等其他字段）
    for i, it in enumerate(anomalies, 1):
        it.setdefault("id", f"A{i:03d}")
    (ymd_dir / "anomalies.json").write_text(
        json.dumps({"anomalies": anomalies}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ymd_dir / "anomalies.md").write_text(
        render_md(anomalies, code=code, as_of=today),
        encoding="utf-8",
    )

    return data

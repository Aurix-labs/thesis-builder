"""scan_anomalies.py · Phase 1.5 异常扫描。

读 data.json，按 references/anomaly-rules.md 规则扫描，输出：
- anomalies.json（结构化）
- anomalies.md（人类可读，CRITICAL → HIGH → MEDIUM 排序）
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# === 规则集 ===
def quarter_label(period_key: str) -> str:
    """20260331 → 2026Q1"""
    y, m = period_key[:4], period_key[4:6]
    q = {"03": "Q1", "06": "Q2", "09": "Q3", "12": "Q4"}.get(m, "?")
    return f"{y}{q}"


def prior_year_period(period_key: str) -> str:
    """20260331 → 20250331"""
    y = int(period_key[:4]) - 1
    return f"{y}{period_key[4:]}"


def scan_financial(fa_rows: list[dict]) -> list[dict]:
    """扫描 financial_abstract，找单季 YoY 异常。"""
    out = []
    by_indicator = {row["指标"]: row for row in fa_rows if "指标" in row}

    if not by_indicator:
        return []
    any_row = next(iter(by_indicator.values()))
    period_keys = [k for k in any_row.keys() if k.isdigit() and len(k) == 8]
    if not period_keys:
        return []
    latest = max(period_keys)
    prior = prior_year_period(latest)

    def yoy(indicator: str):
        row = by_indicator.get(indicator)
        if not row or latest not in row or prior not in row:
            return None
        cur, prv = row[latest], row[prior]
        if prv is None or cur is None or prv == 0:
            return None
        try:
            return float(cur), float(prv), (float(cur) - float(prv)) / abs(float(prv))
        except (TypeError, ValueError):
            return None

    def add(rule_id, indicator, severity, cur, prv, delta, must_steps, hint):
        out.append({
            "rule_id": rule_id,
            "severity": severity,
            "indicator": indicator,
            "period": quarter_label(latest),
            "value": cur,
            "value_display": f"{cur/1e8:.3f}亿" if abs(cur) > 1e6 else f"{cur:.2f}",
            "prior_value": prv,
            "prior_period": quarter_label(prior),
            "delta_pct": delta,
            "blocks_ref": f"financial_abstract.{latest}.{indicator}",
            "must_address_in_step": must_steps,
            "narrative_hint": hint,
        })

    res = yoy("归母净利润")
    if res:
        cur, prv, d = res
        if d < -0.50:
            add("FIN-001", "归母净利润", "CRITICAL", cur, prv, d,
                ["0.5", "4", "5", "8"], f"{quarter_label(latest)} 归母净利同比 {d*100:.1f}%，断崖式下滑")
        elif d < -0.30:
            add("FIN-002", "归母净利润", "HIGH", cur, prv, d,
                ["0.5", "4", "5"], f"{quarter_label(latest)} 归母净利同比 {d*100:.1f}%，显著下滑")

    res = yoy("营业总收入")
    if res:
        cur, prv, d = res
        if d < -0.30:
            add("FIN-003", "营业总收入", "HIGH", cur, prv, d,
                ["0.5", "1", "4"], f"{quarter_label(latest)} 营收同比 {d*100:.1f}%")

    res = yoy("扣非净利润")
    if res:
        cur, prv, d = res
        if d < -0.50:
            add("FIN-006", "扣非净利润", "CRITICAL", cur, prv, d,
                ["0.5", "4", "5"], f"{quarter_label(latest)} 扣非同比 {d*100:.1f}%")

    return out


def scan_fund_flow(ff_rows: list[dict], market_cap: float) -> list[dict]:
    """近 60 日主力净流入累计 / 市值。"""
    if not ff_rows or not market_cap:
        return []
    recent = ff_rows[-60:] if len(ff_rows) >= 60 else ff_rows
    cum = sum(float(r.get("主力净流入-净额", 0) or 0) for r in recent)
    ratio = cum / market_cap
    out = []
    if ratio < -0.20:
        out.append({
            "rule_id": "FUND-001", "severity": "CRITICAL",
            "indicator": "主力净流入", "period": "近60日累计",
            "value": cum, "value_display": f"{cum/1e8:.2f}亿",
            "prior_value": None, "prior_period": None, "delta_pct": ratio,
            "blocks_ref": "fund_flow[-60:].主力净流入-净额",
            "must_address_in_step": ["0.5", "6"],
            "narrative_hint": f"近 60 日主力累计净流出 {cum/1e8:.2f} 亿 (占市值 {ratio*100:.1f}%)",
        })
    elif ratio < -0.10:
        out.append({
            "rule_id": "FUND-002", "severity": "HIGH",
            "indicator": "主力净流入", "period": "近60日累计",
            "value": cum, "value_display": f"{cum/1e8:.2f}亿",
            "prior_value": None, "prior_period": None, "delta_pct": ratio,
            "blocks_ref": "fund_flow[-60:].主力净流入-净额",
            "must_address_in_step": ["0.5", "6"],
            "narrative_hint": f"近 60 日主力累计净流出 {cum/1e8:.2f} 亿 (占市值 {ratio*100:.1f}%)",
        })
    return out


def scan_price(kline: list[list], code_market_cap: float) -> list[dict]:
    """近 60 日区间涨跌。"""
    if not kline or len(kline) < 60:
        return []
    closes = [row[2] for row in kline[-60:]]
    chg = (closes[-1] - closes[0]) / closes[0]
    if abs(chg) > 0.30:
        sev = "HIGH" if abs(chg) > 0.50 else "MEDIUM"
        return [{
            "rule_id": "PRICE-001" if sev == "HIGH" else "PRICE-002",
            "severity": sev,
            "indicator": "近60日区间涨跌",
            "period": f"{kline[-60][0]} ~ {kline[-1][0]}",
            "value": chg,
            "value_display": f"{chg*100:.1f}%",
            "prior_value": None, "prior_period": None, "delta_pct": chg,
            "blocks_ref": "kline_daily[-60:]",
            "must_address_in_step": ["0.5", "6"],
            "narrative_hint": f"近 60 日区间涨跌 {chg*100:.1f}%",
        }]
    return []


def render_md(items: list[dict], code: str = "?", as_of: str = "?") -> str:
    """渲染 anomalies 为 markdown（CRITICAL → HIGH → MEDIUM 排序）。"""
    md = [f"# anomalies · {code} · {as_of}", ""]
    for sev in ["CRITICAL", "HIGH", "MEDIUM"]:
        sev_items = [x for x in items if x["severity"] == sev]
        if not sev_items:
            continue
        if sev == "CRITICAL":
            md.append("## CRITICAL（必须在 Step 0.5 整段讨论）")
        elif sev == "HIGH":
            md.append("## HIGH（必须在 Step 0.5 列出）")
        else:
            md.append("## MEDIUM（自决讨论）")
        md.append("")
        for it in sev_items:
            md.append(f"### {it['id']} · {it['indicator']} {it['period']} · {it['narrative_hint']}")
            md.append(f"- 当前：{it['value_display']} `[F:{it['blocks_ref']}]`")
            if it.get("prior_value") is not None:
                md.append(f"- 上年同期：{it['prior_value']/1e8:.3f}亿")
            md.append(f"- 必须讨论 Step：{', '.join(it['must_address_in_step'])}")
            md.append("")
    return "\n".join(md)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-md", required=True)
    args = p.parse_args()

    data = json.loads(Path(args.data).read_text())
    blocks = data.get("blocks", {})
    market_cap = data.get("quote", {}).get("market_cap", 0)

    items = []
    items += scan_financial(blocks.get("financial_abstract", []))
    items += scan_fund_flow(blocks.get("fund_flow", []), market_cap)
    items += scan_price(data.get("kline_daily", []), market_cap)

    sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    items.sort(key=lambda x: sev_rank.get(x["severity"], 99))
    for i, it in enumerate(items, 1):
        it["id"] = f"A{i:03d}"

    out_obj = {
        "$schema": "anomalies-v1",
        "as_of": data.get("meta", {}).get("as_of", "?"),
        "code": data.get("meta", {}).get("code", "?"),
        "items": items,
    }
    Path(args.out_json).write_text(json.dumps(out_obj, ensure_ascii=False, indent=2))

    md = render_md(items, code=out_obj["code"], as_of=out_obj["as_of"])
    Path(args.out_md).write_text(md)

    print(f"[OK] {len(items)} anomalies, {sum(1 for x in items if x['severity']=='CRITICAL')} CRITICAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

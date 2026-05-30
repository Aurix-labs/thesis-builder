"""validate_data.py · 数据质量校验。

在每个 fetch 脚本拉完数据后、Agent 写 report.md 前运行。
检查各模块 data.json 是否达到"可写报告"的最低质量标准。
不达标直接报 FAIL，Agent 应停止写该模块 report.md 并向用户报告。

用法：
  python scripts/validate_data.py --ymd <YYYY-MM-DD> [--module <m>] [--output-dir <dir>]
退出码：
  0 = 全部通过，可写报告
  1 = 有模块 FAIL（数据不足以出报告）
  2 = 有模块 WARN（数据可用但有缺失字段）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REVIEW_MODULES = ["index", "sentiment", "mainline", "capital", "variables", "combatmap"]

# ---- 各模块校验规则 ----

def _check_index(data: dict) -> dict:
    """大盘环境：至少 3/5 指数 trend 有效，total_amount_yi 不为 null。"""
    idx = data.get("index_data", {})
    valid_trend = 0
    total = 0
    for code, info in idx.items():
        trend = info.get("trend", "数据不足")
        if trend != "数据不足":
            valid_trend += 1
        total += 1
    amount = data.get("total_amount_yi")

    issues = []
    if valid_trend < 3:
        issues.append(f"仅 {valid_trend}/{total} 个指数趋势分类成功（需 ≥3）")
    if amount is None:
        issues.append("total_amount_yi 为 null（akshare 指数 volume 字段可能缺失）")

    return {
        "module": "index",
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
        "summary": f"trend={valid_trend}/{total} ok, total_amount={amount}",
    }


def _check_sentiment(data: dict) -> dict:
    """情绪周期：涨跌停总数 > 0，连板数据可用。"""
    up = data.get("limit_up_count", 0)
    down = data.get("limit_down_count", 0)
    max_board = data.get("max_consecutive_board", 0)
    gradient = data.get("board_gradient", {})

    issues = []
    if up + down == 0:
        issues.append("涨跌停数据均为 0（akshare zt_pool 接口可能未返回数据）")
    if not gradient:
        issues.append("连板梯度数据缺失")

    return {
        "module": "sentiment",
        "status": "FAIL" if (up + down == 0) else ("WARN" if issues else "PASS"),
        "issues": issues,
        "summary": f"limit_up={up}, limit_down={down}, max_board={max_board}",
    }


def _check_mainline(data: dict) -> dict:
    """主线识别：涨停板块归类数据可用。"""
    by_sector = data.get("limit_up_by_sector", {})
    sector_flow = data.get("sector_flow_top20", [])
    issues = []
    if not by_sector:
        issues.append("limit_up_by_sector 为空（akshare zt_pool 接口可能未返回数据）")
    if not sector_flow:
        issues.append("sector_flow_top20 为空（akshare sector_fund_flow_rank 盘后可能不可用）")

    return {
        "module": "mainline",
        "status": "FAIL" if not by_sector else ("WARN" if issues else "PASS"),
        "issues": issues,
        "summary": f"sectors={len(by_sector)}, flow_rows={len(sector_flow)}",
    }


def _check_capital(data: dict) -> dict:
    """资金监测：fund_flow（盘后立即可用）必须存在，北向和龙虎榜可延迟。"""
    ff = data.get("fund_flow", {})
    has_fund_flow = ff.get("available", False)
    nb = data.get("northbound", {})
    has_nb_records = len(nb.get("recent_10d", [])) > 0
    lhb = data.get("lhb_count", 0)
    timing = data.get("_timing_notes", [])

    issues = []
    if not has_fund_flow:
        issues.append("fund_flow 为空（stock_market_fund_flow 盘后应可用，请检查 akshare 版本）")
    if not has_nb_records:
        issues.append("北向资金数据无记录")
    if lhb == 0:
        issues.append("龙虎榜为空（约 16:30 后公布；当前时段正常）")
    for note in timing:
        issues.append(note)

    return {
        "module": "capital",
        "status": "FAIL" if not has_fund_flow else ("WARN" if issues else "PASS"),
        "issues": issues,
        "summary": f"fund_flow={'ok' if has_fund_flow else 'MISSING'}, nb_records={len(nb.get('recent_10d', []))}, lhb={lhb}",
    }


def _check_variables(data: dict) -> dict:
    """盘后变量：至少美股或港股有数据，新闻留给 Agent WebSearch。"""
    us = data.get("us_market", {})
    hk = data.get("hk_market", {})
    comm = data.get("commodities", {})
    has_any = (
        len(us.get("dji", [])) > 0
        or len(hk.get("hsi", [])) > 0
    )
    issues = []
    if not has_any:
        issues.append("美股+港股数据均为空（akshare 海外指数接口可能失败）")
    if not comm.get("crude_oil") and not comm.get("gold"):
        issues.append("大宗商品数据为空（akshare futures_foreign_hist 可能失败）")

    return {
        "module": "variables",
        "status": "FAIL" if not has_any else ("WARN" if issues else "PASS"),
        "issues": issues,
        "summary": f"us={sum(len(v) for v in us.values())}rows, hk={sum(len(v) for v in hk.values())}rows",
    }


def _check_combatmap(data: dict) -> dict:
    """作战地图：前五模块的关键参数都已提取。"""
    prereq = data.get("_prereq_status", {})
    missing = [k for k, v in prereq.items() if v == "missing"]
    issues = []
    if missing:
        issues.append(f"前置模块数据缺失: {', '.join(missing)}")

    return {
        "module": "combatmap",
        "status": "FAIL" if missing else "PASS",
        "issues": issues,
        "summary": f"prereq={'all ok' if not missing else f'{len(missing)} missing'}",
    }


CHECKERS = {
    "index": _check_index,
    "sentiment": _check_sentiment,
    "mainline": _check_mainline,
    "capital": _check_capital,
    "variables": _check_variables,
    "combatmap": _check_combatmap,
}


def validate_module(output_dir: Path, ymd: str, module: str) -> dict:
    data_path = output_dir / ymd / module / "data.json"
    if not data_path.exists():
        return {
            "module": module,
            "status": "FAIL",
            "issues": [f"data.json 不存在: {data_path}"],
            "summary": "no data",
        }
    data = json.loads(data_path.read_text(encoding="utf-8"))
    checker = CHECKERS.get(module)
    if checker is None:
        return {"module": module, "status": "PASS", "issues": [], "summary": "no checker"}
    return checker(data)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="market-review 数据质量校验")
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--module", default=None, help="只校验指定模块（默认全部）")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    output_dir = Path(args.output_dir)
    modules = [args.module] if args.module else REVIEW_MODULES

    results = []
    for m in modules:
        r = validate_module(output_dir, args.ymd, m)
        results.append(r)

    # 输出结果
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    warn_count = sum(1 for r in results if r["status"] == "WARN")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    print(f"=== validate_data · {args.ymd} ===")
    for r in results:
        flag = "✅" if r["status"] == "PASS" else ("⚠️" if r["status"] == "WARN" else "❌")
        print(f"{flag} {r['module']}: {r['status']} — {r['summary']}")
        for issue in r["issues"]:
            print(f"   ↳ {issue}")
    print(f"\nPASS={pass_count} WARN={warn_count} FAIL={fail_count}")

    if fail_count > 0:
        return 1
    if warn_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

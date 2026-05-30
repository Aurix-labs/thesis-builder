"""M2 sentiment · 情绪周期定位 数据采集。

字段：limit_up_list, limit_down_list, consecutive_board, bomb_rate, big_noodle
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "sentiment"


def _count_consecutive(records: list[dict]) -> dict:
    """统计连板梯度：{连板数: 股票数}"""
    from collections import Counter
    cnt = Counter()
    for r in records:
        lb = int(r.get("连板数", 0) or 0)
        if lb > 0:
            cnt[lb] += 1
    return dict(sorted(cnt.items()))


def _calc_bomb_rate(limit_up_count: int, bomb_count: int) -> float:
    if limit_up_count + bomb_count == 0:
        return 0.0
    return round(bomb_count / (limit_up_count + bomb_count) * 100, 1)


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)
    today_s = today_d.strftime("%Y%m%d")

    limit_up, limit_down = [], []
    try:
        df_up = ak.stock_zt_pool_em(date=today_s)
        if df_up is not None and not df_up.empty:
            limit_up = df_up.to_dict(orient="records") if hasattr(df_up, "to_dict") else list(df_up)
    except Exception:
        pass

    try:
        df_down = ak.stock_zt_pool_dtgc_em(date=today_s)
        if df_down is not None and not df_down.empty:
            limit_down = df_down.to_dict(orient="records") if hasattr(df_down, "to_dict") else list(df_down)
    except Exception:
        pass

    # 炸板检测：涨停池中"炸板"标记
    bomb_list = [r for r in limit_up if "炸" in str(r.get("状态", "")) or "开板" in str(r.get("备注", ""))]
    bomb_rate = _calc_bomb_rate(len(limit_up), len(bomb_list))

    # 大面股：涨停炸板且当日跌幅 > 8%
    big_noodle = []
    for r in limit_up:
        pct = float(r.get("涨跌幅", 0) or 0)
        status = str(r.get("状态", ""))
        if ("炸" in status or "开板" in status) and pct < -5:
            big_noodle.append(r)

    max_board = 0
    board_gradient = _count_consecutive(limit_up)
    if board_gradient:
        max_board = max(board_gradient.keys())

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "limit_up_count": len(limit_up),
        "limit_down_count": len(limit_down),
        "max_consecutive_board": max_board,
        "board_gradient": board_gradient,
        "bomb_count": len(bomb_list),
        "bomb_rate_pct": bomb_rate,
        "big_noodle_count": len(big_noodle),
        "limit_up_sample": limit_up[:20],   # 前 20 条供 Agent 参考
        "limit_down_sample": limit_down[:20],
        "bomb_sample": bomb_list[:10],
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data

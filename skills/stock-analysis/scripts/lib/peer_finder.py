"""同业自动选股：按 industry 拉板块成分，按市值接近本公司排序，排除 ST。"""
from __future__ import annotations

from typing import Any


def find_peers(
    code: str,
    industry: str,
    count: int = 5,
    *,
    akshare_module=None,
) -> list[str]:
    """返回 count 个同业代码（不含 self）。

    Args:
        code: 本公司 6 位代码
        industry: 板块/行业名（如 "汽车整车"）
        count: 返回数量
        akshare_module: 注入测试用 fake
    """
    if akshare_module is None:
        import akshare as akshare_module

    raw = akshare_module.stock_board_industry_cons_em(symbol=industry)
    if hasattr(raw, "to_dict"):
        raw = raw.to_dict(orient="records")
    if not raw:
        return []

    self_cap = None
    for r in raw:
        if str(r.get("代码", "")).strip() == code:
            self_cap = r.get("总市值")
            break

    candidates: list[tuple[float, str]] = []
    for r in raw:
        rcode = str(r.get("代码", "")).strip()
        rname = str(r.get("名称", "")).strip()
        if rcode == code:
            continue
        if "ST" in rname.upper():
            continue
        cap = r.get("总市值")
        if cap is None or not isinstance(cap, (int, float)):
            continue
        if self_cap is None:
            distance = 0.0
        else:
            distance = abs(float(cap) - float(self_cap))
        candidates.append((distance, rcode))

    candidates.sort(key=lambda x: x[0])
    return [c for _, c in candidates[:count]]

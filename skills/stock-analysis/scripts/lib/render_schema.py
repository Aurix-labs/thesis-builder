"""merged data.json 必填字段 schema 校验。

供 render_html.py 在渲染前调用，任一字段缺失/类型错抛 RenderError 并精确定位。
不引 pydantic（避免依赖膨胀），用一张数据驱动的 SCHEMA 表 + 纯手写检查。
"""
from __future__ import annotations

from typing import Any


class RenderError(Exception):
    """渲染前置检查失败。错误信息必须含确切字段路径。"""


# 风险等级合法值（来自 spec §6.2）
_RISK_LEVELS = {"低", "中", "高", "极高"}

# 每条 SCHEMA 描述：path -> (expected_type, extra_check)
# extra_check 接收当前字段值，返回 None 表示通过、返回 str 描述失败原因
# path 中的 `*` 表示列表全元素遍历
_SCHEMA: list[tuple[str, type | tuple, callable | None]] = [
    # meta（compose 注入）
    ("meta.stock_code", str, None),
    ("meta.stock_name", str, None),
    ("meta.stock_dir", str, None),
    ("meta.ymd", str, None),
    ("meta.time_utc8", str, None),
    ("meta.session_id", str, None),
    ("meta.data_as_of", str, None),
    ("meta.research_status", str, None),
    # chain.summary（LLM 写入）
    ("chain.summary.industry_phase", str, None),
    # rubric.summary
    ("rubric.summary.total", int, lambda v: None if 0 <= v <= 100 else f"应在 [0,100], 实际 {v}"),
    ("rubric.summary.passed", int, lambda v: None if 0 <= v <= 20 else f"应在 [0,20], 实际 {v}"),
    ("rubric.summary.dimensions", list, lambda v: None if len(v) == 6 else f"应恰好 6 条, 实际 {len(v)}"),
    ("rubric.summary.dimensions.*.name", str, None),
    ("rubric.summary.dimensions.*.points_max", int, None),
    ("rubric.summary.dimensions.*.points_got", int, None),
    ("rubric.summary.financials_table", list, lambda v: None if len(v) >= 3 else f"应 ≥3 条, 实际 {len(v)}"),
    ("rubric.summary.financials_table.*.year", int, None),
    ("rubric.summary.financials_table.*.revenue", (int, float), None),
    ("rubric.summary.financials_table.*.net_profit", (int, float), None),
    ("rubric.summary.financials_table.*.gross_margin", (int, float), None),
    ("rubric.summary.financials_table.*.roe", (int, float), None),
    ("rubric.summary.revenue_breakdown", list, lambda v: None if len(v) >= 1 else "应 ≥1 条"),
    ("rubric.summary.revenue_breakdown.*.name", str, None),
    ("rubric.summary.revenue_breakdown.*.value", (int, float), None),
    # elasticity.summary
    ("elasticity.summary.tree_children", list, lambda v: None if len(v) >= 1 else "应 ≥1 条"),
    ("elasticity.summary.tree_children.*.name", str, None),
    ("elasticity.summary.tree_children.*.ratio", str, None),
    ("elasticity.summary.tree_children.*.margin", str, None),
    ("elasticity.summary.tree_children.*.factor", str, None),
    ("elasticity.summary.tree_children.*.is_core", bool, None),
    # risk.summary
    ("risk.summary.level", str, lambda v: None if v in _RISK_LEVELS else f"必须是 {_RISK_LEVELS} 之一, 实际 {v!r}"),
    # valuation.summary
    ("valuation.summary.targets.short", (int, float), None),
    ("valuation.summary.targets.mid", (int, float), None),
    ("valuation.summary.targets.long", (int, float), None),
    ("valuation.summary.targets.mid_change_pct", (int, float), None),
    ("valuation.summary.targets.base_date", str, None),
    ("valuation.summary.rr", (int, float), None),
    # flow_tech (fetch-原始)
    ("flow_tech.kline_daily", list, lambda v: None if len(v) >= 120 else f"应 ≥120 行, 实际 {len(v)}"),
    # peers.summary
    ("peers.summary.list", list, lambda v: None if len(v) >= 1 else "应 ≥1 条"),
    ("peers.summary.list.*.code", str, None),
    ("peers.summary.list.*.name", str, None),
]


def _walk(data: Any, path_parts: list[str], full_path: str) -> Any:
    """按 path_parts 在 data 上深入。遇到 '*' 时不解包（由调用方处理）。
    返回最终值；中间任一段缺失抛 RenderError(full_path)。"""
    cur = data
    for i, p in enumerate(path_parts):
        if p == "*":
            return cur  # 把 list 交给调用方
        if not isinstance(cur, dict):
            raise RenderError(f"data.json 路径 {full_path} 在 {'.'.join(path_parts[:i])} 处不是 dict")
        if p not in cur:
            raise RenderError(f"data.json 缺字段 {full_path}")
        cur = cur[p]
    return cur


def _check_type(value: Any, expected: type | tuple, path: str) -> None:
    # bool 是 int 的子类，要单独处理避免误判
    if expected is int and isinstance(value, bool):
        raise RenderError(f"{path} 期望 int, 实际 bool")
    if not isinstance(value, expected):
        actual = type(value).__name__
        exp_name = expected.__name__ if isinstance(expected, type) else "/".join(t.__name__ for t in expected)
        raise RenderError(f"{path} 期望 {exp_name}, 实际 {actual} {value!r}")


def _validate_one(data: dict, path: str, expected_type, extra_check) -> None:
    parts = path.split(".")
    # 找 '*' 的位置
    if "*" not in parts:
        value = _walk(data, parts, path)
        _check_type(value, expected_type, path)
        if extra_check is not None:
            msg = extra_check(value)
            if msg:
                raise RenderError(f"{path} {msg}")
        return

    # 含 '*'：分两段
    star_idx = parts.index("*")
    head, tail = parts[:star_idx], parts[star_idx + 1 :]
    container = _walk(data, head, ".".join(head))
    if not isinstance(container, list):
        raise RenderError(f"{'.'.join(head)} 期望 list, 实际 {type(container).__name__}")
    for i, item in enumerate(container):
        idx_path = f"{'.'.join(head)}[{i}]" + ("." + ".".join(tail) if tail else "")
        if tail:
            value = _walk(item, tail, idx_path)
        else:
            value = item
        _check_type(value, expected_type, idx_path)
        if extra_check is not None:
            msg = extra_check(value)
            if msg:
                raise RenderError(f"{idx_path} {msg}")


def validate_schema(data: dict) -> None:
    """对合并后的 data.json 跑必填字段 + 类型 + 额外约束检查。

    任一失败抛 RenderError，错误信息精确到字段路径（含列表下标）。
    """
    for path, expected_type, extra in _SCHEMA:
        _validate_one(data, path, expected_type, extra)

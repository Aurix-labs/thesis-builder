# market-review Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `market-review` skill — A 股市场每日复盘系统 with 6 decoupled modules, each producing independent data.json + report.md, synthesized into a daily review.md.

**Architecture:** Mimics stock-analysis v4.0 patterns — Python scripts fetch data via akshare into per-module `data.json`, Agent writes per-module `report.md` guided by `references/modules/<m>.md`, orchestrated by `run_review.py`. Output organized by trading date under `output/<YYYY-MM-DD>/`. All modules TTL=1 day, `--force` to override.

**Tech Stack:** Python 3, akshare, PyYAML, shell scripts (verify), Agent (report writing + synthesis).

---

## File Structure

```
skills/market-review/
├── SKILL.md
├── config.yaml
├── scripts/
│   ├── requirements.txt
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── config_loader.py      # config.yaml loader + alias resolution
│   │   ├── module_io.py           # write/read data.json, latest symlink
│   │   ├── ttl_check.py           # TTL hit detection
│   │   └── trade_calendar.py      # last trading day helper
│   ├── fetch_index.py
│   ├── fetch_sentiment.py
│   ├── fetch_mainline.py
│   ├── fetch_capital.py
│   ├── fetch_variables.py
│   ├── fetch_combatmap_data.py
│   ├── run_review.py
│   ├── verify_facts.py
│   ├── verify_consistency.py
│   └── record_eval.py
├── references/
│   ├── data-schema.md
│   └── modules/
│       ├── index.md
│       ├── sentiment.md
│       ├── mainline.md
│       ├── capital.md
│       ├── variables.md
│       └── combatmap.md
└── evals/
    ├── README.md
    └── evals.json
```

**Key divergence from stock-analysis:**
- No stock code parameter — operates on trading date only
- Output root is `output/<YYYY-MM-DD>/` not `<stock>_<code>/`
- All modules TTL=1, no variable TTLs
- No HTML generation, no compose_report.py — Agent synthesizes review.md directly
- Module 6 (combatmap) fetches from modules 1-5, not from akshare

---

### Task 1: Scaffold skill directory and config

**Files:**
- Create: `skills/market-review/config.yaml`

- [ ] **Step 1: Create config.yaml**

```yaml
# market-review 模块配置（用户可直接编辑）

modules:
  index:
    ttl_days: 1
    aliases: [大盘, 指数, 环境诊断, 大盘环境]
    description: 大盘环境诊断 - 指数多空、量能、涨跌家数、情绪温度计

  sentiment:
    ttl_days: 1
    aliases: [情绪, 周期, 情绪周期, 涨停板]
    description: 情绪周期定位 - 连板梯度、炸板率、溢价率、冰点/主升判定

  mainline:
    ttl_days: 1
    aliases: [主线, 板块, 热点, 题材]
    description: 主线与支线识别 - 板块资金、涨停归类、梯队结构

  capital:
    ttl_days: 1
    aliases: [资金, 北向, 龙虎榜, 机构]
    description: 资金行为监测 - 北向资金流向、龙虎榜信号

  variables:
    ttl_days: 1
    aliases: [消息, 政策, 新闻, 变量, 事件]
    description: 盘后变量汇总 - 政策/新闻/海外异动/影响评级

  combatmap:
    ttl_days: 1
    aliases: [作战图, 仓位, 推演, 预案, 作战地图]
    description: 明日作战地图 - 三种路径推演 + 仓位建议 + 风险提示

defaults:
  mode: review
  force: false
```

- [ ] **Step 2: Verify YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('skills/market-review/config.yaml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/config.yaml
git commit -m "feat(market-review): add config.yaml with 6 modules

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Shared lib — config_loader, module_io, ttl_check, trade_calendar

**Files:**
- Create: `skills/market-review/scripts/lib/__init__.py`
- Create: `skills/market-review/scripts/lib/config_loader.py`
- Create: `skills/market-review/scripts/lib/module_io.py`
- Create: `skills/market-review/scripts/lib/ttl_check.py`
- Create: `skills/market-review/scripts/lib/trade_calendar.py`

- [ ] **Step 1: Create lib/__init__.py**

```python
"""market-review shared library."""
```

- [ ] **Step 2: Create lib/config_loader.py**

```python
"""config.yaml 加载 + 模块别名归一化。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REVIEW_MODULES = ["index", "sentiment", "mainline", "capital", "variables", "combatmap"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_alias_map(config: dict) -> dict[str, str]:
    amap: dict[str, str] = {}
    for canon, body in config.get("modules", {}).items():
        amap[canon.lower()] = canon
        for alias in body.get("aliases", []) or []:
            amap[str(alias).lower()] = canon
    return amap


def resolve_module_name(name_or_alias: str, alias_map: dict[str, str]) -> str:
    key = str(name_or_alias).strip().lower()
    if key not in alias_map:
        raise ValueError(f"未知模块名或别名：{name_or_alias!r}")
    return alias_map[key]


def get_ttl(module: str, config: dict) -> int | None:
    body = config.get("modules", {}).get(module, {})
    return body.get("ttl_days")
```

- [ ] **Step 3: Create lib/module_io.py**

```python
"""模块数据读写 + latest 软链管理。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_module_data(output_root: Path, module: str, ymd: str, data: dict) -> Path:
    ymd_dir = output_root / ymd / module
    ymd_dir.mkdir(parents=True, exist_ok=True)
    (ymd_dir / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    update_latest_symlink(output_root / ymd, module)
    return ymd_dir


def read_module_data(output_root: Path, ymd: str, module: str) -> dict:
    path = output_root / ymd / module / "data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_latest_ymd(output_root: Path, module: str) -> str | None:
    """在所有 ymd 目录中找包含此模块 latest 软链的最新日期。"""
    if not output_root.exists():
        return None
    best = None
    for child in sorted(output_root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        latest = child / module / "latest"
        if latest.is_symlink():
            target = latest.readlink()
            target_abs = (latest.parent / target) if not target.is_absolute() else target
            if target_abs.exists():
                best = child.name
                break
    return best


def update_latest_symlink(ymd_dir: Path, module: str) -> None:
    """在 <ymd_dir>/<module>/ 下创建 latest -> <ymd_dir.name> 软链。"""
    module_dir = ymd_dir / module
    module_dir.mkdir(parents=True, exist_ok=True)
    latest = module_dir / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(ymd_dir.name, target_is_directory=True)
```

- [ ] **Step 4: Create lib/ttl_check.py**

```python
"""TTL 命中判定。"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .module_io import get_latest_ymd


def days_between(ymd_start: str, ymd_end: str) -> int:
    s = dt.date.fromisoformat(ymd_start)
    e = dt.date.fromisoformat(ymd_end)
    return (e - s).days


def is_within_ttl(output_root: Path, module: str, today: str, ttl_days: int) -> tuple[bool, str | None]:
    latest = get_latest_ymd(output_root, module)
    if latest is None:
        return False, None
    delta = days_between(latest, today)
    return delta <= ttl_days, latest
```

- [ ] **Step 5: Create lib/trade_calendar.py**

```python
"""交易日辅助：获取最近交易日。"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import time


def last_trade_day(today: str | None = None) -> str:
    """推算最近交易日（简单规则：跳过周末；不含节假日判断）。"""
    d = dt.date.fromisoformat(today) if today else dt.date.today()
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= dt.timedelta(days=1)
    return d.isoformat()
```

- [ ] **Step 6: Run smoke test**

Run: `cd skills/market-review && python -c "from scripts.lib.config_loader import load_config; c=load_config(); print(list(c['modules'].keys()))"`
Expected: `['index', 'sentiment', 'mainline', 'capital', 'variables', 'combatmap']`

- [ ] **Step 7: Commit**

```bash
git add skills/market-review/scripts/lib/
git commit -m "feat(market-review): add shared lib modules

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: requirements.txt

**Files:**
- Create: `skills/market-review/scripts/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
akshare>=1.16.0
pyyaml>=6.0
```

- [ ] **Step 2: Commit**

```bash
git add skills/market-review/scripts/requirements.txt
git commit -m "feat(market-review): add requirements.txt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: fetch_index.py — 模块一：大盘环境诊断

**Files:**
- Create: `skills/market-review/scripts/fetch_index.py`

- [ ] **Step 1: Create fetch_index.py**

```python
"""M1 index · 大盘环境诊断 数据采集。

字段：index_quotes, breadth, volume_stage
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "index"
INDEX_CODES = {
    "sh000001": "上证指数",
    "sh000300": "沪深300",
    "sh000905": "中证500",
    "sh000852": "中证1000",
    "sz399006": "创业板指",
}


def _classify_trend(kline_records: list[dict]) -> str:
    """基于最近 20 条日 K 判断 MA5/MA20 方向"""
    if len(kline_records) < 20:
        return "数据不足"
    closes = [r.get("收盘", 0) or 0 for r in kline_records[-20:]]
    if not closes or closes[-1] == 0:
        return "数据不足"
    ma5 = sum(closes[-5:]) / min(5, len(closes[-5:]))
    ma20 = sum(closes[-20:]) / min(20, len(closes[-20:]))
    prev_ma5 = sum(closes[-6:-1]) / min(5, len(closes[-6:-1])) if len(closes) >= 6 else ma5
    prev_ma20 = sum(closes[-21:-1]) / min(20, len(closes[-21:-1])) if len(closes) >= 21 else ma20

    if ma5 > ma20 and prev_ma5 > prev_ma20:
        return "多头排列"
    elif ma5 < ma20 and prev_ma5 < prev_ma20:
        return "空头排列"
    else:
        return "震荡"


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    today_d = dt.date.fromisoformat(today)
    today_s = today_d.strftime("%Y%m%d")
    start_s = (today_d - dt.timedelta(days=60)).strftime("%Y%m%d")

    output_root = Path(output_root)

    # 拉各指数日 K
    index_data = {}
    for code, name in INDEX_CODES.items():
        try:
            if code.startswith("sh"):
                symbol = code[2:]
                df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
            else:
                symbol = code[2:]
                df = ak.stock_zh_index_daily(symbol=f"sz{symbol}")
        except Exception:
            try:
                df = ak.stock_zh_index_daily(symbol=code)
            except Exception:
                index_data[code] = {"name": name, "error": "fetch_failed", "kline": []}
                continue

        if df is not None and not df.empty:
            records = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
            # akshare 返回的列名可能是英文或中文
            index_data[code] = {
                "name": name,
                "kline": records[-30:],  # 最近 30 天
                "trend": _classify_trend(records),
            }
        else:
            index_data[code] = {"name": name, "error": "empty_data", "kline": []}

    # 涨跌家数（从全 A 指数成分推算或直接取东方财富接口）
    breadth = {"up": 0, "down": 0, "up_pct5": 0, "down_pct5": 0}
    try:
        # 尝试获取全市场涨跌统计
        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is not None and not spot_df.empty:
            records = spot_df.to_dict(orient="records") if hasattr(spot_df, "to_dict") else list(spot_df)
            for r in records:
                pct = float(r.get("涨跌幅", 0) or 0)
                if pct > 0:
                    breadth["up"] += 1
                elif pct < 0:
                    breadth["down"] += 1
                if pct > 5:
                    breadth["up_pct5"] += 1
                elif pct < -5:
                    breadth["down_pct5"] += 1
    except Exception:
        pass

    # 计算全市场总成交额
    total_volume = 0.0
    total_amount = 0.0
    for code_data in index_data.values():
        kline = code_data.get("kline", [])
        if kline:
            last = kline[-1]
            total_amount += float(last.get("成交额", 0) or 0)

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "index_data": index_data,
        "breadth": breadth,
        "total_amount_yi": round(total_amount / 1e8, 2) if total_amount > 0 else None,
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_index.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_index.py
git commit -m "feat(market-review): add fetch_index.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: fetch_sentiment.py — 模块二：情绪周期定位

**Files:**
- Create: `skills/market-review/scripts/fetch_sentiment.py`

- [ ] **Step 1: Create fetch_sentiment.py**

```python
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
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_sentiment.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_sentiment.py
git commit -m "feat(market-review): add fetch_sentiment.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: fetch_mainline.py — 模块三：主线与支线识别

**Files:**
- Create: `skills/market-review/scripts/fetch_mainline.py`

- [ ] **Step 1: Create fetch_mainline.py**

```python
"""M3 mainline · 主线与支线识别 数据采集。

字段：sector_flow, sector_limit_up, mainline_candidates
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "mainline"


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    # 概念板块资金流向
    sector_flow = []
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念")
        if df is not None and not df.empty:
            sector_flow = df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
    except Exception:
        pass

    # 涨停股按板块归类（需结合 sentiment 数据——这里先独立拉取涨停再归类）
    limit_up_by_sector: dict[str, int] = {}
    try:
        today_s = today_d.strftime("%Y%m%d")
        df_up = ak.stock_zt_pool_em(date=today_s)
        if df_up is not None and not df_up.empty:
            records = df_up.to_dict(orient="records") if hasattr(df_up, "to_dict") else list(df_up)
            for r in records:
                sector = str(r.get("所属行业", "") or r.get("板块", "") or "").strip()
                if sector:
                    limit_up_by_sector[sector] = limit_up_by_sector.get(sector, 0) + 1
    except Exception:
        pass

    # 按涨停家数排序，取前 10 板块
    top_sectors = sorted(limit_up_by_sector.items(), key=lambda x: x[1], reverse=True)[:10]

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "sector_flow_top20": sector_flow[:20],
        "limit_up_by_sector": dict(top_sectors),
        "sector_count": len(sector_flow),
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_mainline.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_mainline.py
git commit -m "feat(market-review): add fetch_mainline.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: fetch_capital.py — 模块四：资金行为监测

**Files:**
- Create: `skills/market-review/scripts/fetch_capital.py`

- [ ] **Step 1: Create fetch_capital.py**

```python
"""M4 capital · 资金行为监测 数据采集。

字段：northbound_flow, northbound_3d, lhb_list
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data, read_module_data

MODULE_NAME = "capital"


def _fetch_northbound(ak, today_d: dt.date) -> dict:
    """拉北向资金当日数据"""
    today_s = today_d.strftime("%Y%m%d")
    start_s = (today_d - dt.timedelta(days=10)).strftime("%Y%m%d")

    result = {"today_net": None, "recent_10d": []}
    try:
        # 沪股通
        df_sh = ak.stock_hsgt_hist_em(symbol="沪股通")
        # 深股通
        df_sz = ak.stock_hsgt_hist_em(symbol="深股通")

        if df_sh is not None and not df_sh.empty:
            sh_records = df_sh.to_dict(orient="records") if hasattr(df_sh, "to_dict") else list(df_sh)
            result["recent_10d"] = sh_records[-10:]

        if df_sz is not None and not df_sz.empty:
            sz_records = df_sz.to_dict(orient="records") if hasattr(df_sz, "to_dict") else list(df_sz)
            result["sz_recent_10d"] = sz_records[-10:]

        # 计算当日净买卖（最近一条记录）
        sh_last = result.get("recent_10d", [])
        sz_last = result.get("sz_recent_10d", [])
        sh_net = float(sh_last[-1].get("净买额", 0) or 0) if sh_last else 0
        sz_net = float(sz_last[-1].get("净买额", 0) or 0) if sz_last else 0
        result["today_net"] = round(sh_net + sz_net, 2)
    except Exception:
        pass
    return result


def _fetch_lhb(ak, today_d: dt.date) -> list[dict]:
    """拉龙虎榜当日数据"""
    today_s = today_d.strftime("%Y%m%d")
    try:
        df = ak.stock_sina_lhb_detail_daily(trade_date=today_s)
        if df is not None and not df.empty:
            return df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)
    except Exception:
        pass
    return []


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    northbound = _fetch_northbound(ak, today_d)
    lhb = _fetch_lhb(ak, today_d)

    # 尝试读前两日北向数据算 3 日流向
    nb_3d = [northbound.get("today_net")]
    for offset in (1, 2):
        prev_d = today_d - dt.timedelta(days=offset)
        try:
            prev_data = read_module_data(output_root, prev_d.isoformat(), MODULE_NAME)
            prev_nb = prev_data.get("northbound", {})
            nb_3d.append(prev_nb.get("today_net"))
        except (FileNotFoundError, KeyError):
            nb_3d.append(None)

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "northbound": northbound,
        "northbound_3d": nb_3d,
        "lhb_count": len(lhb),
        "lhb_sample": lhb[:30],
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_capital.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_capital.py
git commit -m "feat(market-review): add fetch_capital.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: fetch_variables.py — 模块五：盘后变量汇总

**Files:**
- Create: `skills/market-review/scripts/fetch_variables.py`

- [ ] **Step 1: Create fetch_variables.py**

```python
"""M5 variables · 盘后变量汇总 数据采集。

仅拉海外市场收盘数据。新闻/政策部分留给 Agent WebSearch。
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from lib.module_io import write_module_data

MODULE_NAME = "variables"

# 海外指数 akshare 接口映射
OVERSEAS_INDICES = {
    "道琼斯": "stock_us_daily",
    "纳斯达克": "stock_us_daily",
    "标普500": "stock_us_daily",
    "恒生指数": "stock_hk_daily",
}


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    ak = akshare_module
    output_root = Path(output_root)
    today_d = dt.date.fromisoformat(today)

    # 美股三大指数（复用同一接口，取最近 5 日）
    us_market = {}
    try:
        df_dji = ak.index_us_stock_sina(symbol=".DJI")
        if df_dji is not None and not df_dji.empty:
            recs = df_dji.to_dict(orient="records") if hasattr(df_dji, "to_dict") else list(df_dji)
            us_market["dji"] = recs[-5:] if recs else []
    except Exception:
        us_market["dji"] = []

    try:
        df_ixic = ak.index_us_stock_sina(symbol=".IXIC")
        if df_ixic is not None and not df_ixic.empty:
            recs = df_ixic.to_dict(orient="records") if hasattr(df_ixic, "to_dict") else list(df_ixic)
            us_market["nasdaq"] = recs[-5:] if recs else []
    except Exception:
        us_market["nasdaq"] = []

    try:
        df_spx = ak.index_us_stock_sina(symbol=".INX")
        if df_spx is not None and not df_spx.empty:
            recs = df_spx.to_dict(orient="records") if hasattr(df_spx, "to_dict") else list(df_spx)
            us_market["sp500"] = recs[-5:] if recs else []
    except Exception:
        us_market["sp500"] = []

    # 港股恒生
    hk_market = {}
    try:
        df_hsi = ak.stock_hk_index_daily_sina(symbol="HSI")
        if df_hsi is not None and not df_hsi.empty:
            recs = df_hsi.to_dict(orient="records") if hasattr(df_hsi, "to_dict") else list(df_hsi)
            hk_market["hsi"] = recs[-5:] if recs else []
    except Exception:
        hk_market["hsi"] = []

    # 大宗商品（原油、黄金）
    commodities = {}
    try:
        df_oil = ak.futures_foreign_hist(symbol="原油")
        if df_oil is not None and not df_oil.empty:
            recs = df_oil.to_dict(orient="records") if hasattr(df_oil, "to_dict") else list(df_oil)
            commodities["crude_oil"] = recs[-3:] if recs else []
    except Exception:
        commodities["crude_oil"] = []

    try:
        df_gold = ak.futures_foreign_hist(symbol="黄金")
        if df_gold is not None and not df_gold.empty:
            recs = df_gold.to_dict(orient="records") if hasattr(df_gold, "to_dict") else list(df_gold)
            commodities["gold"] = recs[-3:] if recs else []
    except Exception:
        commodities["gold"] = []

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "us_market": us_market,
        "hk_market": hk_market,
        "commodities": commodities,
        "_note": "新闻/政策部分由 Agent 通过 WebSearch 获取并直接写入 report.md",
    }
    write_module_data(output_root, MODULE_NAME, today, data)
    return data
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_variables.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_variables.py
git commit -m "feat(market-review): add fetch_variables.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: fetch_combatmap_data.py — 模块六：提取前五模块关键参数

**Files:**
- Create: `skills/market-review/scripts/fetch_combatmap_data.py`

- [ ] **Step 1: Create fetch_combatmap_data.py**

```python
"""M6 combatmap · 从前五模块 data.json 提取关键参数。

本模块不从 akshare 拉数据，只读前五模块的 data.json，
提取结构化的关键参数写入 market_data.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from lib.module_io import write_module_data, read_module_data

MODULE_NAME = "combatmap"
PREREQ_MODULES = ["index", "sentiment", "mainline", "capital", "variables"]


def _safe_read(output_root: Path, ymd: str, module: str) -> dict:
    try:
        return read_module_data(output_root, ymd, module)
    except (FileNotFoundError, KeyError):
        return {}


def _extract_index_params(index_data: dict) -> dict:
    """从模块一提取大盘参数"""
    result = {"trends": {}, "total_amount_yi": index_data.get("total_amount_yi")}
    idx_map = index_data.get("index_data", {})
    for code, info in idx_map.items():
        name = info.get("name", code)
        result["trends"][name] = info.get("trend", "未知")
    result["breadth"] = index_data.get("breadth", {})
    return result


def _extract_sentiment_params(sentiment_data: dict) -> dict:
    """从模块二提取情绪参数"""
    return {
        "limit_up_count": sentiment_data.get("limit_up_count", 0),
        "limit_down_count": sentiment_data.get("limit_down_count", 0),
        "max_consecutive_board": sentiment_data.get("max_consecutive_board", 0),
        "board_gradient": sentiment_data.get("board_gradient", {}),
        "bomb_rate_pct": sentiment_data.get("bomb_rate_pct", 0),
        "big_noodle_count": sentiment_data.get("big_noodle_count", 0),
    }


def _extract_mainline_params(mainline_data: dict) -> dict:
    """从模块三提取主线参数"""
    return {
        "limit_up_by_sector": mainline_data.get("limit_up_by_sector", {}),
        "sector_flow_top10": mainline_data.get("sector_flow_top20", [])[:10],
    }


def _extract_capital_params(capital_data: dict) -> dict:
    """从模块四提取资金参数"""
    nb = capital_data.get("northbound", {})
    return {
        "northbound_today_net": nb.get("today_net"),
        "northbound_3d": capital_data.get("northbound_3d", []),
        "lhb_count": capital_data.get("lhb_count", 0),
    }


def _extract_variables_params(variables_data: dict) -> dict:
    """从模块五提取变量参数"""
    us = variables_data.get("us_market", {})
    hk = variables_data.get("hk_market", {})
    comm = variables_data.get("commodities", {})
    return {
        "us_market_summary": {
            k: v[-1] if v else None
            for k, v in us.items()
        },
        "hk_market_summary": {
            k: v[-1] if v else None
            for k, v in hk.items()
        },
        "commodities_summary": {
            k: v[-1] if v else None
            for k, v in comm.items()
        },
    }


def fetch(output_root: str | Path, today: str, *, akshare_module=None) -> dict:
    output_root = Path(output_root)

    index_d = _safe_read(output_root, today, "index")
    sentiment_d = _safe_read(output_root, today, "sentiment")
    mainline_d = _safe_read(output_root, today, "mainline")
    capital_d = _safe_read(output_root, today, "capital")
    variables_d = _safe_read(output_root, today, "variables")

    market_data = {
        "date": today,
        "index": _extract_index_params(index_d),
        "sentiment": _extract_sentiment_params(sentiment_d),
        "mainline": _extract_mainline_params(mainline_d),
        "capital": _extract_capital_params(capital_d),
        "variables": _extract_variables_params(variables_d),
        "_prereq_status": {
            "index": "ok" if index_d else "missing",
            "sentiment": "ok" if sentiment_d else "missing",
            "mainline": "ok" if mainline_d else "missing",
            "capital": "ok" if capital_d else "missing",
            "variables": "ok" if variables_d else "missing",
        },
    }

    # 写入两个文件：data.json（内部用）+ market_data.json（供 stock-review 消费）
    write_module_data(output_root, MODULE_NAME, today, market_data)
    market_data_path = output_root / today / MODULE_NAME / "market_data.json"
    market_data_path.write_text(
        json.dumps(market_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return market_data
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/fetch_combatmap_data.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/fetch_combatmap_data.py
git commit -m "feat(market-review): add fetch_combatmap_data.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: run_review.py — 编排调度

**Files:**
- Create: `skills/market-review/scripts/run_review.py`

- [ ] **Step 1: Create run_review.py**

```python
"""market-review 模块执行入口（数据层操作，不写 report.md）。

用法：
  python run_review.py [--force] [--module <m>] [--date <YYYY-MM-DD>]
输出（stdout）：
  每个模块一行 JSON，含 status (reuse/data_ready) + 路径
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Callable

from lib.config_loader import (
    REVIEW_MODULES, load_config, build_alias_map, resolve_module_name, get_ttl,
)
from lib.ttl_check import is_within_ttl

_FETCH_REGISTRY: dict[str, Callable] = {}


def _register_fetchers():
    global _FETCH_REGISTRY
    if _FETCH_REGISTRY:
        return
    from fetch_index import fetch as f_index
    from fetch_sentiment import fetch as f_sentiment
    from fetch_mainline import fetch as f_mainline
    from fetch_capital import fetch as f_capital
    from fetch_variables import fetch as f_variables
    from fetch_combatmap_data import fetch as f_combatmap
    _FETCH_REGISTRY = {
        "index": f_index,
        "sentiment": f_sentiment,
        "mainline": f_mainline,
        "capital": f_capital,
        "variables": f_variables,
        "combatmap": f_combatmap,
    }


def expand_modules(user_modules: list[str], config: dict) -> list[str]:
    """归一化别名 + 展开 review → 全部 6 个模块。返回有序清单。"""
    amap = build_alias_map(config)
    canonical = [resolve_module_name(m, amap) for m in user_modules]
    out: list[str] = []
    for m in canonical:
        if m == "review":
            for rm in REVIEW_MODULES:
                if rm not in out:
                    out.append(rm)
        else:
            if m not in out:
                out.append(m)
    # 确保 combatmap 在最后（依赖前五模块）
    if "combatmap" in out:
        out.remove("combatmap")
        out.append("combatmap")
    return out


def process_one(
    *,
    output_root: Path,
    module: str,
    today: str,
    force: bool,
    config: dict,
) -> dict[str, Any]:
    """处理一个模块。返回状态 dict。"""
    ttl = get_ttl(module, config)
    if ttl is None:
        raise ValueError(f"模块 {module} 无 TTL 配置")

    within, latest = is_within_ttl(output_root, module, today, ttl)
    if within and latest and not force:
        return {
            "module": module,
            "status": "reuse",
            "ymd": latest,
            "data_json": str(output_root / latest / module / "data.json"),
            "report_md": str(output_root / latest / module / "report.md"),
            "needs_report_md": False,
        }

    _register_fetchers()
    fn = _FETCH_REGISTRY[module]
    # combatmap 不需要 akshare 引用
    fn(output_root=output_root, today=today)

    ymd_dir = output_root / today / module
    return {
        "module": module,
        "status": "data_ready",
        "ymd": today,
        "data_json": str(ymd_dir / "data.json"),
        "report_md": str(ymd_dir / "report.md"),
        "needs_report_md": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_review.py",
        description="market-review 模块执行入口（数据层）",
    )
    p.add_argument("--force", action="store_true", help="覆盖 TTL，强制重跑")
    p.add_argument("--module", default="review", help="模块名/别名（默认 review=全部）")
    p.add_argument("--date", default=None, help="交易日（YYYY-MM-DD，默认今天）")
    p.add_argument("--output-dir", default="output", help="输出根目录（默认 ./output）")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    today = args.date or dt.date.today().isoformat()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    config = load_config()
    try:
        modules = expand_modules([args.module], config)
    except ValueError as e:
        print(f"[X] {e}", file=sys.stderr)
        return 1

    errors = 0
    for m in modules:
        try:
            r = process_one(
                output_root=output_root,
                module=m,
                today=today,
                force=args.force,
                config=config,
            )
            print(json.dumps(r, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"module": m, "status": "error", "error": str(e)}, ensure_ascii=False))
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run help check**

Run: `cd skills/market-review && python scripts/run_review.py --help`
Expected: Prints usage with --force, --module, --date, --output-dir

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/run_review.py
git commit -m "feat(market-review): add run_review.py orchestration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: verify_facts.py — 单模块 data.json ↔ report.md 校验

**Files:**
- Create: `skills/market-review/scripts/verify_facts.py`

- [ ] **Step 1: Create verify_facts.py**

```python
"""verify_facts.py · 校验单模块 data.json ↔ report.md 标签对齐。

检查 report.md 中的 [F:] [C:] 标签与 data.json 数据一致性。
复用了 stock-analysis 的标签校验逻辑，适配 market-review 的输出结构。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r'\[(F|C|I|T):([^\[\]]+)\]')
NUM_RE = re.compile(r'(-?\d+\.?\d*)\s*(亿|万|%|倍|元|万手|手)?')

UNIT_SCALES = {
    "亿": 1e8, "万": 1e4, "千": 1e3,
    "%": 1, "pct": 1, "倍": 1, "元": 1,
}

ALLOWED_FUNCS = {'pow': pow, 'sqrt': math.sqrt, 'abs': abs}
FORMULA_TOKEN = re.compile(r'[\w\.\[\]\-\|]+')


def parse_payload(payload: str) -> tuple[str, str | None]:
    if '|' in payload:
        path, unit = payload.rsplit('|', 1)
        return path.strip(), unit.strip()
    return payload, None


def resolve_path(data: Any, path: str) -> Any:
    tokens = re.findall(r'[^.\[\]]+|\[-?\d+\]', path)
    cur = data
    for tok in tokens:
        if tok.startswith('[') and tok.endswith(']'):
            idx = int(tok[1:-1])
            if not isinstance(cur, list):
                raise KeyError(f"expects list, got {type(cur).__name__}")
            cur = cur[idx]
        else:
            if isinstance(cur, list):
                cur = cur[int(tok)]
            elif isinstance(cur, dict):
                if tok not in cur:
                    raise KeyError(f"{tok} not in dict")
                cur = cur[tok]
            else:
                raise KeyError(f"cannot index {type(cur).__name__}")
    return cur


def parse_nearest_number(line: str, col: int) -> float | None:
    matches = list(NUM_RE.finditer(line[:col]))
    if not matches:
        return None
    try:
        return float(matches[-1].group(1))
    except ValueError:
        return None


def rel_diff(a: float, b: float) -> float:
    if b == 0:
        return abs(a)
    return abs(a - b) / abs(b)


def check_f_tag(tag_payload: str, data: Any, line_no: int, line: str, col: int) -> dict | None:
    path, unit = parse_payload(tag_payload)
    try:
        raw = resolve_path(data, path)
        expected = float(raw) / UNIT_SCALES.get(unit, 1) if unit else float(raw)
    except (KeyError, ValueError, TypeError) as e:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": f"path 解析失败：{e}",
        }
    actual = parse_nearest_number(line, col)
    if actual is None:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": "标签前未找到数字",
        }
    if rel_diff(actual, expected) > 0.01:
        return {
            "kind": "FAIL", "tag": f"[F:{tag_payload}]", "line": line_no,
            "reason": f"标 {actual} vs data.json {expected:.4g}，差 {rel_diff(actual, expected)*100:.1f}%",
        }
    return None


def eval_formula(formula: str, data: Any) -> float:
    def replace(m):
        tok = m.group(0)
        if tok in ('-', '+', '*', '/'):
            return tok
        if tok.replace('.', '').replace('-', '').replace('e', '').replace('E', '').isdigit():
            return tok
        if tok in ALLOWED_FUNCS:
            return tok
        path, unit = parse_payload(tok)
        try:
            v = resolve_path(data, path)
            return str(float(v) / UNIT_SCALES.get(unit, 1) if unit else float(v))
        except (KeyError, ValueError, TypeError):
            raise ValueError(f"token {tok} 无法解析")
    replaced = FORMULA_TOKEN.sub(replace, formula)
    return eval(replaced, {"__builtins__": None}, ALLOWED_FUNCS)  # noqa: S307


def check_c_tag(tag_payload: str, data: Any, line_no: int, line: str, col: int) -> dict | None:
    try:
        expected = eval_formula(tag_payload, data)
    except Exception as e:
        return {"kind": "FAIL", "tag": f"[C:{tag_payload}]", "line": line_no, "reason": str(e)}
    actual = parse_nearest_number(line, col)
    if actual is None or rel_diff(actual, expected) > 0.01:
        return {"kind": "FAIL", "tag": f"[C:{tag_payload}]", "line": line_no,
                "reason": f"标 {actual} vs 公式算出 {expected:.4g}"}
    return None


def check_i_tag(tag_payload: str, line_no: int) -> dict | None:
    if len(tag_payload.strip()) < 4:
        return {"kind": "FAIL", "tag": f"[I:{tag_payload}]", "line": line_no,
                "reason": "推断依据过短（< 4 字）"}
    return None


def verify_module(data_path: Path, report_path: Path) -> int:
    md_text = report_path.read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    tags = list(TAG_RE.finditer(md_text))
    fails, warns = [], []

    for m in tags:
        kind = m.group(1)
        payload = m.group(2).strip()
        # 计算行号和列号
        line_no = md_text[:m.start()].count('\n') + 1
        line_start = md_text.rfind('\n', 0, m.start()) + 1
        line_end = md_text.find('\n', m.start())
        if line_end == -1:
            line_end = len(md_text)
        line = md_text[line_start:line_end]
        col = m.start() - line_start

        r = None
        if kind == 'F':
            r = check_f_tag(payload, data, line_no, line, col)
        elif kind == 'C':
            r = check_c_tag(payload, data, line_no, line, col)
        elif kind == 'I':
            r = check_i_tag(payload, line_no)

        if r:
            (warns if r['kind'] == 'WARN' else fails).append(r)

    print(f"=== verify_facts · {len(tags)} tags ===")
    for r in fails + warns:
        print(f"[{r['kind']}] L{r.get('line', '?')} {r['tag']}: {r['reason']}")
    print(f"\n[PASS] {len(tags) - len(fails) - len(warns)} / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--module", required=True, help="模块名")
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    data_path = Path(args.output_dir) / args.ymd / args.module / "data.json"
    report_path = Path(args.output_dir) / args.ymd / args.module / "report.md"

    if not data_path.exists():
        print(f"ERROR: {data_path} not found", file=sys.stderr)
        return 1
    if not report_path.exists():
        print(f"ERROR: {report_path} not found", file=sys.stderr)
        return 1

    return verify_module(data_path, report_path)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/verify_facts.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/verify_facts.py
git commit -m "feat(market-review): add verify_facts.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: verify_consistency.py — 跨模块一致性校验

**Files:**
- Create: `skills/market-review/scripts/verify_consistency.py`

- [ ] **Step 1: Create verify_consistency.py**

```python
"""verify_consistency.py · 合成后跨模块一致性校验。

检查项：
1. 各模块 report.md 存在且 MARKER 头对齐
2. module 间共享数据数字一致（如同一个指数在不同模块中数值相同）
3. review.md 引用了全部 6 个模块
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REVIEW_MODULES = ["index", "sentiment", "mainline", "capital", "variables", "combatmap"]
MARKER_RE = re.compile(r'<!-- REVIEW_MODULE_START\s+module=(\w+)\s+date=(\d{4}-\d{2}-\d{2})\s+-->')


def check_module_markers(ymd_dir: Path) -> list[dict]:
    """检查各模块 report.md 是否有正确的 MARKER 头。"""
    issues = []
    for m in REVIEW_MODULES:
        report_path = ymd_dir / m / "report.md"
        if not report_path.exists():
            issues.append({"kind": "FAIL", "module": m, "reason": "report.md 不存在"})
            continue
        content = report_path.read_text(encoding="utf-8")
        marker = MARKER_RE.search(content)
        if not marker:
            issues.append({"kind": "FAIL", "module": m, "reason": "缺少 REVIEW_MODULE_START marker"})
            continue
        if marker.group(1) != m:
            issues.append({"kind": "WARN", "module": m, "reason": f"marker module={marker.group(1)} != 目录名 {m}"})
    return issues


def check_review_md(ymd_dir: Path) -> list[dict]:
    """检查 review.md 是否引用了全部模块。"""
    review_path = ymd_dir / "review.md"
    issues = []
    if not review_path.exists():
        return [{"kind": "FAIL", "module": "review", "reason": "review.md 不存在"}]

    content = review_path.read_text(encoding="utf-8")
    for m in REVIEW_MODULES:
        # 检查每个模块的关键标识词
        keywords = {
            "index": "大盘环境",
            "sentiment": "情绪周期",
            "mainline": "主线",
            "capital": "资金",
            "variables": "盘后变量",
            "combatmap": "作战地图",
        }
        kw = keywords.get(m, m)
        if kw not in content:
            issues.append({"kind": "WARN", "module": m, "reason": f"review.md 中未出现关键词 '{kw}'"})
    return issues


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    ymd_dir = Path(args.output_dir) / args.ymd
    if not ymd_dir.exists():
        print(f"ERROR: {ymd_dir} not found", file=sys.stderr)
        return 1

    issues = check_module_markers(ymd_dir) + check_review_md(ymd_dir)

    fails = [i for i in issues if i["kind"] == "FAIL"]
    warns = [i for i in issues if i["kind"] == "WARN"]

    print(f"=== verify_consistency ===")
    for i in issues:
        print(f"[{i['kind']}] {i['module']}: {i['reason']}")
    print(f"\n[PASS] {6 - len(fails) - len(warns)} modules / [FAIL] {len(fails)} / [WARN] {len(warns)}")
    return 1 if fails else (2 if warns else 0)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/verify_consistency.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/verify_consistency.py
git commit -m "feat(market-review): add verify_consistency.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: record_eval.py — 评估记录提取

**Files:**
- Create: `skills/market-review/scripts/record_eval.py`

- [ ] **Step 1: Create record_eval.py**

```python
"""record_eval.py · 从 review.md 提取关键判断写入 eval.json。

正则提取情绪周期、主线方向、仓位建议、场景数、风险提示。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SENTIMENT_PAT = re.compile(r'(情绪周期|周期阶段)[：:]\s*(.+?)(?:[。，\n]|$)')
MAINLINE_PAT = re.compile(r'(主线|主线方向)[：:]\s*(.+?)(?:[。，\n]|$)')
POSITION_PAT = re.compile(r'(仓位建议|仓位)[：:]\s*(.+?)(?:[。，\n]|$)')
SCENARIO_PAT = re.compile(r'(强势路径|中性路径|弱势路径)')
RISK_PAT = re.compile(r'(风险提示|警惕|陷阱)[：:]\s*(.+?)(?:[。]|\n\n|$)')


def extract_sentiment_stage(md: str) -> str | None:
    m = SENTIMENT_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_mainline(md: str) -> str | None:
    m = MAINLINE_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_position(md: str) -> str | None:
    m = POSITION_PAT.search(md)
    return m.group(2).strip() if m else None


def extract_scenarios(md: str) -> list[str]:
    return list(set(SCENARIO_PAT.findall(md)))


def extract_risks(md: str) -> list[str]:
    risks = []
    # 找"风险提示"后的列表项
    risk_section = re.search(r'风险提示[：:]\s*\n((?:\s*[-•]\s*.+\n?)+)', md)
    if risk_section:
        for line in risk_section.group(1).splitlines():
            cleaned = re.sub(r'^\s*[-•]\s*', '', line).strip()
            if cleaned:
                risks.append(cleaned)
    return risks[:5]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ymd", required=True, help="交易日 YYYY-MM-DD")
    p.add_argument("--output-dir", default="output", help="输出根目录")
    args = p.parse_args(argv)

    review_path = Path(args.output_dir) / args.ymd / "review.md"
    if not review_path.exists():
        print(f"ERROR: {review_path} not found", file=sys.stderr)
        return 1

    md = review_path.read_text(encoding="utf-8")

    eval_data = {
        "date": args.ymd,
        "market_review": {
            "sentiment_stage": extract_sentiment_stage(md),
            "mainline_direction": extract_mainline(md),
            "position_advice": extract_position(md),
            "scenarios": extract_scenarios(md),
            "risk_warnings": extract_risks(md),
        },
    }

    eval_path = Path(args.output_dir) / args.ymd / "eval.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"eval.json written to {eval_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Dry-run syntax check**

Run: `cd skills/market-review && python -c "import ast; ast.parse(open('scripts/record_eval.py').read()); print('Syntax OK')"`
Expected: `Syntax OK`

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/scripts/record_eval.py
git commit -m "feat(market-review): add record_eval.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 14: Reference docs — data-schema.md

**Files:**
- Create: `skills/market-review/references/data-schema.md`

- [ ] **Step 1: Create data-schema.md**

````markdown
# market-review · data.json 字段规约

## 通用字段

每个模块的 `data.json` 顶层必须包含：
- `module` (string): 模块名
- `ymd` (string): 交易日 YYYY-MM-DD

## index/data.json

```json
{
  "module": "index",
  "ymd": "2026-05-30",
  "index_data": {
    "<code>": {
      "name": "上证指数",
      "kline": [{"日期": "2026-05-30", "开盘": 3050.0, "最高": 3080.0, "最低": 3040.0, "收盘": 3065.0, "成交量": 12345678, "成交额": 123456789012}],
      "trend": "多头排列"
    }
  },
  "breadth": {"up": 2500, "down": 1800, "up_pct5": 120, "down_pct5": 30},
  "total_amount_yi": 8500.5
}
```

## sentiment/data.json

```json
{
  "module": "sentiment",
  "ymd": "2026-05-30",
  "limit_up_count": 45,
  "limit_down_count": 12,
  "max_consecutive_board": 6,
  "board_gradient": {"1": 20, "2": 10, "3": 5, "4": 3, "5": 1, "6": 1},
  "bomb_count": 15,
  "bomb_rate_pct": 25.0,
  "big_noodle_count": 3,
  "limit_up_sample": [],
  "limit_down_sample": [],
  "bomb_sample": []
}
```

## mainline/data.json

```json
{
  "module": "mainline",
  "ymd": "2026-05-30",
  "sector_flow_top20": [],
  "limit_up_by_sector": {"人工智能": 12, "机器人": 8, "新能源车": 5},
  "sector_count": 128
}
```

## capital/data.json

```json
{
  "module": "capital",
  "ymd": "2026-05-30",
  "northbound": {
    "today_net": 25.5,
    "recent_10d": [],
    "sz_recent_10d": []
  },
  "northbound_3d": [25.5, -10.2, 8.0],
  "lhb_count": 85,
  "lhb_sample": []
}
```

## variables/data.json

```json
{
  "module": "variables",
  "ymd": "2026-05-30",
  "us_market": {"dji": [], "nasdaq": [], "sp500": []},
  "hk_market": {"hsi": []},
  "commodities": {"crude_oil": [], "gold": []},
  "_note": "新闻/政策部分由 Agent 通过 WebSearch 获取并直接写入 report.md"
}
```

## combatmap/data.json (market_data.json)

```json
{
  "date": "2026-05-30",
  "index": {},
  "sentiment": {},
  "mainline": {},
  "capital": {},
  "variables": {},
  "_prereq_status": {"index": "ok", "sentiment": "ok", "mainline": "ok", "capital": "ok", "variables": "ok"}
}
```
````

- [ ] **Step 2: Commit**

```bash
git add skills/market-review/references/data-schema.md
git commit -m "feat(market-review): add data-schema.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 15: Reference docs — 6 module method guides

**Files:**
- Create: `skills/market-review/references/modules/index.md`
- Create: `skills/market-review/references/modules/sentiment.md`
- Create: `skills/market-review/references/modules/mainline.md`
- Create: `skills/market-review/references/modules/capital.md`
- Create: `skills/market-review/references/modules/variables.md`
- Create: `skills/market-review/references/modules/combatmap.md`

- [ ] **Step 1: Create references/modules/index.md**

````markdown
# index · 大盘环境诊断 · 方法论

> 本模块产出：各指数多空状态、量能台阶、涨跌家数比、情绪温度计
> 数据输入：`output/<ymd>/index/data.json`
> 输出文件：同目录 `report.md`，必须以 `<!-- REVIEW_MODULE_START module=index date=<ymd> -->` 开头

## 强约束

- 最低行数：30 行
- 必含 section：指数多空状态 / 量能分析 / 涨跌家数 / 情绪温度计
- 市场复盘不提个股

## 分析方法

### 各指数多空状态

| 指数 | 收盘价 | MA5 | MA20 | 排列状态 | 日涨跌幅 |
|------|--------|-----|------|---------|---------|
| 上证指数 | [F:index_data.sh000001.kline[-1].收盘] | 计算 | 计算 | [I:] | [F:] |
| 沪深300 | ... | ... | ... | ... | ... |
| 中证500 | ... | ... | ... | ... | ... |
| 中证1000 | ... | ... | ... | ... | ... |
| 创业板指 | ... | ... | ... | ... | ... |

判断：整体偏多/偏空/分化

### 量能分析

- 全市场成交额：[F:total_amount_yi] 亿
- 与前 5 日均量对比：[I:]（放量/缩量/持平）
- 量能台阶：[I:]（万亿以上/8000-10000亿/6000-8000亿/6000亿以下）

### 涨跌家数

| 指标 | 数值 |
|------|------|
| 上涨家数 | [F:breadth.up] |
| 下跌家数 | [F:breadth.down] |
| 涨跌比 | [C:breadth.up/breadth.down] |
| 涨幅>5% | [F:breadth.up_pct5] |
| 跌幅<-5% | [F:breadth.down_pct5] |

### 情绪温度计

根据涨跌家数比、涨>5%和跌<-5%家数判断：
- 极度恐惧 / 恐惧 / 中性 / 乐观 / 狂热
- 判定依据：[I:]

### 结论

- 一句话大盘诊断：[I:]
````

- [ ] **Step 2: Create references/modules/sentiment.md**

````markdown
# sentiment · 情绪周期定位 · 方法论

> 本模块产出：连板梯度、炸板率、溢价率、周期阶段判定
> 数据输入：`output/<ymd>/sentiment/data.json`
> 输出文件：同目录 `report.md`，必须以 `<!-- REVIEW_MODULE_START module=sentiment date=<ymd> -->` 开头

## 强约束

- 最低行数：30 行
- 必含 section：涨停板统计 / 连板梯队 / 情绪周期判定 / 辅证数据
- 市场复盘不提个股

## 分析方法

### 涨停板统计

| 指标 | 数值 |
|------|------|
| 涨停家数 | [F:limit_up_count] |
| 跌停家数 | [F:limit_down_count] |
| 炸板家数 | [F:bomb_count] |
| 炸板率 | [F:bomb_rate_pct]% |
| 大面股数量 | [F:big_noodle_count] |

### 连板梯队

| 连板数 | 家数 | 代表意义 |
|--------|------|---------|
| 6板+ | [F:board_gradient.6] | 空间高度 |
| 5板 | [F:board_gradient.5] | 次高 |
| 4板 | [F:board_gradient.4] | 中位 |
| 3板 | [F:board_gradient.3] | 低位 |
| 2板 | [F:board_gradient.2] | 首板进阶 |
| 1板 | [F:board_gradient.1] | 首板 |

最高连板：[F:max_consecutive_board] 板

### 情绪周期判定

根据连板高度、炸板率、大面股数综合判断：

| 阶段 | 特征 | 当前匹配 |
|------|------|---------|
| 冰点 | 涨停<20，最高板≤2，无大面 | ✅/❌ |
| 修复 | 涨停回升，炸板率下降 | ✅/❌ |
| 主升 | 涨停>50，梯队完整，最高板≥5 | ✅/❌ |
| 高位分歧 | 炸板率>30%，大面股增多 | ✅/❌ |
| 退潮 | 高标断板，涨停骤减 | ✅/❌ |

**判定**：[I:] 阶段，理由：[I:]

### 辅证信号
- 昨日涨停今日溢价情况：[I:]
- 是否出现极值信号（全部涨停<10 / 炸板率>50%）: [I:]
````

- [ ] **Step 3: Create references/modules/mainline.md**

````markdown
# mainline · 主线与支线识别 · 方法论

> 本模块产出：主线判定、主线状态、支线定位、持续性评估
> 数据输入：`output/<ymd>/mainline/data.json`
> 输出文件：同目录 `report.md`，必须以 `<!-- REVIEW_MODULE_START module=mainline date=<ymd> -->` 开头

## 强约束

- 最低行数：25 行
- 必含 section：板块资金排名 / 涨停归类 / 主线判定 / 支线分析
- 市场复盘不提个股

## 分析方法

### 板块资金排名（Top 10）

| 排名 | 板块 | 净流入 | 涨停家数 |
|------|------|--------|---------|
| 1 | [I:] | [F:] | [I:] |
| ... | ... | ... | ... |

数据来源：`sector_flow_top20` + `limit_up_by_sector`

### 主线判定

主线定义：涨停家数最多 + 梯队最完整 + 有容量中军

- 第一主线：[I:]（涨停 [I:] 只）
- 第二主线：[I:]（涨停 [I:] 只）

### 主线状态

| 状态 | 特征 | 当前判定 |
|------|------|---------|
| 加强 | 涨停数增加，扩散至产业链上下游 | ✅/❌ |
| 分歧 | 龙头分歧但未断板，内部涨跌分化 | ✅/❌ |
| 转弱 | 涨停骤减，龙头断板，资金流出 | ✅/❌ |

判定：[I:]

### 支线分析

| 支线 | 定位 | 持续性 |
|------|------|--------|
| [I:] | 卡位轮动/新方向萌芽/补涨 | [I:] |

### 结论

- 主战场：[I:]
- 操作建议：[I:]（只描述方向，不提个股）
````

- [ ] **Step 4: Create references/modules/capital.md**

````markdown
# capital · 资金行为监测 · 方法论

> 本模块产出：北向资金解读、龙虎榜信号
> 数据输入：`output/<ymd>/capital/data.json`
> 输出文件：同目录 `report.md`，必须以 `<!-- REVIEW_MODULE_START module=capital date=<ymd> -->` 开头

## 强约束

- 最低行数：25 行
- 必含 section：北向资金流向 / 北向行业偏好 / 龙虎榜信号
- 市场复盘不提个股

## 分析方法

### 北向资金

| 指标 | 数值 |
|------|------|
| 当日净买卖 | [F:northbound.today_net] 亿 |
| 连续3日 | [I:]（判断持续流入/流出/转向） |

### 北向行业偏好

根据北向流入行业分布判断加减仓方向：[I:]

### 龙虎榜信号

- 上榜家数：[F:lhb_count]
- 机构行为：[I:]（机构净买入居多/净卖出居多/买卖均衡）
- 游资行为：[I:]（顶级游资活跃/游资防守避险/游资分歧）
- 机构与游资共振/背离：[I:]

### 结论

- 资金面整体信号：[I:]（偏多/偏空/中性）
````

- [ ] **Step 5: Create references/modules/variables.md**

````markdown
# variables · 盘后变量汇总 · 方法论

> 本模块产出：海外市场收盘、政策新闻影响评级
> 数据输入：`output/<ymd>/variables/data.json` + Agent WebSearch
> 输出文件：同目录 `report.md`，必须以 `<!-- REVIEW_MODULE_START module=variables date=<ymd> -->` 开头

## 强约束

- 最低行数：20 行
- 新闻部分由 Agent 通过 WebSearch 获取
- 必含 section：海外市场 / 政策与新闻 / 影响评级
- 市场复盘不提个股

## 分析方法

### 海外市场收盘

| 指数 | 收盘价 | 涨跌幅 |
|------|--------|--------|
| 道琼斯 | [F:] | [F:] |
| 纳斯达克 | [F:] | [F:] |
| 标普500 | [F:] | [F:] |
| 恒生指数 | [F:] | [F:] |
| 原油 | [F:] | [F:] |
| 黄金 | [F:] | [F:] |

### 政策与新闻

Agent 通过 WebSearch 获取当日盘后重大政策、行业新闻、公告摘要。每条需包含：
- 标题
- 来源
- 一句话摘要

### 影响评级

| 事件 | 影响级别 | 影响方向 |
|------|---------|---------|
| [I:] | 决定全局/影响板块/仅影响个股 | 利多/利空/中性 |

### 预期差清单

列出可能引发明日超预期的变量：[I:]
````

- [ ] **Step 6: Create references/modules/combatmap.md**

````markdown
# combatmap · 明日作战地图 · 方法论 + 合成 review.md 指引

> 本模块产出：三种场景推演 + 仓位建议 + 风险提示
> 输入：前五个模块的 data.json（通过 `market_data.json` 汇总）
> 输出文件：
>   1. `output/<ymd>/combatmap/report.md`（模块六独立报告）
>   2. `output/<ymd>/review.md`（合成完整复盘，Agent 在本模块写完后合成）

## 强约束

- 最低行数：40 行
- 必含 section：关键参数总览 / 三种场景推演 / 仓位建议 / 风险提示
- 市场复盘绝不提个股
- 仓位建议必须引用前五模块的综合信息，不可凭空给出

## 合成策略

### 关键参数总览

| 维度 | 来源模块 | 当前值 |
|------|---------|--------|
| 大盘环境 | index | [I:]（偏多/偏空/震荡） |
| 情绪周期 | sentiment | [I:]（冰点/修复/主升/高位分歧/退潮） |
| 主线方向 | mainline | [I:]（板块名 + 加强/分歧/转弱） |
| 北向资金 | capital | [I:]（持续流入/流出/转向） |
| LHB信号 | capital | [I:]（机构游资共振/分歧） |

### 三种场景推演

#### 强势路径
- 触发条件：[T:]（精确到点位、量能、时间）
- 应对策略：[I:]
- 适合仓位：[I:]

#### 中性路径
- 触发条件：[T:]
- 应对策略：[I:]
- 适合仓位：[I:]

#### 弱势路径
- 触发条件：[T:]
- 应对策略：[I:]
- 适合仓位：[I:]

### 仓位建议

- 进攻（7成以上）/ 均衡（4-6成）/ 防御（2-3成）/ 空仓
- 建议：[I:]，理由：[I:]

### 风险提示

当前阶段最需要警惕的陷阱（如流动性衰竭、高标A杀、消息兑现）：[I:]

## Agent 合成 review.md 流程

写完全部 6 个模块的 report.md 后，Agent 合成 `output/<ymd>/review.md`：

1. 读全部 6 份 report.md
2. 在 review.md 开头写 `<!-- REVIEW_MODULE_START module=review date=<ymd> -->`
3. 第一段：「今日复盘摘要」——提取各模块核心结论（2-3 句每个模块）
4. 第二段：「明日作战地图」——直接引用 combatmap/report.md 的三种路径 + 仓位建议
5. 第三段：「关键监控指标」——明早需要第一时间看的数据点
6. 尾部写「仅供复盘参考，不构成投资建议」
````

- [ ] **Step 7: Commit all 6 module references**

```bash
git add skills/market-review/references/modules/
git commit -m "feat(market-review): add 6 module method reference docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 16: SKILL.md

**Files:**
- Create: `skills/market-review/SKILL.md`

- [ ] **Step 1: Create SKILL.md**

````markdown
---
name: market-review
description: |
  A 股市场每日复盘系统。对用户提到的盘面复盘/市场分析/明日预判需求主动调用。
  覆盖：大盘环境、情绪周期、主线识别、资金监测、盘后变量、明日作战地图。
  仅供研究参考，不构成证券投资咨询业务，不构成投资建议。
metadata:
  argument-hint: [--force] [--module <模块名>]
---

# market-review · A 股市场每日复盘系统

## 调用语法

```
/market-review [--force] [--module <模块名>]
```

- 不带 `--module` 默认合成全部（6 模块 + review.md）
- 模块名支持中英别名（详见 [config.yaml](config.yaml)）
- `--force` 覆盖 TTL，强制重跑

### 模块清单

| 模块 | 主名 | TTL |
|---|---|---|
| 大盘环境诊断 | `index` | 1 天 |
| 情绪周期定位 | `sentiment` | 1 天 |
| 主线与支线识别 | `mainline` | 1 天 |
| 资金行为监测 | `capital` | 1 天 |
| 盘后变量汇总 | `variables` | 1 天 |
| 明日作战地图 | `combatmap` | 1 天 |

### 自然语言路由

| 用户说 | 翻译 |
|---|---|
| 开始今日复盘 | `/market-review` |
| 今天市场怎么样 | `/market-review` |
| 复盘一下今天大盘 | `/market-review` |
| 明天能不能做 | `/market-review` |
| 今天的情绪周期是什么阶段 | `/market-review --module sentiment` |
| 重新跑一下今天复盘 | `/market-review --force` |

## 强约束（含 Why）

| ID | 约束 | Why |
|---|---|---|
| R1 | 当日数据当日有效，`--date` 默认取最近交易日，不加 `--force` 就复用已有 data.json | 同一交易日盘后数据不会变，重复拉取浪费 API 配额 |
| R2 | `--force` 是打破 R1 的唯一方式，可作用到指定模块 `--force --module index` | 避免 Agent "想做完整一点"就自作主张全部重跑 |
| R3 | 模块间 report.md 彼此不引用（不写"见模块一的结论"），只引用 data.json 中的原始数据 | 模块解耦的核心保障 |
| R4 | 合成 review.md 时各模块独立应用 R1/R2 | 模块六每次都重写（依赖前五模块最新输出） |
| R5 | 单模块永不输出"明日作战地图"或仓位建议；仓位建议仅模块六产出 | 仓位需要综合全部模块信息 |
| R6 | 每个模块 report.md 必须以 `<!-- REVIEW_MODULE_START -->` 段开头，标注模块名和交易日 | 合成时验证模块完整性和日期对齐 |
| R7 | 市场复盘绝不提个股 | 核心边界铁律 |
| R8 | Python 脚本只管 fetch 和校验，不生成 report.md | Agent 是 report.md 的唯一生产者 |
| R9 | verify_facts 校验单模块 data.json↔report.md；verify_consistency 仅合成后跑 | 跨模块一致性只在合并后才有意义 |

## Agent 执行流程

### 完整复盘（例：`/market-review`）

```
1. 跑 python scripts/run_review.py --date <today> [--force]
2. 解析 stdout 输出（JSONL）：
   - status=reuse  → 直接读 <module>/<ymd>/report.md 给用户
   - status=data_ready → 读 data.json + references/modules/<m>.md
                         写 <module>/<today>/report.md
                         跑 python scripts/verify_facts.py --module <m> --ymd <today>
3. 对每个 needs_report_md=true 的模块循环执行步骤 2
4. Agent 读 6 份 report.md，合成 output/<today>/review.md
5. 跑 python scripts/verify_consistency.py --ymd <today>
6. 跑 python scripts/record_eval.py --ymd <today>
7. 把 review.md 内容反馈给用户
```

### 单模块（例：`/market-review --module sentiment`）

```
1. 跑 python scripts/run_review.py --date <today> --module sentiment [--force]
2. 解析 stdout：
   - status=reuse → 直接读 report.md
   - status=data_ready → Agent 写 report.md → verify_facts
3. 把 report.md 内容反馈给用户
```

## 输出结构

```
output/
└── <YYYY-MM-DD>/
    ├── index/{data.json, report.md}
    ├── sentiment/{data.json, report.md}
    ├── mainline/{data.json, report.md}
    ├── capital/{data.json, report.md}
    ├── variables/{data.json, report.md}
    ├── combatmap/{data.json, market_data.json, report.md}
    ├── review.md
    └── eval.json
```

## 配置

模块 TTL、别名、默认行为见 [config.yaml](config.yaml)。用户可直接编辑。

## 关键文档

| 何时读 | 文件 |
|---|---|
| 写某个模块 report.md 时 | [references/modules/<m>.md](references/modules/) |
| 写 data.json 时 | [references/data-schema.md](references/data-schema.md) |
| 配置改动 | [config.yaml](config.yaml) |
````

- [ ] **Step 2: Commit**

```bash
git add skills/market-review/SKILL.md
git commit -m "feat(market-review): add SKILL.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 17: Evals

**Files:**
- Create: `skills/market-review/evals/README.md`
- Create: `skills/market-review/evals/evals.json`

- [ ] **Step 1: Create evals/README.md**

```markdown
# market-review · Evals

## 运行方式

在 skill 目录下通过 Agent 交互触发，人工验证输出。

## 测试场景

见 `evals.json`
```

- [ ] **Step 2: Create evals/evals.json**

```json
{
  "skill_name": "market-review",
  "evals": [
    {
      "id": 1,
      "name": "default-review",
      "prompt": "开始今日复盘",
      "expected_output": "Skill triggers and runs the default review mode for the latest trading day. Each module either reuses TTL-fresh data.json or fetches new data. Agent writes per-module report.md, synthesizes review.md, runs verify_consistency and record_eval.",
      "files": [],
      "assertions": [
        {
          "text": "Invokes scripts/run_review.py with --module review",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "Each module directory under output/<ymd>/ contains data.json and report.md",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "review.md exists at output/<ymd>/review.md with '今日复盘摘要' and '明日作战地图' sections",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "eval.json exists at output/<ymd>/eval.json",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "verify_consistency.py exits 0 (all PASS)",
          "passed": null,
          "evidence": ""
        }
      ]
    },
    {
      "id": 2,
      "name": "single-module",
      "prompt": "今天的情绪周期是什么阶段",
      "expected_output": "Skill triggers and runs ONLY the `sentiment` module. Produces sentiment/<ymd>/report.md but does NOT produce review.md or run other modules.",
      "files": [],
      "assertions": [
        {
          "text": "Invokes scripts/run_review.py with --module sentiment",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "sentiment/<ymd>/report.md exists",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "Other module directories are not created in this run",
          "passed": null,
          "evidence": ""
        }
      ]
    },
    {
      "id": 3,
      "name": "force-refresh",
      "prompt": "重新跑一下今天复盘",
      "expected_output": "Skill recognizes '重新跑下' as --force, bypasses TTL for all modules, fetches fresh data and regenerates all reports.",
      "files": [],
      "assertions": [
        {
          "text": "Invokes scripts/run_review.py with --force",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "JSONL output contains 'data_ready' (not 'reuse') for all modules, proving --force took effect",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "Fresh review.md is produced",
          "passed": null,
          "evidence": ""
        }
      ]
    },
    {
      "id": 4,
      "name": "no-stock-mention",
      "prompt": "开始今日复盘",
      "expected_output": "review.md must NOT mention any individual stock by name or code (R7). Should reference sectors and aggregate data only.",
      "files": [],
      "assertions": [
        {
          "text": "review.md contains no 6-digit stock codes",
          "passed": null,
          "evidence": ""
        },
        {
          "text": "review.md references sectors/indices (e.g., '人工智能板块') but not individual stocks",
          "passed": null,
          "evidence": ""
        }
      ]
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add skills/market-review/evals/
git commit -m "feat(market-review): add evals

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 18: Integration — update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add market-review to current skills list**

Read [CLAUDE.md](CLAUDE.md) line 5-7.

Change:
```markdown
## 当前 skills

- `skills/stock-analysis/` — A 股个股深度研究系统 v4.0（模块化：7 个独立分析模块 + 1 个合成层，按 TTL 复用快照）
```

To:
```markdown
## 当前 skills

- `skills/stock-analysis/` — A 股个股深度研究系统 v4.0（模块化：7 个独立分析模块 + 1 个合成层，按 TTL 复用快照）
- `skills/market-review/` — A 股市场每日复盘系统（模块化：6 个独立分析模块按 TTL=1 天复用快照，合成每日作战地图）
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add market-review to skill list

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

Before executing, verify:
1. All 18 tasks have exact file paths
2. All code blocks are complete (no "..." elisions in key logic)
3. All commands have expected output
4. Module directory structure matches SKILL.md
5. Combatmap depends on modules 1-5 (ordered last in run_review.py)

---

## Execution Order

Tasks 1-3 (scaffold + lib + requirements) can run in parallel.
Tasks 4-9 (fetch scripts) can run in parallel after Task 2.
Tasks 10-13 (orchestration + verify + eval) can run in parallel after Task 3.
Tasks 14-17 (docs + SKILL.md + evals) can run in parallel.
Task 18 (CLAUDE.md) runs last.

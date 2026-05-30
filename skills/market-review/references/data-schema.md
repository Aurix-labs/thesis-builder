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

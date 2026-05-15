# data.json Schema

Phase 1 输出的 `output/<股票名>_<代码>/<YYYY-MM-DD>/data.json` 的结构。
Phase 2/3 的 AI 读取此 JSON 提取所需数据。

## 顶层字段

```json
{
  "meta": { ... },
  "quote": { ... },
  "kline_daily": [ ... ],
  "financials": [ ... ],
  "business_segments": [ ... ],
  "top_holders": [ ... ],
  "news": [ ... ],
  "blocks": { ... }
}
```

## meta

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | ✓ | 6 位 A 股代码（"002594"） |
| name | string | ✓ | 公司中文简称（"比亚迪"） |
| exchange | string | ✓ | "SH" / "SZ" / "BJ" |
| industry | string | – | 申万一级行业 |
| as_of | string | ✓ | 数据截止日 YYYY-MM-DD |
| source | string | ✓ | "akshare" / "mcp" / "manual" |

## quote

| 字段 | 类型 | 说明 |
|------|------|------|
| price | number | 最新收盘价 |
| change_pct | number | 当日涨跌幅 (-1.84 表示 -1.84%) |
| market_cap | number | 总市值（元） |
| pe | number | 滚动 PE |
| pb | number | 最新 PB |

## kline_daily

数组，每行 `[date, open, close, low, high, volume]`。

**OHLC 顺序约定：** `[open, close, low, high]`（与 ECharts candlestick series 默认一致）。
**禁止：** OHLC 中改用 `[open, high, low, close]`。

示例：
```json
[
  ["2023-05-15", 215.30, 218.50, 214.00, 219.80, 12340000],
  ["2023-05-16", 218.50, 220.10, 217.20, 221.50, 9870000]
]
```

最近 3 年 ≈ 730 行。

## financials

每年一行：
```json
[
  { "year": 2025, "revenue": 7771.0, "net_profit": 402.5, "gross_margin": 0.182, "roe": 0.241 },
  { "year": 2024, "revenue": 6023.0, "net_profit": 300.4, "gross_margin": 0.180, "roe": 0.218 }
]
```

数值单位：营收/净利润为亿元；毛利率/ROE 为小数（0.182 表示 18.2%）。

## business_segments

```json
[
  { "name": "汽车及电池", "revenue_share": 0.78, "gross_margin": 0.205 },
  { "name": "手机部件", "revenue_share": 0.20, "gross_margin": 0.085 }
]
```

## top_holders

```json
[
  { "rank": 1, "name": "比亚迪股份有限公司", "share_pct": 0.179, "shares": 521000000 }
]
```

## news

```json
[
  { "title": "比亚迪 4 月销量同比 +21%", "date": "2026-05-08", "source": "新浪财经", "url": "..." }
]
```

## blocks（兼容旧版）

原 `stock_full_report.py` 的 `blocks` 字段保留作为低级 raw 数据透传，供 agent 按需深挖。
新代码应优先使用上面的标准字段。

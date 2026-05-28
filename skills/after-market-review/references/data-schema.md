# after-market-review data.json Schema

`data.json` is the auditable fact package for one stock and one completed trading day.

Top-level required fields:

| Field | Type | Description |
|---|---|---|
| `skill` | string | Always `after-market-review` |
| `code` | string | 6-digit A-share code |
| `name` | string | Chinese short name |
| `trade_date` | string | `YYYY-MM-DD` completed trading date |
| `generated_at` | string | ISO timestamp with UTC+8 offset |
| `data_status` | object | Status per fact layer |
| `market_context` | object | Market indices and broad risk appetite |
| `sector_context` | object | Industry or concept context |
| `stock_trade` | object | Daily and intraday stock trading facts |
| `tick_trade` | object | Tick or large-order behavior |
| `funds_context` | object | Fund-flow and liquidity clues |
| `event_context` | object | News, announcements, and catalysts |
| `sentiment_context` | object | Popularity, keywords, LHB, topic heat |
| `derived` | object | Script-derived intermediate signals |

`data_status` values:

| Value | Meaning |
|---|---|
| `ok` | Layer is complete enough for normal use |
| `partial` | Layer has usable data and documented gaps |
| `unavailable` | Source returned no data or does not support the request |
| `error` | Fetch or normalization failed; see `manifest.json.errors` |

`tick_trade.summary` required fields when `data_status.tick_trade` is `ok` or `partial`:

| Field | Type |
|---|---|
| `large_buy_count` | integer |
| `large_sell_count` | integer |
| `large_buy_amount` | number |
| `large_sell_amount` | number |
| `net_large_amount` | number |
| `peak_buy_windows` | list |
| `peak_sell_windows` | list |
| `tail_behavior` | string |

`derived` should contain string labels only. It must not contain final investment conclusions.

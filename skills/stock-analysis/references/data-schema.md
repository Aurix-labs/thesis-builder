# data.json Schema · v4.0 模块化

每个模块的 `<stock>/<module>/<ymd>/data.json` 是该模块独立的字段集合。

通用顶层字段（所有模块都有）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `module` | string | 模块名（chain/rubric/...） |
| `ymd` | string | 数据日 YYYY-MM-DD |
| `meta` | object | 标的元信息（code/name/industry） |
| `quote` | object | 行情快照（price/market_cap/pe/pb） |

## chain
`meta`、`quote`、`business_segments`、`news`

## rubric
`meta`、`quote`、`financial_abstract`、`top_holders`、`margin`

## elasticity
`meta`、`quote`、`financial_abstract`、`business_segments`

## risk
`meta`、`quote`、`financial_abstract`、`kline_daily`（近 180 天）、`notice`、`news`
额外产物：`anomalies.md` + `anomalies.json`

## valuation
`meta`、`quote`、`financial_abstract`、`research`、`recommend`、`kline_daily`（近 30 天）

## flow-tech
`meta`、`quote`、`kline_daily`（近 365 天）、`top_holders`、`fund_flow`、`margin`

## peers
`self`（本公司）+ `peers`（同业列表，每项含 `code`/`meta`/`quote`/`financial_abstract`）
额外产物：`peers.txt`（每行一个同业代码）

## report（合成层）
不直接拉数据。产物：`report.md`、`fact-check.md`、`report.html`、`manifest.json`（记录引用的各模块 ymd）

## meta 子结构
| 字段 | 说明 |
|---|---|
| `code` | 6 位代码 |
| `name` | 中文简称 |
| `industry` | 行业（chain/rubric 等模块从 stock_individual_info_em 提取） |

## quote 子结构
| 字段 | 说明 |
|---|---|
| `price` | 最新价 |
| `market_cap` | 总市值（元） |
| `pe` | 滚动 PE |
| `pb` | 最新 PB |

## kline_daily 子结构
list[dict]，每行含 `日期`/`开盘`/`收盘`/`最高`/`最低`/`成交量`（akshare stock_zh_a_hist 原始字段）。

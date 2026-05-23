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

## summary 契约（v5 新增）

每个模块的 `<m>/<ymd>/data.json` 在 LLM 分析阶段（写 report.md 同时）必须追加 `summary` 子键，存放该模块的结构化判断（评分 / 目标价 / 弹性树简化形态 / 风险等级等）。

**为什么需要**：v4 之前这些判断只活在 report.md 散文里，HTML 渲染时只能由 agent 重新抽取——v5 改用 `scripts/render_html.py` 渲染，必须有可靠的字段路径可读。

**为什么不另开 summary.json**：

- 模块边界：一个模块 = 一个文件夹 = 一份 data.json 契约，最少文件数
- 与 R5（模块独立性）一致：每个模块自己拥有"原料 + 判断"完整快照

具体字段见各 [modules/<m>.md](modules/) 的"summary 必填字段"小节。

## merged data.json 必填字段（render_html.py 强制）

由 `compose_report.py merge_data_json()` 合并 7 个模块的 data.json 产出 `report/<ymd>/data.json`，
顶层 namespace = `{ chain, rubric, elasticity, risk, valuation, flow_tech, peers, meta }`
（注意 `flow-tech` → `flow_tech`，连字符在 Python/Jinja 标识符里友好）。

**render_html.py 启动时校验以下字段（缺失或类型错 → fail-hard）：**

| 路径 | 类型 | 备注 |
|---|---|---|
| `meta.stock_code` | str | compose 注入 |
| `meta.stock_name` | str | compose 注入 |
| `meta.ymd` | str (YYYY-MM-DD) | compose 注入 |
| `meta.time_utc8` | str (HH:MM) | compose 注入 |
| `meta.session_id` | str (0xXXXX) | compose 注入 |
| `meta.data_as_of` | str (YYYY-MM-DD) | compose 注入（= max(各模块 ymd)） |
| `meta.research_status` | str | compose 注入（首次覆盖 / 持续跟踪） |
| `chain.summary.industry_phase` | str | LLM |
| `rubric.summary.total` | int [0,100] | LLM |
| `rubric.summary.passed` | int [0,20] | LLM |
| `rubric.summary.dimensions` | list (6 条) | LLM |
| `rubric.summary.dimensions[*].{name,points_max,points_got}` | str/int/int | LLM |
| `rubric.summary.financials_table` | list (≥3) | LLM |
| `rubric.summary.financials_table[*].{year,revenue,net_profit,gross_margin,roe}` | int/float/float/float/float | LLM |
| `rubric.summary.revenue_breakdown` | list (≥1) | LLM |
| `rubric.summary.revenue_breakdown[*].{name,value}` | str/float | LLM |
| `elasticity.summary.tree_children` | list (≥1) | LLM |
| `elasticity.summary.tree_children[*].{name,ratio,margin,factor,is_core}` | str/str/str/str/bool | LLM |
| `risk.summary.level` | str ∈ {低,中,高,极高} | LLM |
| `valuation.summary.targets.{short,mid,long,mid_change_pct,base_date}` | float/float/float/float/str | LLM |
| `valuation.summary.rr` | float | LLM |
| `flow_tech.kline_daily` | list (≥120 行) | fetch |
| `peers.summary.list` | list (≥1) | LLM |
| `peers.summary.list[*].{code,name}` | str/str | LLM |

校验实现：[scripts/lib/render_schema.py](../scripts/lib/render_schema.py)。

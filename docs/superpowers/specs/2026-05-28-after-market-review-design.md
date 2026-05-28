# after-market-review · 盘后复盘 Skill 设计

**日期：** 2026-05-28  
**作者范畴：** skills/after-market-review  
**状态：** 已确认设计，待实施计划  
**定位：** 独立于 `stock-analysis` 的短线走势、市场情绪与盘后逻辑复盘 skill

## 背景

`stock-analysis` 的定位是 A 股个股中期研究：产业链、公司质地、业绩弹性、风险、估值、资金技术面、同业对标与合成研究报告。它回答的是“这家公司中期值不值得研究、赔率如何、风险在哪里”。

新的 `after-market-review` 不应混入这个体系。它面向的是另一个问题：某只股票在最近一个交易日为什么这么走。用户希望它在盘后读取当天市场、板块、个股交易、分时、分笔大单、新闻公告与情绪线索，对当日走势做短线复盘，并给出次日需要观察的价位和信号，但第一版不写交易计划。

## 目标

1. 创建独立 skill：`skills/after-market-review/`。
2. 默认支持单股最近交易日盘后复盘，例如“复盘 002594”。
3. 第一版输出 `Markdown` 报告，同时结构化落盘 `data.json` 和 `manifest.json`。
4. 按股票和交易日永久复用历史复盘；用户明确说“重新复盘/刷新/强制更新”才覆盖。
5. 数据主干采用“交易数据 + 新闻公告验证”，舆情和题材热度作为辅助层，后续可逐步增强。
6. 引入分笔/逐笔成交的大单行为分析，用于识别拉升、砸盘、尾盘抢筹等盘口证据。
7. 大单判定规则必须可配置，不写死在脚本中。
8. 次日部分只写观察点，不给买入、卖出、加仓、减仓等交易指令。

## 非目标

- 不扩展或修改 `stock-analysis` 的模块体系。
- 不生成 HTML；第一版只产 `report.md`。
- 不做市场异动自动筛选；第一版只做用户指定单股。
- 不做明确短线交易计划。
- 不依赖付费数据源。
- 不保证所有情绪/新闻接口稳定可用；必须支持分层降级。
- 不把资金流、大单或情绪数据当作单一决定性解释。

## 外部数据依据

第一版以 AkShare 免费公开数据为主要结构化来源，网页搜索仅作为公告和新闻补充验证层。设计时参考的官方能力包括：

- A 股分钟线、分时、分笔、个股新闻、人气榜/热门关键词等股票数据接口：<https://akshare.akfamily.xyz/data/stock/stock.html>
- 指数日线与市场指数数据接口：<https://akshare.akfamily.xyz/data/index/index.html>

实施时必须以本机安装的 AkShare 版本实测为准。若接口名称、字段或可取历史范围与文档不一致，脚本应记录 `data_status` 并降级，而不是让报告使用未经验证的推断。

## 用户入口

默认自然语言触发：

| 用户说法 | 解释 |
|---|---|
| `复盘 002594` | 对 002594 最近一个已收盘交易日做复盘 |
| `盘后复盘 比亚迪` | 解析股票名，对最近交易日做复盘 |
| `重新复盘 002594` | 覆盖同一交易日已有快照，强制刷新 |
| `刷新一下 002594 的复盘` | 同上 |

第一版不暴露复杂命令参数。内部脚本可支持 `--force`、`--trade-date` 和 `--output-dir`，其中 `--trade-date` 主要用于测试和将来扩展，不作为用户默认入口宣传。

## 输出结构

```
output/
└── <股票名>_<代码>/
    └── after-market-review/
        └── <trade_date>/
            ├── data.json
            ├── manifest.json
            └── report.md
```

缓存规则：

- 若 `report.md` 已存在且用户未表达刷新意图，直接复用该报告。
- 若用户表达刷新意图，重新采集数据、覆盖 `data.json` / `manifest.json` / `report.md`。
- 若数据采集完成但报告写作失败，保留 `data.json` 和错误状态，避免丢失事实包。

## 架构

`after-market-review` 采用“脚本管事实，agent 管解释”的边界：

```
用户：复盘 002594
  ↓
scripts/run_review.py
  ↓
确定股票、最近交易日、输出目录、缓存状态
  ↓
采集 7 层事实数据
  ↓
落盘 data.json + manifest.json
  ↓
agent 读取 data.json + references/review-method.md
  ↓
写 report.md
```

建议目录：

```
skills/after-market-review/
├── SKILL.md
├── config.yaml
├── references/
│   ├── review-method.md
│   ├── data-schema.md
│   └── source-policy.md
├── scripts/
│   ├── run_review.py
│   ├── fetch_market.py
│   ├── fetch_sector.py
│   ├── fetch_stock_trade.py
│   ├── fetch_tick_trade.py
│   ├── fetch_funds.py
│   ├── fetch_events.py
│   ├── fetch_sentiment.py
│   └── lib/
└── evals/
```

`run_review.py` 是脚本层唯一入口。各 `fetch_*.py` 只负责拉取、清洗、聚合事实，不写最终结论。

## 七层事实包

### 1. market_context

用途：判断当天是普涨、普跌、结构性行情，还是指数平淡但题材活跃。

数据：

- 上证指数、深证成指、创业板指、沪深 300 等指数涨跌。
- 成交额、振幅、近几日量能对比。
- 可用时记录主要指数日内走势。

### 2. sector_context

用途：判断个股是跟随板块、强于板块、弱于板块，还是独立异动。

数据：

- 所属行业/概念板块当日涨跌幅、排名、成交额。
- 板块内上涨/下跌家数。
- 板块领涨股、领跌股。
- 个股相对行业和指数的强弱。

### 3. stock_trade

用途：构成复盘主轴，解释当天价格路径。

数据：

- 当日日 K：开盘、最高、最低、收盘、涨跌幅、振幅、成交额、成交量、换手率。
- 近 5 / 20 日均量、均额、涨跌幅对比。
- 1 分钟线或可用分钟线：用于拆解开盘、上午、午后、尾盘节奏。
- 脚本派生 `intraday_pattern`，例如“高开回落后午后再拉升”“低开低走尾盘修复”。

### 4. tick_trade

用途：识别分笔/逐笔成交中的大单行为，作为盘口证据。

数据：

- 分笔或大单分时成交：成交时间、成交价格、成交量、成交额、买卖盘性质。
- 大单样本。
- 大单按时间窗聚合后的买卖强度。
- 尾盘盘口行为。

大单规则由 `config.yaml` 控制，第一版默认：

```yaml
large_order:
  amount_min: 1000000
  top_quantile: 0.95
  window_minutes: 10
  include_call_auction: true
```

入选规则：单笔成交额 `>= amount_min`，或进入当日单笔成交额前 `top_quantile` 分位，满足任一条件即作为大单。这样同时兼顾大市值股票的绝对成交规模和小市值股票的相对成交尺度。

报告使用方式：

- 判断拉升阶段是否有连续主动买入。
- 判断回落阶段是缩量回落还是大单集中卖出。
- 判断尾盘是否有抢筹或砸盘。
- 若股价走势与大单方向不一致，明确提示“走势与盘口证据不一致”。

### 5. funds_context

用途：提供资金行为线索，但不把资金流神化成唯一因果。

数据：

- 主力资金流向、超大单/大单/中单/小单等可用字段。
- 成交额、换手率和量比。
- 可用时纳入融资融券余额或当日变动。
- 若资金流接口不可用，用成交额、换手率和分笔大单作为替代证据。

### 6. event_context

用途：验证走势背后的公告、新闻、政策、行业催化或公司事件。

数据：

- 个股新闻。
- 公司公告或重要事项。
- 行业新闻和政策催化。
- 网页搜索补充材料。

事件分类：

- `verified_driver`：能较强解释当天走势的已验证主因。
- `possible_catalyst`：可能有影响，但证据链不足。
- `unsupported_rumor`：有市场传闻或情绪提及，但缺少可靠证据。

报告必须区分“已验证事件”和“可能催化”。没有证据时写“暂无明确事件证据”，不能硬编原因。

### 7. sentiment_context

用途：解释短线情绪，不替代交易数据和事件验证。

数据：

- 人气榜或排名变化。
- 热门关键词。
- 龙虎榜是否上榜及席位线索。
- 题材热度或概念活跃度。

第一版 `sentiment_context` 是辅助层。若不可用，不影响主报告生成。

## data.json 契约

顶层结构：

```json
{
  "skill": "after-market-review",
  "code": "002594",
  "name": "比亚迪",
  "trade_date": "2026-05-28",
  "generated_at": "2026-05-28T18:10:00+08:00",
  "data_status": {
    "market_context": "ok",
    "sector_context": "ok",
    "stock_trade": "ok",
    "tick_trade": "partial",
    "funds_context": "ok",
    "event_context": "ok",
    "sentiment_context": "partial"
  },
  "market_context": {},
  "sector_context": {},
  "stock_trade": {},
  "tick_trade": {},
  "funds_context": {},
  "event_context": {},
  "sentiment_context": {},
  "derived": {}
}
```

`data_status` 取值：

| 状态 | 含义 |
|---|---|
| `ok` | 该层数据完整可用 |
| `partial` | 该层部分可用，报告可引用但必须说明缺口 |
| `unavailable` | 数据源无数据或接口不支持 |
| `error` | 采集异常，错误写入 `manifest.json` |

`tick_trade` 示例：

```json
{
  "config": {
    "amount_min": 1000000,
    "top_quantile": 0.95,
    "window_minutes": 10,
    "include_call_auction": true
  },
  "summary": {
    "large_buy_count": 18,
    "large_sell_count": 11,
    "large_buy_amount": 86000000,
    "large_sell_amount": 54000000,
    "net_large_amount": 32000000,
    "peak_buy_windows": [
      {"window": "10:10-10:20", "amount": 24000000, "price_change_pct": 1.2}
    ],
    "peak_sell_windows": [
      {"window": "09:40-09:50", "amount": 18000000, "price_change_pct": -0.8}
    ],
    "tail_behavior": "尾盘大单净买入"
  },
  "large_orders_sample": []
}
```

`derived` 示例：

```json
{
  "intraday_pattern": "高开回落后午后再拉升",
  "relative_strength": "强于行业且强于主要指数",
  "volume_price_signal": "放量上涨",
  "event_match_level": "medium",
  "sentiment_heat": "rising"
}
```

`derived` 是脚本计算的中间判断，不是最终结论。最终“背后逻辑”由 agent 综合证据写入 `report.md`。

## manifest.json 契约

`manifest.json` 记录来源、调用、错误和复用状态，方便审计：

```json
{
  "skill": "after-market-review",
  "code": "002594",
  "name": "比亚迪",
  "trade_date": "2026-05-28",
  "force": false,
  "sources": [
    {"layer": "stock_trade", "api": "akshare.stock_zh_a_hist_min_em", "status": "ok"},
    {"layer": "tick_trade", "api": "akshare.stock_intraday_sina", "status": "partial"}
  ],
  "errors": [],
  "generated_files": ["data.json", "manifest.json", "report.md"]
}
```

## config.yaml

第一版配置：

```yaml
large_order:
  amount_min: 1000000
  top_quantile: 0.95
  window_minutes: 10
  include_call_auction: true

cache:
  reuse_existing_report: true

sources:
  enable_web_news: true
  enable_sentiment: true
  enable_lhb: true

report:
  include_next_day_watch: true
  include_trade_plan: false
```

配置原则：

- 大单阈值、聚合窗口和是否包含集合竞价必须可调。
- 情绪、龙虎榜、网页新闻是可关闭的辅助数据源。
- `include_trade_plan` 第一版固定为 `false`，即使配置存在也不开放交易计划写作。

## report.md 结构

```markdown
# 比亚迪（002594）2026-05-28 盘后复盘

## 一句话结论
今天走势属于：市场带动 / 板块共振 / 个股消息驱动 / 盘口资金推动 / 情绪退潮。

## 今日走势拆解
- 集合竞价 / 开盘
- 上午
- 午后
- 尾盘

## 市场与板块背景
大盘环境、所属板块表现、个股相对强弱。

## 量价与盘口
分钟线 + 分笔大单：放量位置、大单偏买偏卖、拉升或回落是否有盘口确认、尾盘行为。

## 事件与消息验证
公告、新闻、行业催化，分为已验证主因、可能催化、暂无证据支持。

## 背后逻辑
1-3 条主逻辑，每条绑定交易、板块、事件或情绪证据。

## 次日观察点
关键价位、量能阈值、板块延续信号、情绪热度变化、相关公告或新闻是否继续发酵。
```

写作强约束：

- 不写“建议买入/卖出/加仓/减仓”。
- 不把资金流或大单行为当成万能解释。
- 没有新闻/公告证据时，必须写“暂无明确事件证据”。
- 情绪数据只做辅助，不盖过交易数据和事件验证。
- 次日观察点只描述“若出现什么现象，说明什么”，不推导成操作指令。
- 每条核心逻辑都必须能回指到至少一类证据：交易、板块、事件、盘口或情绪。

## 失败降级

| 层 | 失败处理 |
|---|---|
| `market_context` | 仍可写个股复盘，但标记“市场背景缺失” |
| `sector_context` | 不判断板块共振，只判断个股自身走势 |
| `stock_trade` | 关键层，失败则不生成报告，只保存错误 |
| `tick_trade` | 报告保留“盘口大单证据缺失”，不用分笔推断 |
| `funds_context` | 用成交额、换手率和分笔大单替代资金流 |
| `event_context` | 写“暂无明确事件证据”，不能硬编原因 |
| `sentiment_context` | 不影响主报告，只少写情绪验证 |

脚本必须把每层失败写入 `data_status` 和 `manifest.json.errors`。agent 写报告时必须尊重这些状态。

## 测试与回归

### 路由与缓存

- `复盘 002594` 能创建或读取 `output/<股票名>_002594/after-market-review/<trade_date>/`。
- 已有 `report.md` 且未 force 时复用。
- `重新复盘 002594` 能触发强制刷新。

### 数据契约

- `data.json` 必含 7 个事实层、`data_status`、`derived`。
- 每个状态只能是 `ok` / `partial` / `unavailable` / `error`。
- 某层失败时，仍能落盘完整顶层结构。

### 大单计算

用 fixture 构造分笔数据，验证：

- `amount_min` 生效。
- `top_quantile` 生效。
- 两者满足任一即可入选大单。
- `window_minutes` 聚合时间窗正确。
- 修改 `config.yaml` 后阈值变化生效。
- 尾盘窗口能正确识别净买入、净卖出或中性。

### 报告约束

- 报告不包含买入、卖出、加仓、减仓等交易计划措辞。
- 缺少 `event_context` 时，报告必须出现“暂无明确事件证据”或同义说明。
- 缺少 `tick_trade` 时，报告不得写大单推断。
- “背后逻辑”每条必须引用至少一类证据。

## 实施切片建议

1. scaffold `skills/after-market-review/`、`SKILL.md`、`config.yaml`、references 基础文档。
2. 实现 `run_review.py`、输出目录、缓存和股票解析。
3. 实现 `stock_trade` 与 `market_context`，保证最小复盘可跑。
4. 实现 `tick_trade` 和可配置大单聚合。
5. 实现 `sector_context`、`funds_context`、`event_context`、`sentiment_context` 的初版采集和降级。
6. 写 `review-method.md`，约束 agent 如何从 `data.json` 写 `report.md`。
7. 补单元测试、fixtures 和 evals。

## 风险

1. AkShare 接口字段和可用历史范围可能变化。应通过 `source-policy.md` 和 `manifest.json` 记录数据源状态。
2. 分笔成交数据可能只覆盖最近交易日或近期交易日。默认入口是最近交易日，因此第一版可接受；指定历史日期能力不作为用户承诺。
3. 新闻和情绪数据容易产生事后归因。报告必须区分已验证主因和可能催化。
4. 大单方向字段可能因数据源定义不同而不完全等同主动买卖。报告应使用“盘口证据显示/大单样本显示”，避免绝对化。
5. 免费数据源存在缺口。分层降级是第一版稳定性的核心要求。

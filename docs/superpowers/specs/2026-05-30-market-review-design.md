# market-review Skill 设计规格书

**日期**: 2026-05-30
**状态**: 已批准
**范围**: 首版仅 `market-review` skill，`stock-review` 留待后续

---

## 一、定位与边界

### 1.1 角色

`market-review` 是 A 股市场每日复盘系统，定位为"宏观观察员"。回答三个问题：
- 明天适不适合交易？
- 主战场在哪？
- 该用几成力？

### 1.2 边界铁律

- **市场复盘绝不提个股**。不写"XX 股票带动板块"，只写"板块内核心股涨停 X 只"。
- 不做任何具体股票的买卖建议。
- 与 `stock-analysis` 平级，无隶属关系。

### 1.3 与 stock-review 的关系

`market-review` 产出的 `combatmap/market_data.json` 结构化为 `stock-review` 可直接消费的格式（情绪阶段、仓位建议、主线方向、风险提示、场景触发条件）。`stock-review` 读取此文件作为"强制约束参数"，避免解析整份 review.md。

---

## 二、架构

### 2.1 目录结构

```
skills/market-review/
├── SKILL.md                          # 触发规则、调用语法、强约束、执行流程
├── config.yaml                       # 模块名/别名/TTL/默认行为
├── scripts/
│   ├── requirements.txt
│   ├── fetch_index.py                # 模块一：大盘环境诊断
│   ├── fetch_sentiment.py            # 模块二：情绪周期定位
│   ├── fetch_mainline.py             # 模块三：主线与支线识别
│   ├── fetch_capital.py              # 模块四：资金行为监测
│   ├── fetch_variables.py            # 模块五：盘后变量汇总
│   ├── fetch_combatmap_data.py       # 模块六：提取前五模块关键参数
│   ├── run_review.py                 # 编排调度
│   ├── verify_facts.py               # 校验 data.json ↔ report.md 标签对齐
│   ├── verify_consistency.py         # 合成后校验跨模块一致性
│   └── record_eval.py                # 从 review.md 提取关键判断 → eval.json
├── references/
│   ├── data-schema.md                # 6 个模块 data.json 的字段规约
│   └── modules/
│       ├── index.md                  # 模块一：Agent 写报告指引
│       ├── sentiment.md              # 模块二：Agent 写报告指引
│       ├── mainline.md               # 模块三：Agent 写报告指引
│       ├── capital.md                # 模块四：Agent 写报告指引
│       ├── variables.md              # 模块五：Agent 写报告指引
│       └── combatmap.md              # 模块六：Agent 写报告指引 + 合成指引
├── evals/
│   ├── README.md
│   └── evals.json
└── output/
    └── <YYYY-MM-DD>/
        ├── index/{data.json, report.md}
        ├── sentiment/{data.json, report.md}
        ├── mainline/{data.json, report.md}
        ├── capital/{data.json, report.md}
        ├── variables/{data.json, report.md}
        ├── combatmap/{market_data.json, report.md}
        ├── review.md
        └── eval.json
```

### 2.2 设计原则

- **模块化解耦**：6 个模块各有独立的 fetch 脚本、data.json、report.md。模块间彼此不引用对方的分析结论，只引用 data.json 中的原始数据。
- **脚本拉数据，Agent 写报告**：akshare 优先，Agent 不碰数据拉取。唯一例外是模块五（盘后变量），新闻解读需 Agent WebSearch。
- **当日数据当日有效**：TTL 统一为 1 天，`--date` 默认取最近交易日，数据已存在则复用。

---

## 三、模块设计

### 模块一：大盘环境诊断 (`index`)

**数据**：上证/沪深300/中证500/中证1000/创业板指日K（开高低收量）、5/20日均线方向、上涨/下跌家数、涨幅>5%与跌幅<-5%家数、A 股总成交额。

**akshare 接口**：`ak.stock_zh_index_daily()`

**输出**：
- `data.json`：各指数多空状态（多头排列/空头排列/震荡）、量能台阶对比、涨跌家数比
- `report.md`：大盘环境诊断结论、情绪温度计定位（极度恐惧/恐惧/中性/乐观/狂热）

### 模块二：情绪周期定位 (`sentiment`)

**数据**：涨停板/跌停板列表、炸板率、连板高度及梯队序列、昨日涨停今日溢价率、日内大面股数量。

**akshare 接口**：`ak.stock_zt_pool_em()`、`ak.stock_zt_pool_dtgc_em()`

**输出**：
- `data.json`：涨停列表、连板梯度（最高板高度+各板家数）、炸板率、溢价率、大面股数
- `report.md`：周期阶段判定（冰点/修复/主升/高位分歧/退潮）及辅证依据

### 模块三：主线与支线识别 (`mainline`)

**数据**：概念板块资金净流入排名、各板块涨停家数及核心股统计、涨停股按概念归类。

**akshare 接口**：`ak.stock_sector_fund_flow_rank()`

**输出**：
- `data.json`：板块资金排名、涨停归类（板块→涨停股列表）、各板块梯队结构
- `report.md`：主线判定（涨停最多+梯队最完整+有容量中军）、主线状态（加强/分歧/转弱）、支线定位及持续性评估

### 模块四：资金行为监测 (`capital`)

**数据**：北向资金当日净买卖额及行业分布、连续三日流向、龙虎榜数据（上榜个股、买卖席位、机构/游资参与度）。

**akshare 接口**：`ak.stock_hsgt_hist_em()`、`ak.stock_sina_lhb_detail_daily()`

**输出**：
- `data.json`：北向净买卖额、行业分布、龙虎榜上榜列表及买卖金额
- `report.md`：北向行为解读（方向+行业偏好）、龙虎榜关键信号（机构/游资共振或分歧）

### 模块五：盘后变量汇总 (`variables`)

**数据**：盘后重要政策/行业新闻/公告（Agent WebSearch）、海外市场收盘（美股/港股/大宗商品，akshare）、影响评级判定。

**数据源**：akshare（海外收盘数据）+ Agent WebSearch（新闻解读）

**输出**：
- `data.json`：海外市场收盘数据（美股三大指数、恒指、原油、黄金）
- `report.md`：新闻摘要清单、每条的"影响级别"（决定全局/影响板块/仅影响个股）、预期差

### 模块六：明日作战地图 (`combatmap`)

**不拉新数据**。Agent 读取前五个模块的 `data.json`，提取关键参数到 `market_data.json`，然后据此写出三种场景推演。

**输入来源**：

| 参数 | 来自 |
|---|---|
| 大盘多空状态 | index/data.json |
| 情绪周期阶段 | sentiment/data.json |
| 主线方向与状态 | mainline/data.json |
| 资金行为信号 | capital/data.json |
| 盘后变量清单 | variables/data.json |

**输出**：
- `market_data.json`：结构化的关键参数（供 stock-review 消费）
- `report.md`：三种指数推演路径（强势/中性/弱势，含触发条件、应对策略）、统一仓位建议（进攻/均衡/防御/空仓）、风险提示

---

## 四、执行流程

```
交易日 15:30 后用户调用 /market-review [--force]

1. python scripts/run_review.py --date <today> [--force]
   └─ 检查每个模块 output/<today>/<module>/data.json
      ├─ 存在且非 --force → 跳过 fetch
      └─ 不存在 → 调对应的 fetch_<module>.py
         产出 output/<today>/<module>/data.json

2. 对每个 needs_report=true 的模块：
   └─ Agent 读 data.json + references/modules/<module>.md
      写 output/<today>/<module>/report.md

3. python scripts/verify_facts.py --date <today> --module <m>
   └─ 每个模块逐个校验 data.json ↔ report.md

4. Agent 读 6 份 report.md，合成 review.md
   └─ "今日复盘摘要"（面板诊断结论）+ "明日作战地图"（场景推演+仓位）

5. python scripts/verify_consistency.py --date <today>
   └─ 跨模块一致性校验（同一数据在不同模块间数值一致，模块六参数引用正确）

6. python scripts/record_eval.py --date <today>
   └─ 从 review.md 提取关键判断 → eval.json
```

---

## 五、强约束

| ID | 约束 | Why |
|---|---|---|
| R1 | 当日数据当日有效，`--date` 默认取最近交易日，不加 `--force` 就复用已有 data.json | 同一交易日盘后数据不会变，重复拉取浪费 API 配额 |
| R2 | `--force` 是打破 R1 的唯一方式，可作用到指定模块 `--force --module index` | 避免 Agent "想做完整一点"就自作主张全部重跑 |
| R3 | 模块间 report.md 彼此不引用（不写"见模块一结论"），只引用 data.json 中的原始数据 | 模块解耦的核心保障 |
| R4 | 合成 review.md 时各模块独立应用 R1/R2 | 模块六每次都重写（依赖前五模块最新输出） |
| R5 | 单模块永不输出"明日作战地图"或仓位建议；仓位建议仅模块六产出 | 仓位需要综合全部模块信息 |
| R6 | 每个模块 report.md 必须以 `<!-- REVIEW_MODULE_START -->` 段开头，标注模块名和交易日 | 合成时验证模块完整性和日期对齐 |
| R7 | 市场复盘绝不提个股 | 核心边界铁律 |
| R8 | Python 脚本只管 fetch 和校验，不生成 report.md | Agent 是 report.md 的唯一生产者 |
| R9 | verify_facts 校验单模块 data.json↔report.md；verify_consistency 仅合成后跑 | 跨模块一致性只在合并后才有意义 |

---

## 六、配置

```yaml
# config.yaml
modules:
  index:
    alias: [大盘, 指数, 环境诊断, 大盘环境]
    ttl_days: 1
    description: 大盘环境诊断 - 指数多空、量能、涨跌家数、情绪温度计
  sentiment:
    alias: [情绪, 周期, 情绪周期, 涨停板]
    ttl_days: 1
    description: 情绪周期定位 - 连板梯度、炸板率、溢价率、冰点/主升判定
  mainline:
    alias: [主线, 板块, 热点, 题材]
    ttl_days: 1
    description: 主线与支线识别 - 板块资金、涨停归类、梯队结构
  capital:
    alias: [资金, 北向, 龙虎榜, 机构]
    ttl_days: 1
    description: 资金行为监测 - 北向资金流向、龙虎榜信号
  variables:
    alias: [消息, 政策, 新闻, 变量, 事件]
    ttl_days: 1
    description: 盘后变量汇总 - 政策/新闻/海外异动/影响评级
  combatmap:
    alias: [作战图, 仓位, 推演, 预案, 作战地图]
    ttl_days: 1
    description: 明日作战地图 - 三种路径推演 + 仓位建议 + 风险提示
defaults:
  mode: review
  force: false
```

---

## 七、SKILL.md 触发规则

```yaml
---
name: market-review
description: |
  A 股市场每日复盘系统。对用户提到的盘面复盘/市场分析/明日预判需求主动调用。
  覆盖：大盘环境、情绪周期、主线识别、资金监测、盘后变量、明日作战地图。
metadata:
  argument-hint: [--force] [--module <模块名>]
---
```

### 自然语言路由

| 用户说 | 翻译 |
|---|---|
| 开始今日复盘 | `/market-review` |
| 今天市场怎么样 | `/market-review` |
| 复盘一下今天大盘 | `/market-review` |
| 明天能不能做 | `/market-review` |
| 今天的情绪周期是什么阶段 | `/market-review --module sentiment` |
| 重新跑一下今天复盘 | `/market-review --force` |

### 调用语法

```
/market-review [--force] [--module <模块名>]
```

- 不带 `--module` 默认合成全部（6 模块 + review.md）
- `--module` 支持中英别名（见 config.yaml）
- `--force` 覆盖 TTL，强制重拉指定模块（或全部）

---

## 八、Eval 系统（内置轻量）

### record_eval.py

合成 review.md 后自动运行，从 report.md 中正则提取结构化评估点：

```json
{
  "date": "2026-05-30",
  "market_review": {
    "sentiment_stage": "高位分歧",
    "mainline_direction": "人工智能",
    "position_advice": "防御（2-3成）",
    "scenarios": ["强势路径", "中性路径", "弱势路径"],
    "risk_warnings": ["高标A杀风险", "流动性衰竭"]
  }
}
```

次日盘后可人工对照 eval.json 中的预测与当日实际盘面，判断质量。不在此 skill 内做自动准确性比对（留给后续 stock-review 或独立 eval skill）。

---

## 九、与 stock-review 的接口契约

`combatmap/market_data.json` 结构：

```json
{
  "date": "2026-05-30",
  "sentiment_stage": "高位分歧",
  "position_advice": "防御",
  "position_ratio": "2-3成",
  "mainline_sectors": ["人工智能", "机器人"],
  "mainline_status": "分歧",
  "risk_warnings": ["高标A杀风险"],
  "scenario_triggers": {
    "bullish": "高开不破3050，且量能放大至前日1.2倍",
    "neutral": "平开在3030-3050震荡",
    "bearish": "低开破3000或北向开盘半小时净流出超50亿"
  }
}
```

stock-review 读取此文件作为强制约束参数，无需解析 review.md。

---

## 十、不在首版范围

- `stock-review` skill（个股复盘）
- 独立 eval skill（验证迭代系统）
- eval 的自动准确性比对逻辑（`record_eval.py` 只记录不比对）
- 历史回测功能

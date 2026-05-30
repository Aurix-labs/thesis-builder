---
name: market-review
description: |
  A 股市场每日复盘系统。对用户提到的盘面复盘/市场分析/明日预判需求主动调用。
  覆盖：大盘环境、情绪周期、主线识别、资金监测、盘后变量、明日作战地图。
  仅供研究参考，不构成证券投资咨询业务，不构成投资建议。
metadata:
  argument-hint: "[--force] [--module <模块名>]"
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
   - status=reuse  → 直接读已有 report.md，跳过步骤 3
   - status=data_ready → 进入步骤 3
3. **数据质量校验**（每个 data_ready 模块必做）：
   跑 python scripts/validate_data.py --ymd <today> [--module <m>]
   - FAIL → **Agent 停止该模块**，向用户报告数据质量问题，不写 report.md
   - WARN → Agent 可写 report.md，但必须在报告中标注数据缺失项
   - PASS → 继续写 report.md
4. Agent 读 data.json + references/modules/<m>.md，写 report.md
   跑 python scripts/verify_facts.py --module <m> --ymd <today>
5. 对每个 needs_report_md=true 的模块循环执行步骤 3-4
6. Agent 读 6 份 report.md，合成 output/<today>/review.md
7. 跑 python scripts/verify_consistency.py --ymd <today>
8. 跑 python scripts/record_eval.py --ymd <today>
9. 把 review.md 内容反馈给用户
```

### 单模块（例：`/market-review --module sentiment`）

```
1. 跑 python scripts/run_review.py --date <today> --module sentiment [--force]
2. 解析 stdout：
   - status=reuse → 直接读已有 report.md
   - status=data_ready → 跑 validate_data.py → 校验通过再写 report.md → verify_facts
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

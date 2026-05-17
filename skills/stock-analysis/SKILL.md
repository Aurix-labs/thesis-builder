---
name: stock-analysis
description: |
  A 股个股深度研究系统 v4.0（模块化）。当用户提到"分析XXX股票"、"看下XXX"、"研究XXX"、
  "XXXX值得买吗"、"XXX怎么样"、"XXX估值/技术面/质地/风险/产业链"，或直接给出 6 位 A 股代码，
  按需触发对应分析模块。
  Phase 2 拆为 7 个独立模块 + 1 个合成层：
    chain / rubric / elasticity / risk / valuation / flow-tech / peers / report
  每个模块按 TTL 复用快照（chain 90 天 / rubric 90 / elasticity 90 / risk 30 /
    valuation 7 / flow-tech 1 / peers 90）。
  单模块产出 markdown；合成 report 时才生成 HTML。
  本工具仅供研究参考，不构成证券投资咨询业务，不构成投资建议。
metadata:
  argument-hint: <股票代码或公司名> [模块...] [--force]
---

# stock-analysis · A 股个股深度研究系统 v4.0

## 调用语法

```
/stock-analysis <代码或公司名> [模块...] [--force]
```

- 不带模块名默认 `report`（合成全景）
- 模块名支持中英别名（详见 [config.yaml](config.yaml)）
- `--force` 覆盖 TTL，强制重跑

### 模块清单

| 模块 | 主名 | 覆盖原 Step | TTL |
|---|---|---|---|
| 产业链与趋势 | `chain` | Step 1 + Step 2 | 90 天 |
| 公司质地 | `rubric` | Step 3 Rubric 100 分 | 90 天 |
| 业绩弹性 | `elasticity` | Step 4 | 90 天 |
| 风险与止损 | `risk` | Step 5 + Step 0.5 | 30 天 |
| 估值与赔率 | `valuation` | Step 6（除 6a+/6a++） | 7 天 |
| 资金与技术面 | `flow-tech` | Step 6a+ + Step 6a++ | 1 天 |
| 同业对标 | `peers` | Step 7 | 90 天 |
| 合成报告 | `report` | Step 0 + Step 8 + bear-case + fact-check + HTML | — |

### 自然语言路由

| 用户说 | 翻译 |
|---|---|
| 分析 002594 | `/stock-analysis 002594 report` |
| 看下比亚迪 | `/stock-analysis 002594 report` |
| 002594 估值多少 | `/stock-analysis 002594 valuation` |
| 比亚迪技术面怎么样 | `/stock-analysis 002594 flow-tech` |
| 002594 的产业链 | `/stock-analysis 002594 chain` |
| 比亚迪 质地和风险 | `/stock-analysis 002594 rubric risk` |
| 重新跑下 002594 的估值 | `/stock-analysis 002594 valuation --force` |

## 强约束

| ID | 约束 |
|---|---|
| R1 | TTL 内必须复用 latest 快照，**不重新拉数据、不重新跑 LLM 分析** |
| R2 | `--force` 是打破 R1 的唯一方式 |
| R3 | 合成 `report` 时各模块独立应用 R1/R2 |
| R4 | 单模块**永不**出 HTML；HTML 仅在合成 report 时产出 |
| R5 | 模块间分析输出彼此不引用 |
| R6 | 每个模块 report.md 必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头 |
| R7 | bear-case / fact-check 只在合成 report 时跑 |
| R8 | `verify_facts --module <m>` 校验单模块；`verify_consistency` 仅 report 时跑 |
| R9 | `peers/<ymd>/peers.txt` 存在时 `peers --force` 复用名单 |

## Agent 执行流程

### 单模块（例：`/stock-analysis 002594 valuation`）

```
1. 跑 python scripts/run_module.py 002594 valuation [--force]
2. 解析 stdout 输出（JSONL）：
   - status=reuse  → 直接读 <module>/<ymd>/report.md 给用户
   - status=data_ready → 读 data.json + references/modules/valuation.md
                         写 <module>/<today>/report.md
                         跑 python scripts/verify_facts.py --module valuation --stock-dir <stock> --ymd <today>
3. 把最终 report.md 内容反馈给用户
```

### 合成 report（例：`/stock-analysis 002594 report`）

```
1. 跑 python scripts/run_module.py 002594 report [--force]
2. 对每个 needs_report_md=true 的模块，按其 references/modules/<m>.md 写 report.md
3. 跑 python scripts/compose_report.py 002594 → merged report.md + manifest.json
4. 在 merged report.md 顶部插 Step 0（任务锁定）
5. 在 merged report.md 末尾插 Step 8（综合结论 + 跟踪锚点）
6. 跑 python scripts/verify_consistency.py --report <merged_report_md> → 0 FAIL
7. 调 bear-case sub-agent → append 到 report.md（prompt 见 references/modules/report.md）
8. 调 fact-check sub-agent → 写 report/<today>/fact-check.md
9. 按 references/batch-checklist.md 分 6 批写 report/<today>/report.html
10. 跑 bash scripts/verify_html.sh report/<today>/report.html → 全 PASS
```

## 输出结构

```
output/
└── <股票名>_<代码>/
    ├── chain/<ymd>/{data.json,report.md}        + latest 软链
    ├── rubric/<ymd>/{data.json,report.md}       + latest
    ├── elasticity/<ymd>/{data.json,report.md}   + latest
    ├── risk/<ymd>/{data.json,report.md,anomalies.md,anomalies.json}  + latest
    ├── valuation/<ymd>/{data.json,report.md}    + latest
    ├── flow-tech/<ymd>/{data.json,report.md}    + latest
    ├── peers/<ymd>/{data.json,report.md,peers.txt}  + latest
    ├── report/<ymd>/{report.md,fact-check.md,report.html,manifest.json}
    └── .cache/<ymd>/...    # akshare 接口当日缓存（agent 不读）
```

## 配置

模块 TTL、别名、默认行为见 [config.yaml](config.yaml)。用户可直接编辑。

## 关键文档

| 用途 | 文件 |
|---|---|
| 模块方法论 | [references/modules/](references/modules/) |
| 数字标签规范 | [references/tag-spec.md](references/tag-spec.md) |
| 不变量校验 schema | [references/invariants-spec.md](references/invariants-spec.md) |
| HTML 设计规范 | [references/html-spec.md](references/html-spec.md) |
| HTML 分批校验清单 | [references/batch-checklist.md](references/batch-checklist.md) |
| data.json schema | [references/data-schema.md](references/data-schema.md) |
| v3.2 归档（仅参考） | [references/_legacy/](references/_legacy/) |

## 禁止事项（v4 沿用 v3.2 + 新增）

| # | 禁止 | 原因 |
|---|---|---|
| 1 | Python 生成 HTML markup | 转义混乱 |
| 2 | Bash heredoc 写多行 HTML | EOF 易匹配失败 |
| 3 | 跳过任何模块的"标的速写"段 | 破坏 compose 去重逻辑 |
| 4 | 单模块输出 HTML | 违反 R4 |
| 5 | 模块间分析输出互相引用 | 违反 R5（模块独立性） |
| 6 | TTL 内未传 --force 就重新拉数据 | 违反 R1（用户已强约束） |
| 7 | `compose_report.py` 之外的脚本调用合成层产物 | 合成是 agent 责任 |
| 8 | 修改 latest 软链后不更新 manifest | 合成报告需可审计 |
| 9 | 一次性写完整 HTML | 必须分 6 批 |
| 10 | hero meta 显示 A/B/C 字母评级 | v3.1 起改用 `Rubric: <total>/100` |

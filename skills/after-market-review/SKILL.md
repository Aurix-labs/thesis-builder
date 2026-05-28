---
name: after-market-review
description: |
  A 股单股盘后复盘 skill。只要用户要求对某只 A 股做“复盘”“盘后复盘”“今天为什么这么走”“走势逻辑”“短线情绪”“盘口大单”“分时复盘”等当天走势解释，就主动调用本 skill。
  默认对最近一个已收盘交易日做单股复盘，输出 Markdown 报告，并结构化保存 data.json / manifest.json。
  用户说“重新复盘”“刷新”“强制更新”时翻译为 --force。
  第一版只给次日观察点，不给买入、卖出、加仓、减仓等交易计划。本工具仅供研究参考，不构成证券投资咨询业务，不构成投资建议。
metadata:
  argument-hint: <股票代码或公司名> [--force]
---

# after-market-review · A 股盘后复盘

## 调用语法

```bash
/after-market-review <股票代码或公司名> [--force]
```

自然语言路由：

| 用户说 | 翻译 |
|---|---|
| 复盘 002594 | `/after-market-review 002594` |
| 盘后复盘 比亚迪 | `/after-market-review 比亚迪` |
| 今天比亚迪为什么这么走 | `/after-market-review 比亚迪` |
| 重新复盘 002594 | `/after-market-review 002594 --force` |

## 强约束

| ID | 约束 | Why |
|---|---|---|
| R1 | 本 skill 独立于 `stock-analysis`，不读写 `stock-analysis` 模块目录 | `stock-analysis` 是中期研究，本 skill 是短线盘后解释，两者定位不同 |
| R2 | 默认只做单股最近一个已收盘交易日 | 第一版不做市场异动筛选和历史日期承诺 |
| R3 | 同一股票同一交易日已有 `report.md` 且未传 `--force` 时必须复用 | 盘后复盘是历史快照，同日反复重跑会破坏可追溯性 |
| R4 | 脚本只写 `data.json` / `manifest.json`，agent 按 `references/review-method.md` 写 `report.md` | 脚本管事实，agent 管解释 |
| R5 | `stock_trade` 是关键层；该层失败时不写报告 | 没有个股交易事实就无法做复盘 |
| R6 | `tick_trade` 缺失时不得写大单推断 | 分笔证据缺失不能脑补盘口行为 |
| R7 | 没有公告或新闻证据时必须写“暂无明确事件证据” | 避免事后找理由 |
| R8 | 情绪数据只做辅助，不覆盖交易事实和事件验证 | 人气和题材热度容易噪声化 |
| R9 | 不写买入、卖出、加仓、减仓等交易计划 | 第一版只提供观察点，降低误导和合规风险 |
| R10 | 大单阈值必须从 `config.yaml` 读取 | 用户需要随时调整大单金额、分位和聚合窗口 |

## Agent 执行流程

1. 跑：

   ```bash
   cd skills/after-market-review/scripts
   python run_review.py <股票代码或公司名> [--force]
   ```

2. 解析 stdout JSON：
   - `status=reuse`：直接读取并返回 `report_md`。
   - `status=data_ready`：读取 `data_json`、`manifest_json`、`references/review-method.md`，写 `report_md`。
   - `status=error`：读取 `manifest_json` 中的错误并向用户说明。

3. 写 `report.md` 后，返回报告摘要和文件路径。

## 输出结构

```text
output/<股票名>_<代码>/after-market-review/<trade_date>/
├── data.json
├── manifest.json
└── report.md
```

## 关键文档

| 何时读 | 文件 |
|---|---|
| 写 `report.md` 时 | `references/review-method.md` |
| 修改数据契约时 | `references/data-schema.md` |
| 修改数据源或降级规则时 | `references/source-policy.md` |
| 修改大单阈值、缓存或数据源开关时 | `config.yaml` |

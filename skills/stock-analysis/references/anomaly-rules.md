# 异常检测规则 · v3.1

Phase 1.5 阶段 `scan_anomalies.py` 按本规则扫描 data.json，输出 anomalies.json + anomalies.md。

## 规则全集

### 财务异常（financial_abstract）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| FIN-001 | 归母净利润 | 单季 YoY | < -50% | CRITICAL |
| FIN-002 | 归母净利润 | 单季 YoY | -50% ~ -30% | HIGH |
| FIN-003 | 营业总收入 | 单季 YoY | < -30% | HIGH |
| FIN-004 | 销售净利率 | QoQ 绝对变动 | > ±10pct | HIGH |
| FIN-005 | 销售毛利率 | YoY 绝对变动 | > ±5pct | MEDIUM |
| FIN-006 | 扣非净利润 | 单季 YoY | < -50% | CRITICAL |

### 资金面异常（fund_flow）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| FUND-001 | 主力净流入 | 60 日累计 / 市值 | < -20% | CRITICAL |
| FUND-002 | 主力净流入 | 60 日累计 / 市值 | -20% ~ -10% | HIGH |
| FUND-003 | 主力净流入 | 60 日累计 / 市值 | > +20% | HIGH（异常流入）|

### 价格异常（kline_daily）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| PRICE-001 | 收盘价 | 近 60 日区间涨跌 | > ±50% | HIGH |
| PRICE-002 | 收盘价 | 近 60 日区间涨跌 | ±30% ~ ±50% | MEDIUM |

### 业务异常（business）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| BIZ-001 | 主营业务毛利率 | YoY | > ±5pct | MEDIUM |

## severity 等级

- **CRITICAL**：必须在 Step 0.5 整段（≥80字）讨论 + 在 hero/conclusion 高亮
- **HIGH**：必须在 Step 0.5 列出 + 至少在一个后续 Step 分析
- **MEDIUM**：必须在 anomalies.md 列出 + agent 自主决定是否讨论

## 输出 anomalies.json schema

```json
{
  "$schema": "anomalies-v1",
  "as_of": "YYYY-MM-DD",
  "code": "300775",
  "items": [
    {
      "id": "A001",
      "rule_id": "FIN-001",
      "severity": "CRITICAL",
      "indicator": "归母净利润",
      "period": "2026Q1",
      "value": 10737549.01,
      "value_display": "0.107亿",
      "prior_value": 128606786.31,
      "prior_period": "2025Q1",
      "delta_pct": -0.917,
      "blocks_ref": "financial_abstract.20260331.归母净利润",
      "must_address_in_step": ["0.5", "4", "5", "8"],
      "narrative_hint": "2026Q1 归母净利同比 -91.7%，断崖式下滑"
    }
  ]
}
```

## Step 强制讨论映射

| severity | 必须出现的 Step |
|---|---|
| CRITICAL | Step 0.5 整段 + ≥ 1 后续 Step |
| HIGH | Step 0.5 列出 + ≥ 1 后续 Step |
| MEDIUM | anomalies.md 列出，agent 自决 |

verify_facts.py 反查规则：
- 对每条 CRITICAL，检查 Step 0.5 section 中是否包含 `indicator` 字符串
- 对每条 HIGH，检查 Step 0.5 section 中是否包含 `indicator` 字符串
- 不满足 → FAIL

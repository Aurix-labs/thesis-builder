# risk · 风险与止损 · 方法论

> 本模块产出：异常分析 + 风险清单 + 逻辑破坏条件
> 数据输入：`<stock>/risk/<ymd>/data.json`（`meta`/`quote`/`financial_abstract`/`kline_daily`/`notice`/`news`）
> 输出文件：同目录 `report.md`，必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头
> 额外产物：`anomalies.md` + `anomalies.json`

## 强约束

- 数字必须带 `[F:]/[C:]/[I:]/[T:]/[GAP:]` 标签（详见 [../tag-spec.md](../tag-spec.md)）
- 最低行数：40 行
- 必含 section：标的速写 / Step 0.5 异常分析 / 风险清单 / 至少 3 条逻辑破坏条件

## 方法论

### Step 0.5：核心异常分析（必做）

> **inputs:** `blocks.financial_abstract`, `blocks.fund_flow`, `kline_daily`, anomalies.json
> **outputs:** 每条 CRITICAL/HIGH 异常的成因 + 影响 + 跟踪锚点

**前置：** 必须先读 `anomalies.md`（Phase 1.5 自动产出）。

**强制：** 对每条 **CRITICAL** anomaly 必须有一整段 ≥80 字分析；对每条 **HIGH** 必须列出。

**模板：**

```text
#### A001 · <indicator> <period> <YoY 描述>
- 数值：<value> [F:<blocks_ref>]
- 上年同期：<prior_value> [F:<prior_ref>]
- **可能原因**：<原因 1 / 原因 2 / 原因 3>，需在 Step <X> 深入
- **对投资逻辑的影响**：<拐点是否成立 / 估值是否需要重置>
- **跟踪指标**：<在 Step 8 跟踪锚点中加入对应字段>
```

**输出：** 一整段 ≥80 字分析。verify_facts.py 会检查 CRITICAL 的 indicator 字符串是否在本段出现。

### Step 5：风险分析与逻辑破坏条件

> **inputs:** `blocks.notice`, anomalies.json
> **outputs:** 风险清单 + 至少 3 条可量化失效条件

#### 5a. 风险清单（必做）

| 风险类型 | 具体场景 | 影响程度 | 发生概率 |
|---------|---------|---------|---------|
| 行业周期 |  | 高/中/低 | 高/中/低 |
| 竞争格局 |  |  |  |
| 交付/产能 |  |  |  |
| 客户集中度 |  |  |  |
| 财务质量 |  |  |  |
| 治理/关联交易 |  |  |  |
| 技术替代 |  |  |  |

#### 5b. 逻辑破坏条件（止损信号，必做，至少 3 条）

每条需**可量化或可观测**，格式示例：
1. 价格跌回 XX 以下
2. 新增大额减值计提
3. 核心客户流失

### 异常检测规则全集

Phase 1.5 阶段 `scan_anomalies.py` 按本规则扫描 data.json，输出 anomalies.json + anomalies.md。

#### 财务异常（financial_abstract）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| FIN-001 | 归母净利润 | 单季 YoY | < -50% | CRITICAL |
| FIN-002 | 归母净利润 | 单季 YoY | -50% ~ -30% | HIGH |
| FIN-003 | 营业总收入 | 单季 YoY | < -30% | HIGH |
| FIN-004 | 销售净利率 | QoQ 绝对变动 | > ±10pct | HIGH |
| FIN-005 | 销售毛利率 | YoY 绝对变动 | > ±5pct | MEDIUM |
| FIN-006 | 扣非净利润 | 单季 YoY | < -50% | CRITICAL |

#### 资金面异常（fund_flow）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| FUND-001 | 主力净流入 | 60 日累计 / 市值 | < -20% | CRITICAL |
| FUND-002 | 主力净流入 | 60 日累计 / 市值 | -20% ~ -10% | HIGH |
| FUND-003 | 主力净流入 | 60 日累计 / 市值 | > +20% | HIGH（异常流入）|

#### 价格异常（kline_daily）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| PRICE-001 | 收盘价 | 近 60 日区间涨跌 | > ±50% | HIGH |
| PRICE-002 | 收盘价 | 近 60 日区间涨跌 | ±30% ~ ±50% | MEDIUM |

#### 业务异常（business）

| 规则 ID | 指标 | 计算 | 阈值 | severity |
|---|---|---|---|---|
| BIZ-001 | 主营业务毛利率 | YoY | > ±5pct | MEDIUM |

#### severity 等级

- **CRITICAL**：必须在 Step 0.5 整段（≥80 字）讨论 + 在 hero/conclusion 高亮
- **HIGH**：必须在 Step 0.5 列出 + 至少在一个后续 Step 分析
- **MEDIUM**：必须在 anomalies.md 列出 + agent 自主决定是否讨论

#### anomalies.json schema

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

#### Step 强制讨论映射

| severity | 必须出现的 Step |
|---|---|
| CRITICAL | Step 0.5 整段 + ≥ 1 后续 Step |
| HIGH | Step 0.5 列出 + ≥ 1 后续 Step |
| MEDIUM | anomalies.md 列出，agent 自决 |

verify_facts.py 反查规则：
- 对每条 CRITICAL，检查 Step 0.5 section 中是否包含 `indicator` 字符串
- 对每条 HIGH，检查 Step 0.5 section 中是否包含 `indicator` 字符串
- 不满足 → FAIL

## 报告骨架（agent 写 report.md 时必须遵循）

```markdown
<!-- THESIS_SNAPSHOT_START -->
（脚本自动注入）
<!-- THESIS_SNAPSHOT_END -->

## Step 0.5 · 核心异常分析

#### A001 · <indicator> <period> <YoY 描述>
- 数值：<value> [F:<blocks_ref>]
- 上年同期：<prior_value> [F:<prior_ref>]
- **可能原因**：…（≥80 字一整段）
- **对投资逻辑的影响**：…
- **跟踪指标**：…

#### A002 · ...（每条 CRITICAL 一段，每条 HIGH 至少列出）

## Step 5 · 风险分析与逻辑破坏条件

### 5a 风险清单
| 风险类型 | 具体场景 | 影响程度 | 发生概率 |
|---|---|---|---|
| 行业周期 | [I:] | 高/中/低 | 高/中/低 |
| 竞争格局 | ... | ... | ... |
| 交付/产能 | ... | ... | ... |
| 客户集中度 | ... | ... | ... |
| 财务质量 | ... | ... | ... |
| 治理/关联交易 | ... | ... | ... |
| 技术替代 | ... | ... | ... |

### 5b 逻辑破坏条件（至少 3 条，必须可量化）
1. 价格跌破 XX 元（对应 PE XX 倍） [C:]
2. 季度净利同比再下滑 > -30% [F:]
3. 核心客户 / 大订单流失 [I:]
```

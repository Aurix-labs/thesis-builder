# rubric · 公司质地 · 方法论

> 本模块产出：公司质地 Rubric 100 分评分与不碰清单
> 数据输入：`<stock>/rubric/<ymd>/data.json`（`meta`/`quote`/`financial_abstract`/`top_holders`/`margin`）
> 输出文件：同目录 `report.md`，必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头

## 强约束

- 数字必须带 `[F:]/[C:]/[I:]/[T:]/[GAP:]` 标签（详见 [../tag-spec.md](../tag-spec.md)）
- 最低行数：50 行
- 必含 section：标的速写 / Rubric 100 分评分表 / 不碰清单

## 方法论

### Step 3：公司筛选与质量评分

> **inputs:** `financials[]`, `financial_abstract[]`, `quote`, `blocks.top_holders`, `blocks.margin`
> **outputs:** Rubric 6 维 100 分

#### 3a. 正面筛选清单

| 标准 | 要求 | 达标判定 |
|------|------|---------|
| 市值门槛 | 百亿以上优先 | 60 亿以下慎重 |
| 行业地位 | 细分领域前三 | 市占率数据支撑 |
| 业务相关度 | 主营与产业方向强关联 | 100% 专注 > 多元化 |
| 业绩弹性 | 涨价/放量对利润有敏感度 | 需量化弹性桥 |
| 位置性价比 | 当前估值 vs 逻辑兑现空间 | PE/PB 分位 + PEG |
| 管理层/战略信号 | 产能扩张、新客户定点、股权激励 | 行动 > 口号 |

#### 3b. 不碰清单（负面排查，必做）

- [ ] 市值 50 亿以下？
- [ ] 蹭概念？
- [ ] 分销商/贸易商？
- [ ] 看不到业绩落地？
- [ ] 主业拖后腿？

#### 3c. Rubric 评分（100 分制，二值加和）

100 分制，6 维拆 20 个二值检查项（6+4+4+3+2+1）。每项 ✅/❌，分值固定。维度分 = 通过项 × 单项分。**禁止小数点。**

报告中必须出现完整 rubric 表格（不能只给总分），格式：

| ID | 检查项 | data 依据 | 分值 | 本票（举例） |
|---|---|---|---|---|
| BF-01 | 营收 3 年 CAGR ≥ 15% | financials[].revenue | 5 | ❌ |
| ... | ... | ... | ... | ... |
| **合计** | | | **100** | **<total>/100** |

### Rubric 完整规则（共 20 项，100 分）

#### 1. 基本面质量（30 分，6 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| BF-01 | 营收 3 年 CAGR ≥ 15% | financials 三年算 CAGR | 5 |
| BF-02 | 最新年度净利同比 > 0% | financials[最新].net_profit YoY | 5 |
| BF-03 | 最新季度净利同比 > -30% | financial_abstract 最新季 YoY | 5 |
| BF-04 | 毛利率 3 年波动 < ±10pct | financials[].gross_margin 极差 | 5 |
| BF-05 | ROE 最新年度 > 10% | financials[最新].roe | 5 |
| BF-06 | 资产负债率 < 60% | financial_abstract.资产负债率 | 5 |

#### 2. 产业匹配度（20 分，4 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| IND-01 | 主营营收占比 ≥ 70% 行业主线 | business 最新按行业分类 | 5 |
| IND-02 | 行业最新 PMI 或景气 > 50 / 上行 | [I:行业研报] | 5 |
| IND-03 | 公司近 12 月有政策/订单催化公告 | research / notice | 5 |
| IND-04 | 产业链位置（上/中/下游）利润率排第 1 | [I:Step 2 价值链分析] | 5 |

#### 3. 业绩弹性（20 分，4 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| ELA-01 | 量价敏感度可量化（公式可写出） | [I:Step 4 弹性树] | 5 |
| ELA-02 | 最新产能利用率有披露 | research / 公告 | 5 |
| ELA-03 | 新产能/新业务有时间表 | research / 公告 | 5 |
| ELA-04 | 上一周期峰值利润 ≥ 当前 2 倍（弹性空间） | financials 历史 | 5 |

#### 4. 估值与位置（15 分，3 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| VAL-01 | PE-TTM 历史分位 < 50% | 计算 | 5 |
| VAL-02 | PB < 同行业均值 | 同行 PB 对比 | 5 |
| VAL-03 | 3 年价格分位 < 50% | kline_daily | 5 |

#### 5. 资金与交易结构（10 分，2 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| FUND-01 | 近 60 日主力资金净流入 ≥ 0 | fund_flow 累计 | 5 |
| FUND-02 | 融资余额 / 流通市值 < 5% | margin | 5 |

#### 6. 治理与风险（5 分，1 × 5）

| ID | 检查项 | data 依据 | 分值 |
|---|---|---|---|
| GOV-01 | 近 1 年无重大诉讼/处罚/减持 | notice | 5 |

#### 合计 100 分

**评级（仅供参考，不显示字母级）：**
- ≥ 80：优秀
- 60-79：良好
- 40-59：一般
- < 40：较差

#### hero meta 显示规则

`Rubric: <total>/100`
副标：`<passed_items>/20 ✓`

例：`Rubric: 10/100`、副标 `2/20 ✓`

## 报告骨架（agent 写 report.md 时必须遵循）

```markdown
<!-- THESIS_SNAPSHOT_START -->
（脚本自动注入）
<!-- THESIS_SNAPSHOT_END -->

## Step 3 · 公司质地评分

### 正面筛选清单
| 标准 | 达标判定 | 本票判断 |
|---|---|---|
| 市值门槛 | 百亿优先 | [F:] |
| 行业地位 | 细分前三 | [I:] |
| ... |  |  |

### 不碰清单（负面排查）
- [x] / [ ] 市值 50 亿以下？
- [x] / [ ] 蹭概念？
- [x] / [ ] 分销商/贸易商？
- [x] / [ ] 看不到业绩落地？
- [x] / [ ] 主业拖后腿？

### Rubric 100 分评分（20 项二值）
| ID | 检查项 | 依据 | 分值 | 本票 |
|---|---|---|---|---|
| BF-01 | 营收 3 年 CAGR ≥ 15% | [F:] | 5 | ✅/❌ |
| BF-02 | 最新年度净利同比 > 0% | [F:] | 5 | ✅/❌ |
| ... | ... | ... | ... | ... |
| GOV-01 | 近 1 年无重大诉讼/处罚/减持 | [F:] | 5 | ✅/❌ |
| **合计** |  |  | **100** | **<total>/100** |

副标：`<passed_items>/20 ✓` · 评级：{优秀/良好/一般/较差}
```

## summary 必填字段（rubric/<ymd>/data.json）

LLM 在写 report.md **之前**，必须把以下字段写回 `<ymd>/data.json` 的 `summary` 子键：

```json
{
  "summary": {
    "total": 72,
    "passed": 14,
    "dimensions": [
      {"name": "基本面",     "points_max": 30, "points_got": 18},
      {"name": "产业匹配",   "points_max": 20, "points_got": 16},
      {"name": "业绩弹性",   "points_max": 20, "points_got": 14},
      {"name": "估值与位置", "points_max": 15, "points_got": 10},
      {"name": "资金交易",   "points_max": 10, "points_got": 9},
      {"name": "治理风险",   "points_max": 5,  "points_got": 5}
    ],
    "financials_table": [
      {"year": 2023, "revenue": 6023.15, "net_profit": 300.41, "gross_margin": 0.2034, "roe": 0.2103},
      {"year": 2024, "revenue": 7773.34, "net_profit": 402.54, "gross_margin": 0.2188, "roe": 0.2245},
      {"year": 2025, "revenue": 8500.00, "net_profit": 500.00, "gross_margin": 0.2250, "roe": 0.2350}
    ],
    "revenue_breakdown": [
      {"name": "汽车", "value": 6700, "percent": 0.79}
    ]
  }
}
```

**约束**：

- `dimensions` 必须恰好 6 条（名称固定：基本面/产业匹配/业绩弹性/估值与位置/资金交易/治理风险）
- `total = sum(d.points_got for d in dimensions)`（render_html.py 不校验加法，但报告内一致性由 verify_consistency.py 兜底）
- `financials_table` 至少 3 行（最近 3 年），数字单位：营收/净利 = 亿元，gross_margin/roe = 0-1 小数（HTML 渲染时 × 100 显示百分比）
- `revenue_breakdown` 至少 1 项，`value` 单位 = 亿元，`percent` = 0-1 小数

报告中所有"X/100"、"X/20 ✓"、6 维评分条的数字必须与 `summary` 严格一致（散文/数据不一致由 fact-check 兜底）。

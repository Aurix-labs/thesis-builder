# Invariants 块 schema · v3.2

> Phase 2 §1 写 part1 时，agent 在 compliance 声明之后、Step 0 之前插入本块。
> 合并 report.md 之后 `verify_consistency.py` 会按本文档校验。

## 1. 块的位置与标记

````markdown
# 报告标题
> **合规声明**：...

<!-- invariants v3.2 -->
```yaml
constants:
  price: 86.87
  ...
```

## Step 0 · 任务锁定
...
````

`<!-- invariants v3.2 -->` 是脚本识别的唯一标记。整块内容是合法 YAML。

## 2. 必填段

### 2.1 constants（≥ 4 项）

```yaml
constants:
  price: 86.87                    # 当前股价（元）
  shares: 38.82                   # 总股本（亿股）
  book_value_per_share: 32.975166 # 每股净资产（元）
  baseline_eps_2026: 5.00         # 本框架基准 EPS26
  baseline_eps_2027: 6.00         # 本框架基准 EPS27（如适用）
  research_eps_2026_mid: 4.50     # 研报中位 EPS26（对照展示用，可选）
```

### 2.2 derived（算式 → 重算 → 对正文）

```yaml
derived:
  market_cap_yi: "price * shares"     # 字符串算式
  pe_2026e_base: "price / baseline_eps_2026"
  pe_2027e_base: "price / baseline_eps_2027"
  pb: "price / book_value_per_share"
```

每个键的值是 YAML 字符串算式；脚本用 constants（含已算出 derived）做安全 eval。

### 2.3 keywords（每个被引用的 invariant 至少 1 个别名）

```yaml
keywords:
  baseline_eps_2026:
    - "基准 EPS26"
    - "本框架 EPS-2026"
    - "本框架基准 EPS26"
  baseline_eps_2027:
    - "基准 EPS27"
    - "本框架 EPS-2027"
  market_cap_yi:
    - "市值"
    - "总市值"
```

CONS-baseline-eps / CONS-derived 用这些别名扫正文。

### 2.4 targets（三档目标价 + 乘法关系）

```yaml
targets:
  short:  {low: 96,  high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:    {low: 110, high: 125, pe_low: 22,   pe_high: 25,   eps_var: baseline_eps_2026}
  long:   {low: 150, high: 180, pe_low: 25,   pe_high: 30,   eps_var: baseline_eps_2027}
```

**自洽要求：** `low == pe_low * ctx[eps_var]` ±1%（high 同）。CONS-target-mult 强制。

### 2.5 anomalies（仅 CRITICAL + HIGH）

```yaml
anomalies:
  - {id: ANO-001, severity: CRITICAL, indicator: 营收, period: 2025FY, value: -54.55, unit: "%"}
  - {id: ANO-002, severity: CRITICAL, indicator: 归母净利, period: 2025FY, value: -71.89, unit: "%"}
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: "pct"}
```

MEDIUM 不进 invariants（由 fact-checker subagent 软检）。

## 3. 可选段（对齐 分析框架.md v6.0-fusion）

### 3.1 five_dim_score（五维综合评分 100 分）

```yaml
five_dim_score:
  fundamental: 28    # /40
  capital: 12        # /20
  technical: 8       # /15
  sentiment: 11      # /15
  catalyst: 6        # /10
  total: 65          # /100
  grade: C           # A(80-100) / B(60-79) / C(40-59) / D(<40)
```

### 3.2 rubric_six_dim（Step 3 Rubric 100 分）

```yaml
rubric_six_dim:
  fundamental: 15      # /30
  industry_fit: 20     # /20
  elasticity: 15       # /20
  valuation: 10        # /15
  capital: 5           # /10
  governance: 5        # /5
  total: 70            # /100
  passed: 13           # /20 项
```

### 3.3 speculation_risk（5 维炒作风险 100 分）

```yaml
speculation_risk:
  fundamental_decoupling: 18    # /20，越高越健康
  valuation_bubble: 15
  fund_speculation: 12
  sentiment_hype: 16
  technical_pattern: 14
  total: 75                     # /100
```

### 3.4 screening_19（19 项快速筛选）

```yaml
screening_19:
  passed: 17
  total: 19
  failed_items: [VAL-01, FUND-01]
```

## 4. verify_consistency 六类检查

| ID | 规则 | 触发对象 |
|----|------|---------|
| CONS-derived | derived 算式重算 = 正文 keyword 附近数字 ±1% | 必填 derived |
| CONS-target-mult | targets.{level}.{bound} = pe_{bound} × ctx[eps_var] ±1% | 必填 targets |
| CONS-anomaly-title | `### ANO-XXX` 标题数字 ≈ invariants.anomalies[X].value ±5%（unit-anchored） | 必填 anomalies |
| CONS-baseline-eps | keywords.baseline_eps_XXXX 别名附近数字 ≈ constants.baseline_eps_XXXX ±1% | 必填 keywords + baseline_eps |
| CONS-score-consistency | 5/6 维分加和 == total；grade 区间一致；screening_19.passed + len(failed_items) == total | 可选段 |
| CONS-explicit-ref | `{{$path}}` 可解析 | 显式引用 |

## 5. 显式引用语法

```markdown
中期目标价 {{$targets.mid.low}}-{{$targets.mid.high}} 元
ANO-001 数值：{{$anomalies.ANO-001.value}}%
基准 EPS26 = {{$constants.baseline_eps_2026}} 元
```

- 普通字段：`{{$constants.X}}` / `{{$derived.X}}` / `{{$targets.level.field}}`
- anomalies 数组：用 id 作主键 `{{$anomalies.ANO-001.value}}`（不用 array index 避免脆弱）

## 6. 完整范例（五粮液 000858 · 困境反转 + 高股息）

````yaml
constants:
  price: 86.87
  shares: 38.82
  book_value_per_share: 32.975166
  baseline_eps_2026: 5.00
  baseline_eps_2027: 6.00

keywords:
  baseline_eps_2026: ["基准 EPS26", "本框架 EPS-2026", "本框架基准 EPS26"]
  baseline_eps_2027: ["基准 EPS27", "本框架 EPS-2027"]
  market_cap_yi: ["总市值", "市值"]

derived:
  market_cap_yi: "price * shares"
  pe_2026e_base: "price / baseline_eps_2026"
  pb: "price / book_value_per_share"

targets:
  short: {low: 96, high: 100, pe_low: 19.2, pe_high: 20.0, eps_var: baseline_eps_2026}
  mid:   {low: 110, high: 125, pe_low: 22,  pe_high: 25,  eps_var: baseline_eps_2026}
  long:  {low: 150, high: 180, pe_low: 25,  pe_high: 30,  eps_var: baseline_eps_2027}

anomalies:
  - {id: ANO-001, severity: CRITICAL, indicator: 营收, period: 2025FY, value: -54.55, unit: "%"}
  - {id: ANO-002, severity: CRITICAL, indicator: 归母净利, period: 2025FY, value: -71.89, unit: "%"}
  - {id: ANO-003, severity: CRITICAL, indicator: 经现金流/营收, period: 2026Q1, value: -0.11, unit: ""}
  - {id: ANO-005, severity: HIGH, indicator: 资产负债率, period: 2023-2026Q1, value: 15.69, unit: pct}

rubric_six_dim:
  fundamental: 15
  industry_fit: 20
  elasticity: 15
  valuation: 10
  capital: 5
  governance: 5
  total: 70
  passed: 13
````

## 7. 累积流程

```
Phase 2 §1 写 part1 → 填 constants（price/shares/book_value），baseline_eps 占位 TBD
Phase 2 §2 写 part2 → 写 Step 4 情景表时回填 baseline_eps，加 derived/keywords
Phase 2 §3 写 part3 → 写 Step 6 目标价时回填 targets，可选段评分
合并 report.md     → verify_facts (单点) → verify_consistency (跨节)
```

Phase 2 三段 partial 校验不要求 invariants 完整（允许 TBD 占位），仅在合并后必须完整。

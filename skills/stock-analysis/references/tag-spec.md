# 数字标签语法 · v3.1

报告 MD 中**每个具体数字**必须带标签，否则 verify_facts.py fail。

## 四类标签

| 标签 | 含义 | 反查方式 |
|---|---|---|
| `[F:path]` | Fact — data.json 字段精确值 | resolve_path → ±1% |
| `[C:formula]` | Computed — 由 F 算出 | eval_formula → ±1% |
| `[I:reason]` | Inference — 推断 | reason ≥4 字中文 |
| `[T:assumption]` | Target/projection — 估算 | 200 字内须有"失效条件" |
| `[GAP:field]` | Gap — 信息缺失 | 统计，不报错 |

## path 语法（[F:] 用）

点号分隔，支持：
- 简单字段：`quote.price`
- 数组下标：`research[0].2026_eps` / `kline_daily[-1][2]`
- 报告期键（YYYYMMDD）：`financial_abstract.20260331.归母净利润`
- 嵌套：`financials[2025].revenue`

## formula 语法（[C:] 用）

允许：`+ - * /`、数字字面量、`<path>` 引用。

示例：
- `[C:quote.price * 547887000]`
- `[C:financials[2025].revenue / financials[2024].revenue - 1]`

## reason 规则（[I:] 用）

- 必须中文，≥ 4 字
- 禁止：`see above` / `推断` / `常识` 等空泛
- 推荐：`行业常识·钛合金锻造龙头` / `Step 4 情景分析期望值` / `产业链调研·2025-10`

## assumption 规则（[T:] 用）

- 必须在 200 字窗口内出现 `失效条件:` 或 `失效条件：`
- 推荐配套乘法表（≥ 3 行 `├─` 字符）

## GAP 规则

- 标准句式：`[GAP: <字段> 在 data.json 缺失，需 <web补/调研补>]`
- 报告头部按 Step 自动汇总
- 若某 Step GAP > 50% 该字段需求 → 自动加 ⚠ 警告条

## 嵌入位置

- 必须紧跟数字（同行内）
- 数字与标签之间允许出现单位（亿/%/倍/元/万手）

## 哪些数字不需要标签

- 日期（2026-05-15）
- 版本号（v3.1）
- Step 编号（Step 0.5）
- 锚点编号（A001）
- 通用计数（"3 条 / 5 项"）

## 示例

```markdown
营收 15.89 亿 [F:financials.2025.revenue]
市值 162.5 亿 [C:quote.price * quote.total_shares]
市占率 60% [I:行业常识·30吨以上钛合金锻件唯一民营龙头]
中期 ¥36-42 [T:基准EPS 0.95 × PE 30-33x]

失效条件:
- 2026Q2 净利继续负增 → 区间下沿失守
[GAP: top_holders 在 data.json 缺失，需 web 补]
```

# 数字标签语法 · v3.1

报告 MD 中**每个具体数字**必须带标签，否则 verify_facts.py fail。

## 五类标签

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
- 数组下标（单层）：`research[0].2026_eps` / `blocks.fund_flow[-1].收盘价`
- ⚠️ v3.2 起 TAG_RE 仅认一层 `[N]`，多层下标（如 `kline_daily[-1][2]`）请改用对象字段路径
- 报告期键（YYYYMMDD）：`financial_abstract.20260331.归母净利润`
- 嵌套：`financials[2025].revenue`

## formula 语法（[C:] 用）

允许：`+ - * /`、数字字面量、`<path>` 引用。

**v3.2 扩展白名单函数：**
- `pow(x, y)` — 幂运算
- `sqrt(x)` — 平方根
- `abs(x)` — 绝对值

**v3.2 修复：** 公式中独立 `-` 现在被识别为运算符（v3.1 会误判为 path token，已修）。

**CAGR 示例：** `[C:pow(financials.营业总收入.20251231|亿 / financials.营业总收入.20221231|亿, 1/3) - 1]`

示例：
- `[C:quote.price * 547887000]`
- `[C:financials[2025].revenue / financials[2024].revenue - 1]`

## 单位后缀（v3.2）

`[F:path|单位]` 与 `[C:formula|单位]` 末尾允许 `|单位` 后缀，verify_facts 按单位归一化后比对。

| 单位 | scale (除数) | 含义 |
|------|-----------|------|
| `亿` | 1e8 | data 值 / 1e8 后比对（金额类常用） |
| `万` | 1e4 | |
| `千` | 1e3 | |
| `%` | 1 | data 已百分制（akshare 字段），不缩放 |
| `pct` | 1 | 同 %，文档习惯 |
| `倍` | 1 | 同 1 |
| `元` | 1 | 默认，等价于不带后缀 |

**示例：**

```
营收 405.29 亿 [F:financials.营业总收入.20251231|亿]
资产负债率 34.31% [F:financials.资产负债率.20260331|%]
市值 3372.29 亿 [C:price * shares|亿]
```

**向后兼容：** 不带 `|单位` 等同 v3.1 行为（直接比对原始值）。

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
毛利 6.32 亿 [C:financials[2025].revenue * financials[2025].gross_margin]
市占率 60% [I:行业常识·30吨以上钛合金锻件唯一民营龙头]
中期 ¥36-42 [T:基准EPS 0.95 × PE 30-33x]

失效条件:
- 2026Q2 净利继续负增 → 区间下沿失守
[GAP: top_holders 在 data.json 缺失，需 web 补]
```

## 常见错误速查（v3.2）

下列陷阱在 v3.1 实际跑出来过；v3.2 已修，列出供 agent 理解为什么 tag-spec 现在长这样：

| 陷阱 | v3.1 现象 | v3.2 修法 |
|------|----------|----------|
| 嵌套下标被截断 | `[F:kline_daily[-1][2]]` 解析成 `kline_daily[-1` | TAG_RE 改写支持一层 `[N]`；多层禁用 |
| 独立 `-` 被当 path | 公式 `a / b - 1` 抛 `formula token - 无法解析` | FORMULA_TOKEN replace 中放行单字符运算符 |
| 单位错配 100 倍差异 | 报告写"405.29 亿"，data.json 存 `4.053e10` 元 | 用 `|亿` 后缀让 verify 归一化 |
| CAGR 无法表达 | `(end/start)^(1/3) - 1` 用 + - * / 写不出 | `pow(end / start, 1/3) - 1` |
| 数字标签距离过远 | tag 前 30 字符外的最近数字会被错抓 | tag 必须紧贴目标数字（同行 < 20 字符） |

**预防原则：**
- 金额类标签**始终加** `|亿` 后缀（除非数字真的以元为单位）
- 含数组下标的 path 仅嵌一层 `[N]`，更深嵌套改用对象字段
- 公式包含 `-` 时 always 写空格隔开（`a - b`，不是 `a-b`）

---
name: stock-analysis
description: |
  A股个股深度研究系统。当用户提到"分析XXX股票"、"看下XXX"、"研究XXX"、
  "XXXX值得买吗"、"XXX怎么样"、"XXX基本面"，或直接给出6位A股代码
  （000/001/002/300/301/600/601/603/605/688 开头），自动触发三阶段流程：
  Phase 1 数据采集（K线/财务/股东）→ Phase 2 Step 0-8 深度分析（产业链/弹性/估值/盈亏比/止损信号）
  → Phase 3 手写 HTML 研究报告。
  生成结果为 output/<股票名>_<代码>/<YYYY-MM-DD>/ 下的 data.json + report.md + report.html。
  本工具仅供研究参考，不构成证券投资咨询业务，不构成投资建议。
metadata:
  argument-hint: <股票代码 或 股票名称>
---

# stock-analysis · 个股深度研究系统

## Agent 阅读顺序

1. **本文 SKILL.md** — 阶段总览（你正在读）
2. **Phase 1.5 时** → `output/.../data_inventory.md` + `output/.../anomalies.md`（自动产出）
3. **Phase 2 写每段前** → [references/tag-spec.md](references/tag-spec.md) + [references/analysis-framework.md](references/analysis-framework.md) 对应 Step
4. **Phase 2 评分** → [references/rubric-spec.md](references/rubric-spec.md)
5. **Phase 2 异常** → [references/anomaly-rules.md](references/anomaly-rules.md)
6. **Phase 3 时** → [references/html-spec.md](references/html-spec.md) + [references/batch-checklist.md](references/batch-checklist.md)
7. **写/读 data.json 时** → [references/data-schema.md](references/data-schema.md)
8. **Phase 3 末** → 跑 [scripts/verify_html.sh](scripts/verify_html.sh)（含 verify_content.py）

---

## 触发示例

| 用户说 | 触发 |
|--------|------|
| `分析 002594` | ✓ |
| `看下比亚迪` | ✓ |
| `002594 值得买吗` | ✓ |
| `比亚迪基本面怎么样` | ✓ |
| `帮我研究下比亚迪` | ✓ |

---

## 阶段时序（v3.2）

```text
Phase 1   数据采集
  └─ fetch_data.py 末尾自动 chain：
       build_inventory.py → data_inventory.md
       scan_anomalies.py  → anomalies.{json,md}

Phase 1.5 数据 checkpoint
  └─ agent 必读 data_inventory.md + anomalies.md
  └─ ❌ 字段必须 web_fetch 补 或 显式 [GAP]
  └─ CRITICAL anomaly 必须在 Step 0.5 整段讨论

Phase 2  深度分析（三段检点制 + 标签 + invariants）
  §1 (Step 0, 0.5, 1, 2) → part1 → verify_facts.py --partial part1
       └─ v3.2：part1 必须含 invariants YAML 块（compliance 之后）
  §2 (Step 3, 4, 5)       → part2 → verify_facts.py --partial part2
       └─ v3.2：§2 增量回填 invariants（baseline/derived 字段）
  §3 (Step 6, 7, 8)       → part3 → verify_facts.py --partial part3
       └─ v3.2：§3 增量回填 invariants（target_price 乘法表）
  合并 cat part*.md > report.md
  ↓ v3.2 新增：合并后必须跑 verify_consistency
  verify_consistency.py --report report.md --data data.json  # 0 FAIL

Phase 2.5 Fact-checker（v3.2 仅负责软问题）
  └─ verify_facts.py FULL → 必须 0 FAIL
  └─ verify_consistency.py FULL → 必须 0 FAIL（数值/单位/算式硬错由脚本抓）
  └─ Task(general-purpose subagent) → fact-check-report.md（仅查推断合理性 / 矛盾）
  └─ FAIL 项必须 Edit 修正后重跑（最多 3 轮）

Phase 2.6 Bear-case
  └─ Task(general-purpose subagent) → bear-case.md
  └─ append 到 report.md 作为新 section

Phase 3   HTML 6 批分批手写
  └─ verify_html.sh（含 verify_content.py）→ 0 FAIL
  └─ 删除中间产物 _h_part*.html
```

> **v3.2 变化：** Phase 2 §1 写 part1 时 agent 必须在 compliance 声明之后插入 invariants YAML 块（schema 见 [references/invariants-spec.md](references/invariants-spec.md)），后续 §2 §3 增量回填。合并 report.md 后必跑 verify_consistency。

### Phase 2.5 fact-checker sub-agent prompt（agent 复制粘贴用）

```text
你是审稿人。检查 report.md 数字准确性 + 推断合理性。

【输入】report.md / data.json / anomalies.md（路径见此次 output 目录）

【任务】（v3.2 起仅负责"软问题"，硬错由 verify_facts + verify_consistency 自动抓）
1. 抽样 20 个 [F:] / [C:] 标签，看推断依据是否过于宽泛（"行业常识·龙头地位"这种宽泛理由不通过）
2. 检查所有 [I:] 推断（约 50+ 处）的依据合理性
3. 找出 anomalies.md 中存在但报告中未充分讨论的异常（特别 MEDIUM 级，未进 invariants）
4. 找出 bear-case 是否引用了至少 2 条 ANO（v3.1 要求）
5. 找出报告内部矛盾（特别是 Step 4 情景假设 vs Step 6 目标价假设的语义一致性，数值由 verify_consistency 已抓）

【明确不再做】（已由脚本覆盖）
- 跨节同变量数值是否一致（CONS-baseline-eps / CONS-derived 覆盖）
- 目标价乘法表自洽（CONS-target-mult 覆盖）
- ANO 标题与 invariants 一致（CONS-anomaly-title 覆盖）
- 派生量与算式自洽（CONS-derived 覆盖）

【输出】fact-check-report.md
- PASS: N / FAIL: M / WARN: K
- 每条 FAIL 必含：location + 问题描述 + 修复指令
```

### Phase 2.6 bear-case sub-agent prompt

```text
你是空头分析师。基于 report.md 与 anomalies.md，写 300-500 字对立面观点。

【任务】
1. 找出 3 条主 agent 没充分讨论的负面证据
2. 给出"如果多头观点错了，错在哪里"的具体路径
3. 反驳报告中关键的 [I:] 推断
4. 提出 3 条"如果出现 X 信号，则空头观点确认"的可观测指标

【输出】bear-case.md（不需要标签）
- 必须引用 anomalies.md 中至少 2 条 ID
```

---

## Phase 1 · 数据采集（3-5 min）

**所需数据：** 近 3 年日 K 线、近 3 年财务（营收/净利/毛利/ROE）、主营业务构成、十大股东、近期新闻。

**实现方式（任选）：**

| 方式 | 命令 |
|------|------|
| akshare 参考脚本 | `python scripts/fetch_data.py <代码> [--date YYYY-MM-DD]` |
| 财经类 MCP | agent 直接调用 |
| web_fetch | agent 自行抓取雪球/东财公开页 |
| 手工上传 | 用户提供 CSV/JSON |

**输出：** `output/<股票名>_<代码>/<YYYY-MM-DD>/data.json`，schema 见 [references/data-schema.md](references/data-schema.md)。

---

## Phase 2 · AI 深度分析（30-45 min · 三段检点制）

| 段 | 包含 Step | 落盘 |
|----|-----------|------|
| §1 | Step 0-2（任务/宏观/产业链） | `report.md.part1` |
| §2 | Step 3-5（公司质地/弹性/风险） | `report.md.part2` |
| §3 | Step 6-8（估值/对标/跟踪结论） | `report.md.part3` |
| 合并 | — | `cat part* > report.md` |

**节奏：**
- 同会话默认三段连续执行，不询问"是否继续"
- 每段完成输出 `✅ §X 完成（XX 行 / Step A-B）`
- 跨会话续跑：读 `output/<股票名>_<代码>/latest/` 下已存在的 part 文件决定起点

**最低行数（不可少）：** Step 0:10 / 1:50 / 2:100 / 3:50 / 4:80 / 5:40 / 6:100 / 7:60 / 8:50（合计 540 行）。

**方法论详见：** [references/analysis-framework.md](references/analysis-framework.md)

---

## Phase 3 · HTML 生成（30-40 min · 6 批分批手写）

**工具分工：**
- Write 写 markup / Edit 局部改 / Bash cat 字节拼接
- **禁止：** Python f-string、Bash heredoc、`python -c` 拼字符串

**6 批方案（每批 ≤300 行，写完跑该批 grep 校验）：**

| 批 | 内容 | 主要 grep 校验 |
|----|------|---------------|
| 0 | DOCTYPE + head + style（完整复制 `templates/template_base.css`） | `grep -c '<style>'=1`、accent token 存在 |
| 1 | body + nav + compliance + hero + conclusion-top + profile | nav 13 锚点、4 hero-meta、compliance-banner 存在 |
| 2 | financial-grid + K线 + Step 0-3 | mission/macro/chain/quality 四 id 存在 |
| 3 | Step 4-6（弹性/风险/估值） | elasticity/risk/valuation 三 id 存在 |
| 4 | Step 7-8 + 总结框 + footer | // CONCLUSION 存在、footer 内 `<strong>` = 0 |
| 5 | script（完整复制 `templates/template_base.js`，注入 rawData/pieData） | `__RAW_DATA`/`__PIE_DATA` = 0 |
| 合并 | `cat _h_part*.html > report.html` 然后 `bash scripts/verify_html.sh report.html` | 全 PASS |

**详细分批指南（含 ANCHOR 用法、每批 grep 命令、失败处理）：**
[references/batch-checklist.md](references/batch-checklist.md)

**HTML 设计规范（色板/字体/组件）：**
[references/html-spec.md](references/html-spec.md)

**金标范例：**
[examples/比亚迪_002594.html](examples/比亚迪_002594.html)

---

## 输出结构

```
output/
└── <股票名>_<代码>/
    ├── <YYYY-MM-DD>/
    │   ├── data.json          # Phase 1
    │   ├── report.md.part1-3  # Phase 2 中间产物
    │   ├── report.md          # Phase 2 合并终版
    │   ├── _h_part0-5.html    # Phase 3 中间产物
    │   └── report.html        # 终交付物
    └── latest -> <YYYY-MM-DD>  # 软链
```

---

## 关键禁止事项

| # | 禁止 | 原因 |
|---|------|------|
| 1 | Python 生成 HTML markup | 转义混乱、难维护 |
| 2 | Bash heredoc 写多行 HTML | EOF 容易匹配失败 |
| 3 | 跳过/简化任何 Step | 完整框架缺一不可 |
| 4 | OHLC 用 [open, high, low, close] | 与 ECharts 默认不符 |
| 5 | MathJax 使用双反斜杠 `\\(...\\)` | 分隔符匹配失败 |
| 6 | accent 色混用金色 / 多色 score-fill 渐变 | 违反 Linear Terminal+ 设计 |
| 7 | footer 使用 `<strong>` / 金色 | 违反纯 Mono footer 规范 |
| 8 | Phase 1 输出旧路径 `output/data_<code>.json` | 应使用 `<股票名>_<代码>/<日期>/` |
| 9 | 一次性写完整 HTML | 必须分 6 批，每批 ≤300 行 |
| 11 | 报告中数字不带 [F]/[C]/[I]/[T]/[GAP] 标签 | verify_facts FAIL，无法进 Phase 3。**v3.2 起：金额类标签建议带 \|亿 后缀，否则单位错配仍会 FAIL** |
| 12 | 跳过 fact-checker 或 bear-case sub-agent | 多 agent 防御纵深失效 |
| 13 | hero meta 显示 A/B/C 字母评级 | v3.1 改用 `Rubric: <total>/100` |
| 14 | Step 8 再次出现 5 维综合评分 | 已取消，仅保留定性结论 |


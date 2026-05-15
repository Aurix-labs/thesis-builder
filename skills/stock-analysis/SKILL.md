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
  author: ll-mingli1221
  version: "3.0.0"
  argument-hint: <股票代码 或 股票名称>
---

# stock-analysis · 个股深度研究系统 v3.0

## Compliance

本工具不构成证券投资咨询业务、不构成投资建议。所生成的目标价、操作建议、评级仅为研究演示，
使用者据此操作的盈亏由使用者本人承担。

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

## 三阶段流程

### Phase 1 · 数据采集（3-5 min）

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

### Phase 2 · AI 深度分析（30-45 min · 三段检点制）

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

**两套评分体系（必须区分）：**
- Step 3 公司质地评分（6 维 / 100 分）— hero meta-row 的 Quality 字段
- Step 8 综合交易评分（5 维 / 100 分）— Step 8 卡片内部

**MD 内容禁止：**
- 任何位置出现 `@ll-mingli1221` / `明立` 等署名（仅 HTML footer 出现）
- 末尾添加署名行

**方法论详见：** [references/analysis-framework.md](references/analysis-framework.md)

---

### Phase 3 · HTML 生成（30-40 min · 6 批分批手写）

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
| 8 | MD 中出现作者署名 | 仅 HTML footer 统一渲染 |
| 9 | Phase 1 输出旧路径 `output/data_<code>.json` | 应使用 `<股票名>_<代码>/<日期>/` |
| 10 | 一次性写完整 HTML | 必须分 6 批，每批 ≤300 行 |

---

## 安装

```bash
npx skills add zhangchao/thesis-builder --skill stock-analysis
# 或全局
npx skills add zhangchao/thesis-builder --skill stock-analysis -g
```

## 相关文档

- [references/analysis-framework.md](references/analysis-framework.md) — Step 0-8 方法论详解
- [references/html-spec.md](references/html-spec.md) — HTML 设计规范
- [references/batch-checklist.md](references/batch-checklist.md) — Phase 3 分批校验清单
- [references/data-schema.md](references/data-schema.md) — Phase 1 输出 JSON schema
- [templates/template_base.css](templates/template_base.css) — 完整样式
- [templates/template_base.js](templates/template_base.js) — K线/饼图配置
- [examples/比亚迪_002594.html](examples/比亚迪_002594.html) — 金标范例
- [scripts/fetch_data.py](scripts/fetch_data.py) — akshare 参考脚本
- [scripts/verify_html.sh](scripts/verify_html.sh) — HTML 自检脚本

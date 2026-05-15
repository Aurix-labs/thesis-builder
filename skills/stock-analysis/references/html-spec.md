# HTML 报告设计规范 · Linear Terminal+

> 本文件是 stock-analysis skill 的 Phase 3 HTML 生成参考。
> Phase 3 开始时 agent 必读本文，所有 CSS class 来自 [../templates/template_base.css](../templates/template_base.css)。
> 分批校验清单见 [./batch-checklist.md](./batch-checklist.md)。

---

## 1. 设计语言锚定

报告 HTML 锚定 [Linear Terminal+](../../../docs/superpowers/specs/2026-05-15-stock-analysis-rewrite-design.md#10-设计语言--linear-terminal) 设计语言。
可视化参考：[mockups/aesthetic-preview.html](../../../mockups/aesthetic-preview.html) 中的 B 区块。

**核心特征：**
- 近黑底 #010102 + 单一 lavender #5e6ad2 强调
- Inter 大字标题 + IBM Plex Mono 数据/标签
- Dot grid 背景 + 顶部 lavender radial gradient
- 关键数字 text-shadow 发光（目标价、目标涨跌幅、状态点）
- Hairline 1px 分隔线 + tabular-nums 数字

## 2. 色板（与 template_base.css 一致）

    --canvas:         #010102;
    --surface-1:      #0c0d10;
    --surface-2:      #15161a;
    --hairline:       #1f2128;
    --hairline-strong: #23252a;

    --ink:            #f7f8f8;
    --ink-muted:      #d0d6e0;
    --ink-subtle:     #8a8f98;
    --ink-tertiary:   #62666d;

    --accent:         #5e6ad2;
    --accent-hover:   #828fff;
    --accent-glow:    rgba(94, 106, 210, 0.5);
    --accent-soft:    rgba(94, 106, 210, 0.06);

    --semantic-up:    #27a644;
    --semantic-down:  #ff5a5f;
    --semantic-warn:  #ffcc00;

**用色纪律（禁止违反）：**
- 同一报告内 accent 色仅一种（lavender），不允许在 lavender + 金色 + 橙色 之间混用
- 涨绿跌红遵循 A 股惯例（涨 #ff5a5f / 跌 #27a644），所有 K 线、涨跌幅一致
- Footer 全部用 `--ink-tertiary`，禁止任何 `<strong>` / 金色 / 高亮

## 3. 字体

    --font-display: 'Inter', -apple-system, 'Noto Sans SC', sans-serif;
    --font-body:    'Inter', -apple-system, 'Noto Sans SC', sans-serif;
    --font-mono:    'IBM Plex Mono', 'JetBrains Mono', 'Menlo', monospace;

- 所有数字（财务、目标价、占比、涨跌幅、日期、时间戳）使用 `--font-mono` + `font-variant-numeric: tabular-nums`
- 所有 mono 标签（meta-row 的 k 字段、section eyebrow、status text）：10-11px、letter-spacing 1.5-2px、UPPERCASE
- 中文正文：`--font-body`，15px、line-height 1.65

## 4. 关键组件

### 4.1 Top bar（nav 替代品）

固定顶部，Mono 11px，左侧 `<状态点>DEEP RESEARCH · v3 · ACTIVE`，右侧 `SESSION 0x… · YYYY-MM-DD HH:MM UTC+8`。
状态点：8×8 lavender 圆 + `box-shadow: 0 0 12px #5e6ad2, 0 0 24px rgba(94,106,210,.4)` + pulse 1.6s 动画。

### 4.2 合规 banner（必需）

`<div class="compliance-banner">[RESEARCH ONLY] 本报告仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。</div>`

样式：lavender 1px 描边、`rgba(94,106,210,.06)` 背景、Mono 11px、padding 12px 24px。位于 top-bar 下、hero 上。

### 4.3 Hero

两列 grid（左大字 ticker + lead；右 sparkline + 日内涨跌）：
- ticker：Inter 56px / 600 / -2px letter-spacing
- code（如 `002594.SZ`）：Mono 18px / `--ink-tertiary` / vertical-align: super
- lead（一句话核心矛盾）：Inter 17px / `--ink-subtle` / max-width 640px
- sparkline：220×50 inline SVG，2px stroke `--semantic-down` 或 `--semantic-up`，下方半透明 area fill

### 4.4 Meta row

4 列 grid，1px gap，圆角 6px，border `--hairline`：
- 列背景：`linear-gradient(180deg, rgba(94,106,210,.04), transparent 60%), --surface-1`
- 每列：Mono k（10px uppercase）+ Mono v（28px tabular）+ 可选 sub（Mono 11px `--ink-tertiary`）
- 4 列固定：Quality / Target / R/R / Risk
- Target 列 v 加 lavender 发光：`color: var(--accent-hover); text-shadow: 0 0 16px var(--accent-glow)`

### 4.5 Data grid（财务表）

无外阴影、`--surface-1` 底、`--hairline` 1px 边：
- 表头一行：Mono 10px uppercase，字色 `--accent`，padding 12px 20px
- 数据行：Mono 13px tabular-nums，行间 1px `--hairline`
- 首列字色 `--ink-subtle`，其余 `--ink-muted`
- 正数色 `--semantic-up`，负数色 `--semantic-down`

### 4.6 Section eyebrow

每个 Step 卡片标题上方一行：`// section-name · step_XX`，Mono 10px / 1.8px letter-spacing / uppercase / `--accent`。

### 4.7 评分条（评分维度）

5 段刻度 mono bar：
- 容器：宽 100%、高 6px、`--surface-2` 底
- 填充：5 段 `--accent`（每段宽 18%、间 1px gap）
- 已达段：opacity 1；未达段：opacity 0.2

**禁止：** 旧版的金/橙/红渐变 score-fill。每个评分条结构如下：

    <div class="score-track">
      <div class="score-seg lit"></div>
      <div class="score-seg lit"></div>
      <div class="score-seg lit"></div>
      <div class="score-seg dim"></div>
      <div class="score-seg dim"></div>
    </div>

### 4.8 产业链 SVG

单色 `--ink-subtle` 细线 wireframe + lavender 强调关键节点。
文字 class：`.svg-hdr`（13px / 500 / `--ink`）/ `.svg-sub`（11px / 400 / `--ink-subtle`）。
每个 `<text>` ≤ 14 个中文字，超出换行（y+22）。

### 4.9 弹性树

灰色细框 + lavender 强调 + Mono 数据：
- 顶层节点：1px `--accent` 边框
- 连接竖线：1px × 6px `--accent`
- 横线：1px `--accent`
- 子节点 3 列 flex（2:1:1），每个含业务名 + 营收占比 + 毛利率 + 弹性因子
- 核心业务 lavender 边框；次要业务 `--hairline-strong` 边框

**禁止：** 旧版的红/金/灰 emoji 节点。

### 4.10 三档目标价

一行 hairline data row（不是 grid-3 卡片）：

    SHORT-TERM    MID-TERM         LONG-TERM
    ¥10.50        ¥12.40 ↗ +18.3%  ¥15.80

中期目标价（基准）：lavender 字色 + `text-shadow: 0 0 16px var(--accent-glow)`。

### 4.11 总结框

mono eyebrow `// CONCLUSION` + 朴素 `.card`（无红色左边框、无 emoji）。

### 4.12 Footer

全部 Mono、单色 `--ink-tertiary`：

    <footer>
    <p>⚠ 免责声明：本报告仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。</p>
    <p>数据截止：{date} · 研究状态：{首次覆盖/持续跟踪}</p>
    <p>数据来源：akshare </p>
    </footer>

**禁止：** `<strong>`、金色、emoji 装饰。

## 5. 强制约束

| # | 约束 | 检查方式 |
|---|------|---------|
| 1 | OHLC 顺序必须 [open, close, low, high] | grep rawData 检查首行 |
| 2 | 成交量柱每根单独着色（红涨绿跌） | 检查 itemStyle.color 函数 |
| 3 | MathJax 使用 `\(...\)` 单反斜杠 | `grep -c '\\\\(' report.html` = 0 |
| 4 | 所有 CSS class 来自 template_base.css | 见 batch-checklist.md grep |
| 5 | Footer 无 strong / 金色 | `grep '<strong>' footer段` = 0 |
| 6 | 占位符清零 | `grep '__[A-Z_]*__'` = 0 |
| 7 | score-track 5 段 + lit/dim class | 每条评分条 5 个 score-seg |
| 8 | accent 色仅 lavender，无金/橙混用 | grep `gold\|orange` 在 inline style 中 = 0 |

## 6. 强制页面结构（顺序不可变）

    top-nav (sticky)
    compliance-banner
    .hero
    .conclusion-top
    .grid-2(公司画像 + 近期动态)
    .grid-2(主营业务饼图 + 关键财务指标)
    .card K线图(#chart-kline-full, 480px) + kpi-info-row
    .card#mission        任务锁定与核心矛盾
    .card#macro          宏观与周期定位
    .card#chain          产业链深度拆解
    .card#quality        公司筛选与质量评分
    .card#elasticity     业绩弹性测算
    .card#risk           风险分析
    .card#valuation      估值与买卖时机
    .card#compare        对标分析
    .card#tracking       跟踪计划与综合结论
    .card#conclusion     // CONCLUSION 总结框
    footer

## 7. 时间维度（必需）

- `<title>` = `比亚迪 002594 · 深度研究 · 2026-05-15`
- top-bar 右侧：`SESSION 0x{随机4位hex} · YYYY-MM-DD HH:MM UTC+8`
- meta row 添加第 5 项："AS OF / 数据截止"（如 4 列不够，hero 下方独立 sub-line）
- 三档目标价显式注脚："基于 YYYY-MM-DD 收盘价 ¥XXX"
- 若数据距今 >7 天：顶部 lavender bar `⚠ 数据已 X 天未刷新，建议重新生成`

---

详细分批步骤与 grep 校验：[batch-checklist.md](./batch-checklist.md)。

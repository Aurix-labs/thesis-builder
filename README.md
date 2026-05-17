# thesis-builder

一个 Claude / Cursor / Codex / OpenCode 等 AI agent 通用的 **投资研究 skill 集合**。
首批包含 `stock-analysis` —— A 股个股深度研究系统。

> 本工具仅供研究参考，不构成证券投资咨询业务，不构成投资建议。投资有风险，决策需谨慎。

---

## 安装

### 方式 1：通过 Vercel Skills CLI（推荐）

```bash
# 全局安装（投放到所有支持的 agent）
npx skills add Aurix-labs/thesis-builder --skill stock-analysis -g

# 仅本项目
npx skills add Aurix-labs/thesis-builder --skill stock-analysis

# 安装到指定 agent
npx skills add Aurix-labs/thesis-builder --skill stock-analysis -a claude-code
npx skills add Aurix-labs/thesis-builder --skill stock-analysis -a cursor
```

CLI 自动按 agent 投放到正确位置：Claude Code → `~/.claude/skills/stock-analysis/`、Cursor → `~/.cursor/skills/stock-analysis/`、等等。

### 方式 2：手动复制

```bash
git clone https://github.com/Aurix-labs/thesis-builder
cp -r thesis-builder/skills/stock-analysis ~/.claude/skills/
```

---

## 当前 Skills

### stock-analysis · v4.0（模块化）

A 股个股深度研究系统，原始 Step 0-8 框架拆为 **7 个独立分析模块 + 1 个合成层**，每个模块按内容变化频率独立 TTL 复用快照，让用户按需调用单一维度而不必每次跑全套。

**模块清单：**

| 模块 | 主名 | 内容 | TTL |
|---|---|---|---|
| 产业链与趋势 | `chain` | 宏观周期 + 产业链拆解 + 趋势三要素 | 90 天 |
| 公司质地 | `rubric` | Rubric 100 分评分 + 不碰清单 | 90 天 |
| 业绩弹性 | `elasticity` | 弹性树 + 价格敏感度 + 悲观/基准/乐观 | 90 天 |
| 风险与止损 | `risk` | 风险清单 + 异常分析 + 逻辑破坏条件 | 30 天 |
| 估值与赔率 | `valuation` | 估值方法 + 三档目标价 + 盈亏比 | 7 天 |
| 资金与技术面 | `flow-tech` | 筹码/资金流 + K 线 6 维（位置/趋势/量价/MACD/RSI/KDJ） | 1 天 |
| 同业对标 | `peers` | 同业自动选股 + 5 维对比表 | 90 天 |
| 合成报告 | `report` | Step 0 + Step 8 + bear-case + fact-check + HTML | — |

**使用：**

```bash
# 全景研究报告（默认）
分析 002594
看下比亚迪

# 单模块调用（节省 token，TTL 内自动复用快照）
002594 估值多少
比亚迪技术面怎么样
002594 的产业链
比亚迪 质地和风险

# 强制刷新（覆盖 TTL）
重新跑下 002594 的估值
```

**输出：**

```
output/<股票名>_<代码>/
├── chain/<ymd>/{data.json, report.md}        + latest 软链
├── rubric/<ymd>/{data.json, report.md}       + latest
├── elasticity/<ymd>/{data.json, report.md}   + latest
├── risk/<ymd>/{data.json, report.md, anomalies.md, anomalies.json}  + latest
├── valuation/<ymd>/{data.json, report.md}    + latest
├── flow-tech/<ymd>/{data.json, report.md}    + latest
├── peers/<ymd>/{data.json, report.md, peers.txt}  + latest
└── report/<ymd>/{report.md, fact-check.md, report.html, manifest.json}
```

单模块只出 markdown；合成 `report` 才生成 HTML（每次新跑，引用各模块最新快照）。

**核心特性：**

- **模块化拆分** —— 用户可按需调用单一维度（如只跑估值），不必每次跑完整流程
- **TTL 复用** —— 各模块按内容变化频率独立设 TTL，TTL 内强制复用快照不重新拉数据、不重新跑 LLM 分析
- **强解耦** —— 模块间分析输出彼此不引用；删除任一模块的目录不影响其他模块
- **脚本管事实 + agent 管推理** —— 数据采集与文件操作走 Python（可测试），分析写作由 agent 按 references/modules/<m>.md 完成
- **Linear Terminal+ 设计语言** —— 近黑 + lavender 单点缀 + Mono 数据，仅在合成 HTML 时启用

**详见：** [skills/stock-analysis/SKILL.md](skills/stock-analysis/SKILL.md)、[skills/stock-analysis/config.yaml](skills/stock-analysis/config.yaml)（用户可编辑 TTL / 别名）

---

## 研究哲学

stock-analysis 跟"另一个 AI 股票分析"的差异在七条研究原则与三条底线。这些原则在各模块的方法论文件中被显式约束（见 [skills/stock-analysis/references/modules/](skills/stock-analysis/references/modules/)）。

### 七条原则

1. **产业驱动，非情绪驱动** — 顺的是产业趋势，不是 K 线趋势。产业逻辑是核心，技术面和资金面是辅助验证。
2. **先验证，后结论** — 至少完成"趋势三要素"再下结论；基本面 + 资金面 + 技术面三重交叉验证。
3. **先风控，后收益** — 每份报告必须写清失效条件、止损位、逻辑破坏条件。
4. **盈亏比思维** — 量化"向下 X% 空间 vs 向上 Y% 空间"，给出三档目标价（短/中/长）。
5. **看大象比看蚂蚁容易** — 优先研究信息透明度高的龙头；百亿以上市值优先，60 亿以下慎重。
6. **低位谈逻辑，高位讲情绪** — 位置决定分析重心；高位关注拥挤度和资金面。
7. **宁可错过，不可做错** — 等业绩拐点确认，不急于抄底；识别"真成长"与"伪题材"。

### 三条底线（不可违反）

1. **先事实、后推断** — 关键结论必须有数据日期和来源。
2. **先验证、后判断** — 至少完成"趋势三要素"再下结论。
3. **先风控、后收益** — 每份报告必须写清失效条件。

### 方法论闭环

> 先市场定价 → 反推产业逻辑 → 回到公司业绩验证 → 交易与风控

产业层面（宏观 → 产业链 → 细分产品）自上而下扫描；个股层面（筛选 → 弹性测算 → 估值风控）按 Step 0-8 执行。

---

## Phase 1 依赖（可选）

如使用 akshare 参考脚本：

```bash
pip install -r skills/stock-analysis/scripts/requirements.txt
```

不依赖 akshare 的方式：使用财经 MCP / web_fetch / 手工上传 CSV，详见 SKILL.md Phase 1 段。

---

## MCP / Search 配置

stock-analysis 的 Phase 2 需要联网搜索（行业趋势、竞品研报）。skill 不绑定特定 MCP；agent 可使用宿主环境提供的任一 web_search / Tavily / Brave / 智谱 / 其他 MCP。

> Skill **不**包含 `.mcp.json` 配置；MCP 是宿主环境的责任。

---

## 项目结构

```
thesis-builder/
├── README.md / LICENSE / CHANGELOG.md / CLAUDE.md
├── docs/
│   └── superpowers/
│       ├── specs/        # 设计文档
│       └── plans/        # 实施计划
├── mockups/              # 设计稿
└── skills/
    └── stock-analysis/   # v4.0
```

---

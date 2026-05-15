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

### stock-analysis · v1.0

A 股个股深度研究系统，按买方/卖方研究员工作流的 Step 0-8 框架，生成可视化 HTML 研究报告。

**使用：**
```
分析 002594
看下比亚迪
```

**输出：** `output/<股票名>_<代码>/<YYYY-MM-DD>/{data.json, report.md, report.html}`

**特性：**
- 三层架构：确定性数据采集（Python akshare）+ AI 深度推理（Step 0-8）+ AI 手写 HTML（分批 + 自检脚本）
- 双评分体系：公司质地评分（6 维）vs. 综合交易评分（5 维）
- Linear Terminal+ 设计语言（近黑 + lavender 单点缀 + Mono 数据）
- 时间维度归档：按日期目录组织，`latest` 软链指向最新

**详见：** [skills/stock-analysis/SKILL.md](skills/stock-analysis/SKILL.md)

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
    └── stock-analysis/   # v1.0
```

---

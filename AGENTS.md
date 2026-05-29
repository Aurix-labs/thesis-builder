# thesis-builder · 项目指引

本仓库是一个 skill 集合，遵循 [Vercel Skills CLI](https://github.com/vercel-labs/skills) 规范。

## 当前 skills

- `skills/stock-analysis/` — A 股个股深度研究系统 v4.0（模块化：7 个独立分析模块 + 1 个合成层，按 TTL 复用快照）

## 安装到本机使用

```bash
npx skills add Aurix-labs/thesis-builder --skill stock-analysis
```

详见 [README.md](README.md)。

## 给 Codex 的指引

- 所有 skill 的实际触发与执行规则均写在各自的 `SKILL.md` 中
- 不要把 skill 内部的细节复制到本文件
- 改动 skill 内任何文件时，先读对应 skill 的 SKILL.md 和其 references/

## 设计文档

- `docs/superpowers/specs/` — 设计文档
- `docs/superpowers/plans/` — 实施计划
- `mockups/` — 设计稿

# Examples

## 比亚迪_002594.html

**角色（v5 起）：** 模板回归测试金样本（不是真实分析输出）。

- 由 `python scripts/render_html.py` 用 [比亚迪_002594_input/](比亚迪_002594_input/) 作为输入渲染而成
- 改模板（`templates/report.html.j2` + partials）或 CSS 时，必须先确认 `pytest scripts/tests/test_render_html.py` 全 PASS，再决定是否更新本金样本
- 视觉对比基准：浏览器打开本文件，逐区块对比新渲染产物

## 比亚迪_002594_input/

**角色：** 金样本的确定性渲染输入。

```
比亚迪_002594_input/
├── data.json        ← 合成后的 merged data.json（含各模块 summary 子键）
├── report.md        ← merged + Step 0/Step 8/bear-case append 后的 report.md
├── bear-case.md     ← 对立面观点（可选）
└── fact-check.md    ← 软问题审查报告
```

**⚠️ 禁止：**
- 不要把文件内的财务数字、目标价、评分当成真实研究结论
- 文件内所有数据均为构造的演示值，仅服务于回归测试

**真实分析输出路径：** `output/<股票名>_<代码>/report/<YYYY-MM-DD>/report.html`（由 skill 在运行时按 Phase 1 → 2 → 3 生成）

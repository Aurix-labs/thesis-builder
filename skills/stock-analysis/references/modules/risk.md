# risk · 风险与止损 · 方法论

> 本模块产出：异常分析 + 风险清单 + 逻辑破坏条件
> 数据输入：`<stock>/risk/<ymd>/data.json`（`meta`/`quote`/`financial_abstract`/`kline_daily`/`notice`/`news`）
> 输出文件：同目录 `report.md`，必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头
> 额外产物：`anomalies.md` + `anomalies.json`

## 强约束

- 数字必须带 `[F:]/[C:]/[I:]/[T:]/[GAP:]` 标签（详见 [../tag-spec.md](../tag-spec.md)）
- 最低行数：40 行
- 必含 section：标的速写 / Step 0.5 异常分析 / 风险清单 / 至少 3 条逻辑破坏条件

## 方法论

[v4 Task 17 填实内容，从 _legacy/analysis-framework.md 的 Step 5 + Step 0.5 + _legacy/anomaly-rules.md 全文切出]

## 报告骨架

```markdown
<!-- THESIS_SNAPSHOT_START -->
（由脚本自动注入，agent 不写）
<!-- THESIS_SNAPSHOT_END -->

## risk 主体
...
```

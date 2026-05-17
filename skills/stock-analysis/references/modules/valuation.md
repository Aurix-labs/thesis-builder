# valuation · 估值与赔率 · 方法论

> 本模块产出：估值方法选择 + 三档目标价 + 研报对比 + 盈亏比量化
> 数据输入：`<stock>/valuation/<ymd>/data.json`（`meta`/`quote`/`financial_abstract`/`research`/`recommend`/`kline_daily`）
> 输出文件：同目录 `report.md`，必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头

## 强约束

- 数字必须带 `[F:]/[C:]/[I:]/[T:]/[GAP:]` 标签（详见 [../tag-spec.md](../tag-spec.md)）
- 最低行数：100 行
- 必含 section：标的速写 / 估值方法选择 / 三档目标价 / 研报对比 / 盈亏比量化

## 方法论

[v4 Task 17 填实内容，从 _legacy/analysis-framework.md 的 Step 6 主体（除 6a+/6a++）切出]

## 报告骨架

```markdown
<!-- THESIS_SNAPSHOT_START -->
（由脚本自动注入，agent 不写）
<!-- THESIS_SNAPSHOT_END -->

## valuation 主体
...
```

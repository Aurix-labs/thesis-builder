# peers · 同业对标 · 方法论

> 本模块产出：对标公司 5 维表 + 增长引擎切换分析
> 数据输入：`<stock>/peers/<ymd>/data.json`（`self` + `peers`）
> 输出文件：同目录 `report.md`，必须以 `<!-- THESIS_SNAPSHOT_START -->` 段开头
> 额外产物：`peers.txt`（每行一个同业代码）

## 强约束

- 数字必须带 `[F:]/[C:]/[I:]/[T:]/[GAP:]` 标签（详见 [../tag-spec.md](../tag-spec.md)）
- 最低行数：60 行
- 必含 section：标的速写 / 对标公司 5 维表 / 增长引擎切换分析

## 方法论

[v4 Task 17 填实内容，从 _legacy/analysis-framework.md 的 Step 7 全段切出]

## 报告骨架

```markdown
<!-- THESIS_SNAPSHOT_START -->
（由脚本自动注入，agent 不写）
<!-- THESIS_SNAPSHOT_END -->

## peers 主体
...
```

# report · 合成研究报告 · 方法论

> 本模块由 agent 编排，脚本仅完成合并 + manifest（见 `compose_report.py`）。
> agent 责任：补 Step 0 + Step 8 + bear-case + fact-check + 写 HTML。
> 输入：7 个分析模块 `<module>/latest/report.md` 已就绪。

## 编排流程（agent 必须按顺序执行）

1. `python scripts/run_module.py <code> report [--force]` —— 数据层完成
2. 对每个 `data_ready` 模块写 report.md（参考各 modules/*.md）
3. `python scripts/compose_report.py <code>` —— 得到 merged_report_md
4. 在 merged report.md **顶部**追加 Step 0 任务锁定
5. 在 merged report.md **末尾**追加 Step 8 综合结论
6. `python scripts/verify_consistency.py --report <merged>` → 必须 0 FAIL
7. 调 bear-case sub-agent → append 到 report.md
8. 调 fact-check sub-agent → 写 `report/<today>/fact-check.md`
9. `python scripts/render_html.py <code> <ymd>` → `report/<today>/report.html`（agent 不写 HTML）
10. `bash scripts/verify_html.sh report/<today>/report.html` → 全 PASS

## Step 0 任务锁定（agent 在 merged report.md 顶部插入）

```markdown
## Step 0 · 任务锁定

| 字段 | 值 |
|---|---|
| 标的 | {name}（{code}） |
| 周期 | {短线 1-4 周 / 中线 1-2 季 / 双周期} |
| 数据截止日 | {today} |
| 研究状态 | {首次覆盖 / 跟踪更新 / 事件复盘} |
| 风格预判 | {配置型 / 交易型 / 左侧博弈型} |
```

## Step 8 综合结论（agent 在 merged report.md 末尾插入）

```markdown
## Step 8 · 跟踪计划与综合结论

### 8a. 分层跟踪锚点
| 频率 | 跟踪内容 | 数据来源 |
|---|---|---|
| 高频（周度） |  |  |
| 季度 |  |  |
| 事件驱动 |  |  |

### 8b. 执行清单
**短线：**
- 触发条件（买点）：
- 失效条件（风控）：

**中线（3 财务 + 3 事件）：**
- 财务指标：1. 2. 3.
- 事件触发器：1. 2. 3.

### 8c. 综合结论（仅定性，不打分）
- **一句话判断：** 当前更像 ___（趋势/修复/博弈/困境反转）
- **风险等级：** 低/中/高/极高
- **风格标签：** 配置型/交易型/左侧博弈型
- **操作建议：** 核心配置/择时参与/仅观察/暂不参与
```

## Bear-case sub-agent prompt

```
你是空头分析师。基于 report.md 与 risk/latest/anomalies.md，写 300-500 字对立面观点。

【任务】
1. 找出 3 条主 agent 没充分讨论的负面证据
2. 给出"如果多头观点错了，错在哪里"的具体路径
3. 反驳报告中关键的 [I:] 推断
4. 提出 3 条"如果出现 X 信号，则空头观点确认"的可观测指标

【输出】append 到 report.md 末尾的新 section（"## 空头对立面"）
- 必须引用 anomalies.md 中至少 2 条 ID
```

## Fact-check sub-agent prompt

```
你是审稿人。检查 report.md 软问题（硬错由 verify_facts + verify_consistency 已覆盖）。

【输入】report.md、各模块 data.json、risk/latest/anomalies.md

【任务】
1. 抽样 20 个 [F:] / [C:] 标签，看推断依据是否过于宽泛
2. 检查所有 [I:] 推断的依据合理性
3. 找出 anomalies.md 中存在但报告中未充分讨论的异常
4. 找出 bear-case 是否引用了至少 2 条 anomaly ID
5. 找出报告内部矛盾（Step 4 情景假设 vs Step 6 目标价假设的语义一致性）

【明确不再做】（脚本已覆盖）
- 跨节同变量数值是否一致
- 目标价乘法表自洽
- ANO 标题与 invariants 一致
- 派生量与算式自洽

【输出】<output>/report/<ymd>/fact-check.md
- PASS: N / FAIL: M / WARN: K
- 每条 FAIL 必含 location + 问题描述 + 修复指令
```

## HTML 渲染（v5 起由脚本完成）

HTML 不再由 agent 手写。完整的 report.html 由 `scripts/render_html.py` 一次产出：

```bash
python scripts/render_html.py <code_or_name> <ymd>
```

输入：
- `report/<ymd>/report.md` —— merged 后的全报告（含 Step 0 + Step 8 + bear-case append）
- `report/<ymd>/data.json` —— compose 合并后的全模块 data（含各模块 summary 子键）

输出：
- `report/<ymd>/report.html`

设计规范见 [../html-spec.md](../html-spec.md)。

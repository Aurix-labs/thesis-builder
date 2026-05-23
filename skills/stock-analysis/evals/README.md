# stock-analysis · evals

这里是 **skill 自身的行为回归测试**——区别于：
- `scripts/tests/test_render_html.py`（`render_html.py` 的代码级单元测试）
- `examples/比亚迪_002594_input/`（`render_html.py` 的金样本回归数据）

## 何时跑

改动以下任一文件后跑一次：

- `SKILL.md`
- `config.yaml`
- `references/modules/<m>.md`
- `scripts/run_module.py`
- `scripts/compose_report.py`

## 前置条件

1. `output/比亚迪_002594/` 下至少有一次 latest 快照——否则 eval-1 的 reuse 验证退化为 data_ready 验证；assertions 已经同时容忍两种。
2. 本机能跑通 `python skills/stock-analysis/scripts/run_module.py 002594 valuation`（akshare 网络可达、依赖装好）。
3. skill-creator 已经装在 `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`。

## 跑一次回归

设 `SKILL_CREATOR=~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator`。

按 skill-creator 的 SKILL.md "Running and evaluating test cases" 段流程：

```bash
# 1. 在 stock-analysis-workspace/iteration-N/ 下并行 spawn 三个子 agent，
#    每个跑一条 prompt，with-skill 模式产物存到 eval-<id>/with_skill/outputs/
#    （详见 skill-creator SKILL.md 的 Step 1）

# 2. 子 agent 跑完后，grade 每个 run（assertions 已经在 evals.json 里），
#    把 grading.json 写到对应 eval-<id>/with_skill/

# 3. 聚合 + 启动 viewer
python "$SKILL_CREATOR/scripts/aggregate_benchmark.py" \
  stock-analysis-workspace/iteration-N \
  --skill-name stock-analysis

python "$SKILL_CREATOR/eval-viewer/generate_review.py" \
  stock-analysis-workspace/iteration-N \
  --skill-name stock-analysis \
  --benchmark stock-analysis-workspace/iteration-N/benchmark.json
```

浏览器里逐条对比 with_skill 输出 vs 上一轮，标记回归。

## 显式不做

- **不写 baseline runs**（with_skill vs without_skill）：单人本地开发，没必要每次对比"不用 skill"。
- **不写 trigger eval queries**（20 条 query + run_loop.py 机器优化 description）：当前 description 已经主动触发，机器优化边际收益有限。
- **不挂 CI**：每条 eval 真跑会触发 akshare 拉数 + LLM 调用，本地手动跑更合理。

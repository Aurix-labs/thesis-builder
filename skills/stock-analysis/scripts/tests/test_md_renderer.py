"""测试 md_renderer：markdown-it 配置（fence rule + tag inline rule）。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.md_renderer import MdRenderer


def test_basic_paragraph():
    out = MdRenderer().render("hello **world**")
    assert "<p>hello <strong>world</strong></p>" in out


def test_gfm_table():
    md = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    out = MdRenderer().render(md)
    assert "<table>" in out
    assert "<th>a</th>" in out
    assert "<td>1</td>" in out


def test_mermaid_fence_rewritten_to_div():
    md = "```mermaid\nflowchart LR\n  A --> B\n```"
    out = MdRenderer().render(md)
    assert '<div class="mermaid">' in out
    assert "flowchart LR" in out
    assert "A --&gt; B" in out or "A --> B" in out  # mermaid 内容直通
    assert "language-mermaid" not in out


def test_non_mermaid_fence_keeps_code():
    md = "```python\nx = 1\n```"
    out = MdRenderer().render(md)
    assert '<div class="mermaid">' not in out
    assert "<code" in out


def test_tag_inline_F():
    out = MdRenderer().render("营收 100 亿 [F:financials.2024]")
    assert '<span class="tag-f">[F:financials.2024]</span>' in out


def test_tag_inline_T():
    out = MdRenderer().render("目标价 290 [T:base PE 22x]")
    assert '<span class="tag-t">[T:base PE 22x]</span>' in out


def test_tag_inline_GAP():
    out = MdRenderer().render("某指标缺失 [GAP: 财报未披露]")
    assert '<span class="tag-gap">[GAP: 财报未披露]</span>' in out


def test_tag_inline_C():
    out = MdRenderer().render("PE = 86.87/2.31 = [C: 37.6x]")
    assert '<span class="tag-c">[C: 37.6x]</span>' in out


def test_tag_inline_I():
    out = MdRenderer().render("[I:东吴证券 2026-05-06]")
    assert '<span class="tag-i">[I:东吴证券 2026-05-06]</span>' in out


def test_linkify_disabled():
    """不应该把 [T:thesis] 当链接处理。"""
    out = MdRenderer().render("see http://example.com")
    # http://example.com 不应自动 linkify
    assert '<a href="http://example.com"' not in out


def test_raw_html_pass_through():
    """LLM 在 markdown 里嵌 raw <svg> / <div> 块时直通。"""
    md = '<svg width="10"><rect/></svg>\n\nnormal text'
    out = MdRenderer().render(md)
    assert "<svg" in out
    assert "<rect" in out


from lib.md_renderer import split_report_sections
from lib.render_schema import RenderError
import pytest


_SAMPLE_MD = """<!-- THESIS_SNAPSHOT_START -->
速写
<!-- THESIS_SNAPSHOT_END -->

## Step 0 · 任务锁定

mission body.

## Step 0.5 · 核心异常分析

anomalies body.

## Step 1 · 宏观与周期定位

macro body.

## Step 2 · 产业链

### 2a. 题材来源

ta.

### 2b. 产业链图

```mermaid
flowchart LR
  A --> B
```

### 2c. 业务线

tc.

## Step 3 · 公司质地评分

### 3a. 正面筛选

3a body.

### 3b. 不碰清单

3b body.

### 3c. Rubric 评分

3c skipped.

### 3d. 治理

3d body.

## Step 4 · 业绩弹性测算

### 4a. 弹性树

skipped.

### 4b. 价格敏感度

4b body.

### 4c. 情景分析

4c body.

## Step 5 · 风险分析

risk body.

## Step 6 · 估值

### 6a. 估值方法

6a body.

### 6a+. 资金面

6a+ body.

### 6a++. 技术面

6a++ body.

### 6b. 期货

6b body.

### 6c. 研报对比

6c body.

### 6d. 三档目标价

skipped.

### 6e. 盈亏比

6e body.

### 6f. 框架原则

6f body.

## Step 7 · 对标分析

compare body.

## Step 8 · 跟踪计划

tracking body.
"""


def test_split_returns_all_required_keys():
    out = split_report_sections(_SAMPLE_MD)
    required = {
        "step_0", "step_0_5", "step_1", "step_2",
        "step_3_pre", "step_3_post",
        "step_4_post",
        "step_5",
        "step_6_pre", "step_6_post",
        "step_7", "step_8",
    }
    assert required.issubset(set(out.keys()))


def test_split_step_3_pre_contains_3a_3b_not_3c():
    out = split_report_sections(_SAMPLE_MD)
    assert "3a body" in out["step_3_pre"]
    assert "3b body" in out["step_3_pre"]
    assert "3c skipped" not in out["step_3_pre"]
    assert "3c skipped" not in out["step_3_post"]


def test_split_step_3_post_contains_only_3d():
    out = split_report_sections(_SAMPLE_MD)
    assert "3d body" in out["step_3_post"]
    assert "3a body" not in out["step_3_post"]


def test_split_step_4_post_contains_4b_4c_not_4a():
    out = split_report_sections(_SAMPLE_MD)
    assert "4b body" in out["step_4_post"]
    assert "4c body" in out["step_4_post"]
    assert "skipped" not in out["step_4_post"]


def test_split_step_6_pre_contains_6a_subs_not_6d():
    out = split_report_sections(_SAMPLE_MD)
    assert "6a body" in out["step_6_pre"]
    assert "6a+ body" in out["step_6_pre"]
    assert "6a++ body" in out["step_6_pre"]
    assert "6d" not in out["step_6_pre"]


def test_split_step_6_post_contains_6e_onward_not_6d():
    out = split_report_sections(_SAMPLE_MD)
    assert "6b body" in out["step_6_post"]
    assert "6c body" in out["step_6_post"]
    assert "6e body" in out["step_6_post"]
    assert "6f body" in out["step_6_post"]
    assert "skipped" not in out["step_6_post"]


def test_split_step_2_keeps_mermaid_block():
    out = split_report_sections(_SAMPLE_MD)
    assert "```mermaid" in out["step_2"]
    assert "flowchart LR" in out["step_2"]


def test_split_missing_step_5_raises():
    md = _SAMPLE_MD.replace("## Step 5 · 风险分析\n\nrisk body.\n\n", "")
    with pytest.raises(RenderError, match="Step 5"):
        split_report_sections(md)


def test_split_missing_step_3_subheading_4b_raises():
    md = _SAMPLE_MD.replace("### 4b. 价格敏感度\n\n4b body.\n\n", "")
    with pytest.raises(RenderError, match="Step 4.*4b"):
        split_report_sections(md)

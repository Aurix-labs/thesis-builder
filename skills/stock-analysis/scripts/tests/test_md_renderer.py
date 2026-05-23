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

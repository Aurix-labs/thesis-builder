"""markdown-it-py 配置 + 自定义 fence rule + tag inline rule。

供 render_html.py 把 merged report.md 的章节正文转 HTML。
"""
from __future__ import annotations

import re

from markdown_it import MarkdownIt
from markdown_it.token import Token


# 标签风格映射：[F:...] / [T:...] / [I:...] / [C:...] / [GAP:...]
_TAG_RE = re.compile(r"\[(F|T|I|C|GAP)(:[^\]]*)\]")


def _tag_inline_plugin(md: MarkdownIt) -> None:
    """注册 core ruler，识别 [F:...] / [T:...] / [I:...] / [C:...] / [GAP:...]
    并把对应 text token 拆成 [text, html_inline, text, ...]，输出 <span class="tag-X">[...]</span>。
    """

    def _replace_tags(state):
        for block_token in state.tokens:
            if block_token.type != "inline" or not block_token.children:
                continue
            new_children = []
            for tok in block_token.children:
                if tok.type != "text" or not _TAG_RE.search(tok.content):
                    new_children.append(tok)
                    continue
                content = tok.content
                pos = 0
                for m in _TAG_RE.finditer(content):
                    if m.start() > pos:
                        leading = Token("text", "", 0)
                        leading.content = content[pos:m.start()]
                        new_children.append(leading)
                    h = Token("html_inline", "", 0)
                    kind = m.group(1).lower()
                    h.content = f'<span class="tag-{kind}">{m.group(0)}</span>'
                    new_children.append(h)
                    pos = m.end()
                if pos < len(content):
                    trailing = Token("text", "", 0)
                    trailing.content = content[pos:]
                    new_children.append(trailing)
            block_token.children = new_children

    md.core.ruler.push("tag_inline_rewrite", _replace_tags)


class MdRenderer:
    """统一的 markdown → HTML 渲染器。

    特性：
    - CommonMark + GFM tables + strikethrough
    - 不启用 linkify（保留 [T:xxx] 等标签不被当链接）
    - ```mermaid 块改写为 <div class="mermaid">
    - 行内 [F/T/I/C/GAP:...] 标签包 <span class="tag-X">
    - 允许 HTML pass-through（LLM 可嵌入 raw <svg> 等）
    """

    def __init__(self) -> None:
        md = MarkdownIt("commonmark", {"html": True, "linkify": False, "typographer": False})
        md.enable("table")
        md.enable("strikethrough")

        default_fence = md.renderer.rules.get("fence")

        def fence(tokens, idx, options, env):
            token = tokens[idx]
            info = (token.info or "").strip().lower()
            if info == "mermaid":
                return f'<div class="mermaid">\n{token.content}</div>\n'
            if default_fence:
                return default_fence(tokens, idx, options, env)
            # Fallback (shouldn't hit, default exists)
            return f"<pre><code>{token.content}</code></pre>\n"

        md.renderer.rules["fence"] = fence
        _tag_inline_plugin(md)
        self._md = md

    def render(self, md_text: str) -> str:
        return self._md.render(md_text)

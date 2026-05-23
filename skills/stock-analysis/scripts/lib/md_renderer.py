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


from .render_schema import RenderError

# Step 一级匹配：## Step <N>[.<sub>] · <标题>
_STEP_RE = re.compile(r"^## Step (\d+(?:\.\d+)?) · ", re.MULTILINE)
# 二级子标题：### <数字><字母>(+*)? . <标题>，捕获子标识如 3a / 6a+ / 6a++
_SUBSTEP_RE = re.compile(r"^### (\d+[a-z]\+*)\. ", re.MULTILINE)

# 各 Step 在 HTML 中的归属（决定 step_X 的 key 名）
_STEP_KEY = {
    "0": "step_0",
    "0.5": "step_0_5",
    "1": "step_1",
    "2": "step_2",
    "3": "step_3",  # 进一步拆 pre/post
    "4": "step_4",  # 拆为 post（4a 入树）
    "5": "step_5",
    "6": "step_6",  # 拆 pre/post（6d 入 targets）
    "7": "step_7",
    "8": "step_8",
}

# 必须出现的 Step 一级编号
_REQUIRED_STEPS = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]

# Step 3 拆分：pre 包含 3a,3b；跳过 3c；post 包含 3d
_STEP_3_PRE_SUBS = ["3a", "3b"]
_STEP_3_POST_SUBS = ["3d"]
_STEP_3_SKIP_SUBS = ["3c"]

# Step 4：4a 入弹性树 partial（跳过散文渲染），post 包含 4b,4c
_STEP_4_REQUIRED_SUBS = ["4b", "4c"]
_STEP_4_SKIP_SUBS = ["4a"]

# Step 6：pre = 6a/6a+/6a++（每只票都要有 6a；6a+/6a++ 可缺）
#         post = 6b ~ 6i，跳过 6d
_STEP_6_PRE_SUBS = ["6a", "6a+", "6a++"]
_STEP_6_PRE_REQUIRED = ["6a"]
_STEP_6_SKIP_SUBS = ["6d"]


def _slice_by_steps(md_text: str) -> dict[str, str]:
    """切顶层 Step 段。返回 {step_number_str: body_md}。"""
    matches = list(_STEP_RE.finditer(md_text))
    result: dict[str, str] = {}
    for i, m in enumerate(matches):
        num = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        nl = md_text.find("\n", body_start)
        if nl == -1:
            body = ""
        else:
            body = md_text[nl + 1 : body_end]
        result[num] = body.strip("\n")
    return result


def _slice_substeps(step_body: str) -> dict[str, str]:
    """切某一 Step 段内的 ### Na. ### Nb. 子段。返回 {sub_id: body_md}。"""
    matches = list(_SUBSTEP_RE.finditer(step_body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        sub = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(step_body)
        nl = step_body.find("\n", start)
        if nl == -1:
            body = ""
        else:
            body = step_body[nl + 1 : end]
        out[sub] = body.strip("\n")
    return out


def _retrieve_subhead_line(step_body: str, sub_id: str) -> str:
    """从 step_body 中找 ### <sub_id>. 行尾的标题文字（不含 '### Nx. ' 前缀）。"""
    pat = re.compile(r"^### " + re.escape(sub_id) + r"\. ([^\n]*)\n", re.MULTILINE)
    m = pat.search(step_body)
    if m is None:
        return f"{sub_id}\n"
    return m.group(1).rstrip() + "\n\n"


def split_report_sections(md_text: str) -> dict[str, str]:
    """切 merged report.md 为按 HTML 卡命名的 markdown 片段。

    返回 dict 含至少：
        step_0, step_0_5, step_1, step_2,
        step_3_pre (3a+3b), step_3_post (3d),
        step_4_post (4b+4c),
        step_5,
        step_6_pre (6a+6a+/6a++), step_6_post (6b/6c/6e/6f/...),
        step_7, step_8

    Step 3/4/6 的混合卡跳过被 partial 渲染替代的子段（3c/4a/6d）。
    缺必填段抛 RenderError。
    """
    steps = _slice_by_steps(md_text)
    missing = [n for n in _REQUIRED_STEPS if n not in steps]
    if missing:
        raise RenderError(f"report.md 缺 ## Step {missing[0]} 章节")

    out: dict[str, str] = {}
    out["step_0"] = steps.get("0", "")
    out["step_0_5"] = steps.get("0.5", "")
    out["step_1"] = steps["1"]
    out["step_2"] = steps["2"]
    out["step_5"] = steps["5"]
    out["step_7"] = steps["7"]
    out["step_8"] = steps["8"]

    # Step 3 拆 pre/post
    subs3 = _slice_substeps(steps["3"])
    out["step_3_pre"] = "\n\n".join(
        f"### {s}. " + _retrieve_subhead_line(steps['3'], s) + subs3[s]
        for s in _STEP_3_PRE_SUBS if s in subs3
    )
    out["step_3_post"] = "\n\n".join(
        f"### {s}. " + _retrieve_subhead_line(steps['3'], s) + subs3[s]
        for s in _STEP_3_POST_SUBS if s in subs3
    )

    # Step 4 post
    subs4 = _slice_substeps(steps["4"])
    missing_4 = [s for s in _STEP_4_REQUIRED_SUBS if s not in subs4]
    if missing_4:
        raise RenderError(f"report.md Step 4 缺 ### {missing_4[0]} 子标题")
    out["step_4_post"] = "\n\n".join(
        f"### {s}. " + _retrieve_subhead_line(steps['4'], s) + subs4[s]
        for s in _STEP_4_REQUIRED_SUBS if s in subs4
    )

    # Step 6 pre/post
    subs6 = _slice_substeps(steps["6"])
    missing_6 = [s for s in _STEP_6_PRE_REQUIRED if s not in subs6]
    if missing_6:
        raise RenderError(f"report.md Step 6 缺 ### {missing_6[0]} 子标题")
    out["step_6_pre"] = "\n\n".join(
        f"### {s}. " + _retrieve_subhead_line(steps['6'], s) + subs6[s]
        for s in _STEP_6_PRE_SUBS if s in subs6
    )
    out["step_6_post"] = "\n\n".join(
        f"### {s}. " + _retrieve_subhead_line(steps['6'], s) + subs6[s]
        for s in subs6
        if s not in _STEP_6_PRE_SUBS and s not in _STEP_6_SKIP_SUBS
    )
    return out

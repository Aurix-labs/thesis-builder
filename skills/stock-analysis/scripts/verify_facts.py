"""verify_facts.py · Phase 2 数字标签反查脚本。

输入：report.md + data.json + anomalies.json
输出：PASS/FAIL/WARN 列表；退出码 0 / 1 / 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TAG_RE = re.compile(r'\[(F|C|I|T|GAP):([^\]]+)\]')


@dataclass
class Tag:
    kind: str        # 'F' / 'C' / 'I' / 'T' / 'GAP'
    payload: str     # path / formula / reason / assumption / field
    line_no: int
    line: str        # 整行内容（用于反查上下文）
    col: int         # 标签在行中起始列


def extract_tags(text: str) -> list[Tag]:
    """parse MD 文本，返回所有标签。"""
    out = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in TAG_RE.finditer(line):
            out.append(Tag(
                kind=m.group(1),
                payload=m.group(2).strip(),
                line_no=line_no,
                line=line,
                col=m.start(),
            ))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--anomalies", required=False, default=None)
    p.add_argument("--mode", choices=["partial", "full"], default="full")
    args = p.parse_args()

    md_text = Path(args.report).read_text()
    tags = extract_tags(md_text)
    print(f"[INFO] parsed {len(tags)} tags from {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

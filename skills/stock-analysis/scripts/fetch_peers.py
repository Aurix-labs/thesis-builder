"""M7 peers · 同业对标 数据采集。

字段：self（本公司）+ peers（同业列表）
覆盖 Step 7 对标分析
"""
from __future__ import annotations

from pathlib import Path

from lib.akshare_cache import cached_call
from lib.module_io import write_module_data
from lib.peer_finder import find_peers
from fetch_chain import _extract_meta, _extract_quote


MODULE_NAME = "peers"
FIELDS = ["self", "peers"]


def _fetch_basic(code: str, stock_dir: Path, today: str, akshare_module) -> dict:
    info = cached_call(stock_dir, today, "stock_individual_info_em",
                       akshare_module.stock_individual_info_em, symbol=code)
    spot = cached_call(stock_dir, today, "stock_zh_a_spot_em",
                       akshare_module.stock_zh_a_spot_em)
    fa = cached_call(stock_dir, today, "stock_financial_abstract",
                     akshare_module.stock_financial_abstract, symbol=code)
    meta = _extract_meta(info, code)
    return {
        "code": code,
        "meta": meta,
        "quote": _extract_quote(spot, code),
        "financial_abstract": fa,
    }


def fetch(
    code: str,
    name: str,
    stock_dir: Path,
    today: str,
    *,
    akshare_module=None,
    peers_count: int = 5,
) -> dict:
    if akshare_module is None:
        import akshare as akshare_module

    # 先看 <today>/peers.txt 是否已存在（同日重跑），其次看 latest 的 peers.txt（保持可比性）
    today_peers_txt = stock_dir / MODULE_NAME / today / "peers.txt"
    peer_codes: list[str] = []
    if today_peers_txt.exists():
        peer_codes = [line.strip() for line in today_peers_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        self_basic = _fetch_basic(code, stock_dir, today, akshare_module)
        if name and "name" not in self_basic["meta"]:
            self_basic["meta"]["name"] = name
        industry = self_basic["meta"].get("industry") or ""
        peer_codes = find_peers(code, industry, count=peers_count, akshare_module=akshare_module)

    self_data = _fetch_basic(code, stock_dir, today, akshare_module)
    if name and "name" not in self_data["meta"]:
        self_data["meta"]["name"] = name

    peers_data = [_fetch_basic(pc, stock_dir, today, akshare_module) for pc in peer_codes]

    data = {
        "module": MODULE_NAME,
        "ymd": today,
        "self": self_data,
        "peers": peers_data,
    }
    ymd_dir = write_module_data(stock_dir, MODULE_NAME, today, data)

    # 写/复写 peers.txt
    (ymd_dir / "peers.txt").write_text("\n".join(peer_codes) + "\n", encoding="utf-8")

    return data

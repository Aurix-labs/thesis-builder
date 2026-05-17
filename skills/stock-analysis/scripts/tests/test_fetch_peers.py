"""测试 fetch_peers：含同业选股、peers.txt 持久化、复用机制。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_peers import fetch, MODULE_NAME


class FakeAk:
    def stock_individual_info_em(self, symbol):
        return [{"item": "股票简称", "value": "比亚迪" if symbol == "002594" else f"S{symbol}"},
                {"item": "行业", "value": "汽车整车"}]
    def stock_zh_a_spot_em(self):
        return [{"代码": "002594", "最新价": 280.5, "总市值": 7.8e11, "市盈率-动态": 32.4, "市净率": 4.8},
                {"代码": "601633", "最新价": 25.6, "总市值": 2.2e11, "市盈率-动态": 15.0, "市净率": 2.0}]
    def stock_financial_abstract(self, symbol):
        return [{"指标": "营业收入", "20250331": 1500 if symbol == "002594" else 800}]
    def stock_board_industry_cons_em(self, symbol):
        return [
            {"代码": "002594", "名称": "比亚迪", "总市值": 7.8e11},
            {"代码": "601633", "名称": "长城汽车", "总市值": 2.2e11},
        ]


def test_module_name():
    assert MODULE_NAME == "peers"


def test_fetch_writes_peers_txt(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk(), peers_count=5)
    out_dir = tmp_path / "peers" / "2026-05-17"
    assert (out_dir / "peers.txt").exists()
    assert "601633" in (out_dir / "peers.txt").read_text(encoding="utf-8")


def test_fetch_data_includes_peer_financials(tmp_path):
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk(), peers_count=5)
    assert "self" in data
    assert "peers" in data
    assert any(p["code"] == "601633" for p in data["peers"])


def test_fetch_reuses_peers_txt_on_second_call(tmp_path):
    """先用 peers_count=1 写 peers.txt，再调用应复用而不重新选股。"""
    fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk(), peers_count=5)
    txt_path = tmp_path / "peers" / "2026-05-17" / "peers.txt"
    txt_path.write_text("999999\n", encoding="utf-8")  # 人工改成不存在的代码

    # 第二次调用应该读 999999，而不是重新选 601633
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk(), peers_count=5)
    codes = [p["code"] for p in data["peers"]]
    assert "999999" in codes


def test_fetch_peers_reuses_latest_peers_txt_on_new_day(tmp_path):
    """R9: 新一天 --force 时应复用 latest/peers.txt，不重新选股。"""
    # 第一天：常规创建
    fetch("002594", "比亚迪", tmp_path, "2026-04-30", akshare_module=FakeAk(), peers_count=5)
    # 人工改 latest 的 peers.txt 为一个特殊代码
    (tmp_path / "peers" / "2026-04-30" / "peers.txt").write_text("888888\n", encoding="utf-8")

    # 第二天 (今天)：应该复用 latest 而不是 find_peers 重选
    data = fetch("002594", "比亚迪", tmp_path, "2026-05-17", akshare_module=FakeAk(), peers_count=5)
    codes = [p["code"] for p in data["peers"]]
    assert "888888" in codes  # 来自 latest/peers.txt 而非 find_peers
    # 新 ymd 目录的 peers.txt 应该写入同样的列表（持久化复用结果）
    new_txt = (tmp_path / "peers" / "2026-05-17" / "peers.txt").read_text(encoding="utf-8")
    assert "888888" in new_txt

"""测试同业自动选股。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.peer_finder import find_peers


class FakeAk:
    def stock_board_industry_cons_em(self, symbol):
        # 模拟"汽车整车"板块成分
        return [
            {"代码": "002594", "名称": "比亚迪", "最新价": 280.5, "总市值": 7.8e11},
            {"代码": "601238", "名称": "广汽集团", "最新价": 8.5, "总市值": 0.9e11},
            {"代码": "600104", "名称": "上汽集团", "最新价": 14.2, "总市值": 1.6e11},
            {"代码": "000625", "名称": "长安汽车", "最新价": 13.5, "总市值": 1.3e11},
            {"代码": "601633", "名称": "长城汽车", "最新价": 25.6, "总市值": 2.2e11},
            {"代码": "601127", "名称": "赛力斯", "最新价": 90.0, "总市值": 1.3e11},
            {"代码": "300750", "名称": "ST示例", "最新价": 1.0, "总市值": 0.05e11},
        ]


def test_find_peers_excludes_self(tmp_path):
    peers = find_peers("002594", "汽车整车", count=5, akshare_module=FakeAk())
    assert "002594" not in peers


def test_find_peers_returns_count(tmp_path):
    peers = find_peers("002594", "汽车整车", count=3, akshare_module=FakeAk())
    assert len(peers) == 3


def test_find_peers_orders_by_market_cap_proximity(tmp_path):
    """本票市值 7800 亿，最接近的应是长城（2200）、上汽（1600）等。"""
    peers = find_peers("002594", "汽车整车", count=5, akshare_module=FakeAk())
    # 排除 ST 后剩 5 家（去掉自己）。剩下：广汽 900 / 上汽 1600 / 长安 1300 / 长城 2200 / 赛力斯 1300
    # 按与 7800 的市值接近度排序：长城（5600）< 上汽（6200）< 长安/赛力斯（6500）< 广汽（6900）
    assert peers[0] == "601633"  # 长城最接近


def test_find_peers_excludes_st_names():
    peers = find_peers("002594", "汽车整车", count=10, akshare_module=FakeAk())
    assert "300750" not in peers  # ST示例

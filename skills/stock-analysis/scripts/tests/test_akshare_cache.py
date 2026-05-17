"""测试 akshare 当日缓存（mock akshare 调用，不触网络）。"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.akshare_cache import cached_call, _make_cache_key


def test_make_cache_key_stable():
    k1 = _make_cache_key("stock_zh_a_hist", ("002594",), {"period": "daily"})
    k2 = _make_cache_key("stock_zh_a_hist", ("002594",), {"period": "daily"})
    assert k1 == k2


def test_make_cache_key_different_args_different_keys():
    k1 = _make_cache_key("stock_zh_a_hist", ("002594",), {})
    k2 = _make_cache_key("stock_zh_a_hist", ("600519",), {})
    assert k1 != k2


def test_cached_call_writes_cache_on_miss(tmp_path):
    calls = []
    def fake_fn(symbol):
        calls.append(symbol)
        return [{"date": "2026-05-17", "close": 280.5}]

    out = cached_call(tmp_path, "2026-05-17", "fake_fn", fake_fn, "002594")
    assert out == [{"date": "2026-05-17", "close": 280.5}]
    assert calls == ["002594"]
    cache_dir = tmp_path / ".cache" / "2026-05-17"
    assert cache_dir.exists()
    cache_files = list(cache_dir.glob("fake_fn_*.json"))
    assert len(cache_files) == 1


def test_cached_call_reads_cache_on_hit(tmp_path):
    calls = []
    def fake_fn(symbol):
        calls.append(symbol)
        return [{"v": 1}]

    cached_call(tmp_path, "2026-05-17", "fake_fn", fake_fn, "002594")
    cached_call(tmp_path, "2026-05-17", "fake_fn", fake_fn, "002594")
    assert calls == ["002594"]  # 第二次命中缓存，不再调用


def test_cached_call_different_ymd_different_cache(tmp_path):
    calls = []
    def fake_fn(symbol):
        calls.append(symbol)
        return [{"v": symbol}]

    cached_call(tmp_path, "2026-05-17", "fake_fn", fake_fn, "002594")
    cached_call(tmp_path, "2026-05-18", "fake_fn", fake_fn, "002594")
    assert calls == ["002594", "002594"]  # 不同 ymd 不共享缓存


def test_cached_call_normalizes_dataframe(tmp_path):
    """如果 fake_fn 返回 DataFrame-like，cached_call 应转为 records 再缓存。"""
    try:
        import pandas as pd
    except ImportError:
        return  # pandas 不可用就跳过

    df = pd.DataFrame([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    def fake_fn():
        return df

    out = cached_call(tmp_path, "2026-05-17", "fake_fn", fake_fn)
    assert out == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

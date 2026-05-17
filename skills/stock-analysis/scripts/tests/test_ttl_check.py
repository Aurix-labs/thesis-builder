"""测试 TTL 命中判定。"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.module_io import update_latest_symlink
from lib.ttl_check import is_within_ttl, days_between


def test_days_between_basic():
    assert days_between("2026-05-17", "2026-05-17") == 0
    assert days_between("2026-05-10", "2026-05-17") == 7
    assert days_between("2026-04-30", "2026-05-17") == 17


def test_is_within_ttl_no_latest_returns_false(tmp_path):
    within, ymd = is_within_ttl(tmp_path, "chain", "2026-05-17", ttl_days=90)
    assert within is False
    assert ymd is None


def test_is_within_ttl_hit(tmp_path):
    (tmp_path / "chain" / "2026-05-10").mkdir(parents=True)
    update_latest_symlink(tmp_path / "chain", "2026-05-10")
    within, ymd = is_within_ttl(tmp_path, "chain", "2026-05-17", ttl_days=90)
    assert within is True
    assert ymd == "2026-05-10"


def test_is_within_ttl_boundary_inclusive(tmp_path):
    (tmp_path / "valuation" / "2026-05-10").mkdir(parents=True)
    update_latest_symlink(tmp_path / "valuation", "2026-05-10")
    within, ymd = is_within_ttl(tmp_path, "valuation", "2026-05-17", ttl_days=7)
    assert within is True


def test_is_within_ttl_expired(tmp_path):
    (tmp_path / "valuation" / "2026-05-09").mkdir(parents=True)
    update_latest_symlink(tmp_path / "valuation", "2026-05-09")
    within, ymd = is_within_ttl(tmp_path, "valuation", "2026-05-17", ttl_days=7)
    assert within is False
    assert ymd == "2026-05-09"


def test_is_within_ttl_zero_day(tmp_path):
    """flow-tech 的 TTL=1 时，同一天命中、昨天过期。"""
    (tmp_path / "flow-tech" / "2026-05-17").mkdir(parents=True)
    update_latest_symlink(tmp_path / "flow-tech", "2026-05-17")
    within, _ = is_within_ttl(tmp_path, "flow-tech", "2026-05-17", ttl_days=1)
    assert within is True

    (tmp_path / "flow-tech-old" / "2026-05-15").mkdir(parents=True)
    update_latest_symlink(tmp_path / "flow-tech-old", "2026-05-15")
    within, _ = is_within_ttl(tmp_path, "flow-tech-old", "2026-05-17", ttl_days=1)
    assert within is False

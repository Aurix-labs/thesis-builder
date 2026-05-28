from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.normalize import to_float, pct_change, bucket_time


def test_to_float_handles_commas_percent_and_dash():
    assert to_float("1,234.5") == 1234.5
    assert to_float("3.2%") == 3.2
    assert to_float("-") is None
    assert to_float(None) is None


def test_pct_change_returns_percent():
    assert round(pct_change(11, 10), 2) == 10.0
    assert pct_change(11, 0) is None
    assert pct_change(11, None) is None


def test_bucket_time_groups_by_window_minutes():
    assert bucket_time("09:30:00", 10) == "09:30-09:40"
    assert bucket_time("09:31:20", 10) == "09:30-09:40"
    assert bucket_time("14:56:03", 10) == "14:50-15:00"
    assert bucket_time("15:00:00", 10) == "14:50-15:00"

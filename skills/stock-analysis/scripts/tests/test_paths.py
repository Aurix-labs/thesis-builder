"""测试路径计算与 CLI 解析（不触网络）。"""
import os
import datetime as dt
from pathlib import Path

import pytest

import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from fetch_data import (
    detect_market,
    build_output_dir,
    resolve_default_output_root,
    parse_args,
)


class TestDetectMarket:
    def test_sh_main_board(self):
        assert detect_market("600519") == ("sh600519", "sh")
        assert detect_market("601398") == ("sh601398", "sh")
        assert detect_market("603259") == ("sh603259", "sh")

    def test_sh_star(self):
        assert detect_market("688981") == ("sh688981", "sh")

    def test_sz_main(self):
        assert detect_market("000066") == ("sz000066", "sz")
        assert detect_market("002594") == ("sz002594", "sz")

    def test_sz_chinext(self):
        assert detect_market("300750") == ("sz300750", "sz")
        assert detect_market("301308") == ("sz301308", "sz")

    def test_bj(self):
        assert detect_market("430047") == ("bj430047", "bj")

    def test_invalid(self):
        with pytest.raises(ValueError):
            detect_market("12345")
        with pytest.raises(ValueError):
            detect_market("abcdef")


class TestBuildOutputDir:
    def test_directory_template(self, tmp_path):
        out = build_output_dir(tmp_path, name="比亚迪", code="002594", date="2026-05-15")
        assert out == tmp_path / "比亚迪_002594" / "2026-05-15"

    def test_creates_dir(self, tmp_path):
        out = build_output_dir(tmp_path, name="比亚迪", code="002594", date="2026-05-15", create=True)
        assert out.exists()
        assert out.is_dir()

    def test_updates_latest_symlink(self, tmp_path):
        out = build_output_dir(tmp_path, name="比亚迪", code="002594", date="2026-05-15", create=True)
        latest = tmp_path / "比亚迪_002594" / "latest"
        assert latest.is_symlink()
        assert latest.resolve() == out.resolve()

    def test_overwrites_latest_on_new_date(self, tmp_path):
        build_output_dir(tmp_path, name="比亚迪", code="002594", date="2026-05-10", create=True)
        build_output_dir(tmp_path, name="比亚迪", code="002594", date="2026-05-15", create=True)
        latest = tmp_path / "比亚迪_002594" / "latest"
        assert latest.resolve().name == "2026-05-15"


class TestResolveDefaultOutputRoot:
    def test_resolves_relative_to_cwd_not_script(self):
        # 默认在 cwd/output 而不是 script 同级 output（用户在 thesis-builder/ 跑也对）
        from fetch_data import resolve_default_output_root
        result = resolve_default_output_root()
        assert result == Path.cwd() / "output"


class TestParseArgs:
    def test_minimal(self):
        ns = parse_args(["002594"])
        assert ns.code == "002594"
        assert ns.date is None
        assert ns.output_dir is None
        assert ns.max_kline_years == 3

    def test_with_date(self):
        ns = parse_args(["002594", "--date", "2026-04-22"])
        assert ns.date == "2026-04-22"

    def test_with_output_dir(self, tmp_path):
        ns = parse_args(["002594", "--output-dir", str(tmp_path)])
        assert ns.output_dir == str(tmp_path)

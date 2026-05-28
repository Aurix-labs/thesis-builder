from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.status import ERROR, OK, UNAVAILABLE, layer_result
from run_review import LAYERS, build_artifacts, main, parse_args


def test_parse_args_force():
    args = parse_args(["002594", "--force"])
    assert args.code_or_name == "002594"
    assert args.force is True


def test_build_artifacts_sets_required_statuses():
    layers = {
        "market_context": layer_result(OK, {"indices": []}, []),
        "sector_context": layer_result(UNAVAILABLE, {}, ["missing"]),
        "stock_trade": layer_result(
            OK,
            {"trade_date": "2026-05-28", "daily": {}, "intraday_pattern": "震荡上行"},
            [],
        ),
        "tick_trade": layer_result(OK, {"summary": {}}, []),
        "funds_context": layer_result(OK, {}, []),
        "event_context": layer_result(UNAVAILABLE, {}, []),
        "sentiment_context": layer_result(UNAVAILABLE, {}, []),
    }

    data, manifest = build_artifacts("002594", "比亚迪", "2026-05-28", False, layers)

    assert data["data_status"]["stock_trade"] == OK
    assert data["tick_trade"] == {"summary": {}}
    assert manifest["trade_date"] == "2026-05-28"
    assert manifest["force"] is False


def test_build_artifacts_includes_all_layers_with_error_fallback():
    data, manifest = build_artifacts(
        "002594",
        "比亚迪",
        "2026-05-28",
        True,
        {"stock_trade": layer_result(OK, {"trade_date": "2026-05-28"}, [])},
    )

    assert list(data["data_status"]) == LAYERS
    assert data["data_status"]["stock_trade"] == OK
    assert data["data_status"]["tick_trade"] == ERROR
    assert data["tick_trade"] == {}
    assert {"layer": "tick_trade", "message": "tick_trade did not run"} in manifest["errors"]


def test_main_reuses_existing_report(tmp_path, capsys):
    stock_dir = tmp_path / "比亚迪_002594" / "after-market-review" / "2026-05-28"
    stock_dir.mkdir(parents=True)
    report = stock_dir / "report.md"
    report.write_text("# cached\n", encoding="utf-8")

    code = main(["002594", "--today", "2026-05-28", "--output-dir", str(tmp_path)])

    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "reuse"
    assert out["report_md"].endswith("report.md")


class FakeFetcher:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def fetch(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def _fake_fetchers(stock_trade_status=OK):
    return {
        "stock_trade": FakeFetcher(
            layer_result(
                stock_trade_status,
                {"trade_date": "2026-05-28", "daily": {}, "intraday_pattern": "震荡上行"}
                if stock_trade_status != ERROR
                else {},
                ["stock outage"] if stock_trade_status == ERROR else [],
            )
        ),
        "market": FakeFetcher(layer_result(OK, {"indices": []}, [])),
        "sector": FakeFetcher(layer_result(UNAVAILABLE, {}, [])),
        "tick_trade": FakeFetcher(layer_result(UNAVAILABLE, {"summary": {}}, [])),
        "funds": FakeFetcher(layer_result(OK, {"fund_flow": []}, [])),
        "events": FakeFetcher(layer_result(UNAVAILABLE, {"raw_news": []}, [])),
        "sentiment": FakeFetcher(layer_result(UNAVAILABLE, {"hot_rank": []}, [])),
    }


def test_stock_trade_error_writes_artifacts_and_exits_1(tmp_path, capsys, monkeypatch):
    import run_review

    fetchers = _fake_fetchers(stock_trade_status=ERROR)
    monkeypatch.setattr(run_review, "_import_fetchers", lambda: fetchers)
    monkeypatch.setattr(run_review, "resolve_stock", lambda q, output_root: ("002594", "比亚迪", tmp_path / "比亚迪_002594"))

    code = main(["002594", "--today", "2026-05-28", "--output-dir", str(tmp_path)])

    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert out["error"] == "stock_trade failed"
    data_json = tmp_path / "比亚迪_002594" / "after-market-review" / "2026-05-28" / "data.json"
    manifest_json = tmp_path / "比亚迪_002594" / "after-market-review" / "2026-05-28" / "manifest.json"
    assert data_json.exists()
    assert manifest_json.exists()
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert {"layer": "stock_trade", "message": "stock outage"} in manifest["errors"]


def test_data_ready_writes_artifacts_and_prints_paths(tmp_path, capsys, monkeypatch):
    import run_review

    fetchers = _fake_fetchers()
    monkeypatch.setattr(run_review, "_import_fetchers", lambda: fetchers)
    monkeypatch.setattr(run_review, "resolve_stock", lambda q, output_root: ("002594", "比亚迪", tmp_path / "比亚迪_002594"))

    code = main(["002594", "--today", "2026-05-28", "--output-dir", str(tmp_path)])

    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "data_ready"
    assert out["report_md"].endswith("report.md")
    assert Path(out["data_json"]).exists()
    assert Path(out["manifest_json"]).exists()
    data = json.loads(Path(out["data_json"]).read_text(encoding="utf-8"))
    assert data["data_status"]["stock_trade"] == OK
    assert data["trade_date"] == "2026-05-28"
    assert fetchers["tick_trade"].calls[0][1] == {}

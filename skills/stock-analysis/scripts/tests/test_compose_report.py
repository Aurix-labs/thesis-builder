"""测试 compose_report：合并 + 标的速写去重 + manifest 生成。"""
from pathlib import Path
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from compose_report import compose, dedupe_thesis_snapshots, merge_data_json
from lib.module_io import THESIS_SNAPSHOT_START, THESIS_SNAPSHOT_END, update_latest_symlink, write_module_data
from lib.config_loader import ANALYSIS_MODULES


def _write_module_report(tmp_path: Path, module: str, ymd: str, body: str):
    d = tmp_path / module / ymd
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.md").write_text(body, encoding="utf-8")
    # 同时写一份最小 data.json，便于 compose() 调用 merge_data_json
    (d / "data.json").write_text(
        json.dumps({"module": module, "ymd": ymd, "meta": {}}, ensure_ascii=False),
        encoding="utf-8",
    )
    update_latest_symlink(tmp_path / module, ymd)


def _make_snapshot(name: str) -> str:
    return f"{THESIS_SNAPSHOT_START}\n## {name} 标的速写\n{THESIS_SNAPSHOT_END}\n"


def test_dedupe_thesis_snapshots_keeps_first():
    md = (
        _make_snapshot("A")
        + "\n# Chain section\n"
        + _make_snapshot("B")
        + "\n# Rubric section\n"
        + _make_snapshot("C")
        + "\n# Elasticity section\n"
    )
    out = dedupe_thesis_snapshots(md)
    # 第一段保留、其余删除
    assert out.count(THESIS_SNAPSHOT_START) == 1
    assert "## A 标的速写" in out
    assert "## B 标的速写" not in out
    assert "## C 标的速写" not in out


def test_compose_writes_merged_report(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-05-17",
                              f"{_make_snapshot(m)}\n# {m} 主体\nbody of {m}\n")

    result = compose(stock_dir=tmp_path, today="2026-05-17")
    merged = Path(result["merged_report_md"])
    assert merged.exists()
    content = merged.read_text(encoding="utf-8")
    for m in ANALYSIS_MODULES:
        assert f"# {m} 主体" in content
        assert f"body of {m}" in content
    # 只剩一段速写
    assert content.count(THESIS_SNAPSHOT_START) == 1


def test_compose_writes_manifest(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-04-30",
                              f"# {m}\n")
    result = compose(stock_dir=tmp_path, today="2026-05-17")
    manifest_path = Path(result["merged_report_md"]).parent / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["today"] == "2026-05-17"
    assert manifest["modules"]["chain"]["ymd"] == "2026-04-30"
    assert manifest["modules"]["peers"]["ymd"] == "2026-04-30"


def test_compose_pending_list(tmp_path):
    for m in ANALYSIS_MODULES:
        _write_module_report(tmp_path, m, "2026-05-17", _make_snapshot(m) + f"# {m}\n")
    result = compose(stock_dir=tmp_path, today="2026-05-17")
    assert result["pending"] == ["step_0_task_lock", "step_8_conclusion", "bear_case", "fact_check", "html"]


def test_compose_errors_on_missing_module(tmp_path):
    for m in ANALYSIS_MODULES[:-1]:  # 缺 peers
        _write_module_report(tmp_path, m, "2026-05-17", "# x\n")
    try:
        compose(stock_dir=tmp_path, today="2026-05-17")
        assert False, "应该抛错"
    except FileNotFoundError as e:
        assert "peers" in str(e)


def _write_module_data(tmp_path, module, ymd, payload):
    write_module_data(tmp_path, module, ymd, payload)


def _full_module_payload(module: str, ymd: str) -> dict:
    """构造一份每模块都至少含 {module, ymd, meta, summary?} 的 data.json。"""
    return {
        "module": module,
        "ymd": ymd,
        "meta": {"code": "002594", "name": "比亚迪", "industry": "新能源汽车"},
        "summary": {f"{module}_marker": True},
    }


def test_merge_data_json_namespaces_by_module(tmp_path):
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]:
        _write_module_data(tmp_path, m, "2026-05-15", _full_module_payload(m, "2026-05-15"))
    merged = merge_data_json(stock_dir=tmp_path, today="2026-05-15")
    assert "meta" in merged
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "peers"]:
        assert m in merged
        assert merged[m]["summary"][f"{m}_marker"] is True
    # flow-tech → flow_tech namespace
    assert "flow_tech" in merged
    assert "flow-tech" not in merged


def test_merge_data_json_meta_session_id_format(tmp_path):
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]:
        _write_module_data(tmp_path, m, "2026-05-15", _full_module_payload(m, "2026-05-15"))
    merged = merge_data_json(stock_dir=tmp_path, today="2026-05-15", stock_code="002594", stock_name="比亚迪")
    assert merged["meta"]["stock_code"] == "002594"
    assert merged["meta"]["stock_name"] == "比亚迪"
    assert merged["meta"]["ymd"] == "2026-05-15"
    assert re.match(r"^0x[0-9a-f]{4}$", merged["meta"]["session_id"])
    assert re.match(r"^\d{2}:\d{2}$", merged["meta"]["time_utc8"])


def test_merge_data_json_research_status_first_coverage(tmp_path):
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]:
        _write_module_data(tmp_path, m, "2026-05-15", _full_module_payload(m, "2026-05-15"))
    merged = merge_data_json(stock_dir=tmp_path, today="2026-05-15", stock_code="002594", stock_name="比亚迪")
    assert merged["meta"]["research_status"] == "首次覆盖"


def test_merge_data_json_research_status_follow_up_when_history_exists(tmp_path):
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]:
        _write_module_data(tmp_path, m, "2026-05-15", _full_module_payload(m, "2026-05-15"))
    (tmp_path / "report" / "2026-04-15").mkdir(parents=True)
    (tmp_path / "report" / "2026-04-15" / "report.md").write_text("old", encoding="utf-8")
    merged = merge_data_json(stock_dir=tmp_path, today="2026-05-15", stock_code="002594", stock_name="比亚迪")
    assert merged["meta"]["research_status"] == "持续跟踪"


def test_merge_data_json_data_as_of_picks_max_ymd(tmp_path):
    _write_module_data(tmp_path, "chain", "2026-04-15", _full_module_payload("chain", "2026-04-15"))
    _write_module_data(tmp_path, "rubric", "2026-04-15", _full_module_payload("rubric", "2026-04-15"))
    _write_module_data(tmp_path, "elasticity", "2026-04-15", _full_module_payload("elasticity", "2026-04-15"))
    _write_module_data(tmp_path, "risk", "2026-05-14", _full_module_payload("risk", "2026-05-14"))
    _write_module_data(tmp_path, "valuation", "2026-05-15", _full_module_payload("valuation", "2026-05-15"))
    _write_module_data(tmp_path, "flow-tech", "2026-05-15", _full_module_payload("flow-tech", "2026-05-15"))
    _write_module_data(tmp_path, "peers", "2026-04-15", _full_module_payload("peers", "2026-04-15"))
    merged = merge_data_json(stock_dir=tmp_path, today="2026-05-15", stock_code="002594", stock_name="比亚迪")
    assert merged["meta"]["data_as_of"] == "2026-05-15"


def test_compose_writes_merged_data_json(tmp_path):
    # 同时塞 report.md 和 data.json
    for m in ["chain", "rubric", "elasticity", "risk", "valuation", "flow-tech", "peers"]:
        _write_module_data(tmp_path, m, "2026-05-15", _full_module_payload(m, "2026-05-15"))
        # write_module_data 已经设了 latest 软链；同目录补 report.md
        (tmp_path / m / "2026-05-15" / "report.md").write_text(
            f"<!-- THESIS_SNAPSHOT_START --> {m} <!-- THESIS_SNAPSHOT_END -->\n# {m}\n",
            encoding="utf-8",
        )
    result = compose(stock_dir=tmp_path, today="2026-05-15", stock_code="002594", stock_name="比亚迪")
    merged_data_path = tmp_path / "report" / "2026-05-15" / "data.json"
    assert merged_data_path.exists()
    d = json.loads(merged_data_path.read_text(encoding="utf-8"))
    assert d["meta"]["stock_code"] == "002594"
    assert "chain" in d and "flow_tech" in d
    assert "merged_data_json" in result

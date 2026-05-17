"""测试 build_inventory.py：读 data.json → 输出 data_inventory.md"""
import pytest
pytest.skip("v4 legacy", allow_module_level=True)

import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'

def test_inventory_includes_all_blocks(tmp_path):
    """data_inventory.md 必须列出 data.json 中所有 blocks 与行数。"""
    data_path = tmp_path / 'data.json'
    data_path.write_text((FIXTURES / 'mini_data.json').read_text())
    inv_path = tmp_path / 'data_inventory.md'

    subprocess.run(
        ['python', str(Path(__file__).parent.parent / 'build_inventory.py'),
         '--data', str(data_path), '--out', str(inv_path)],
        check=True,
    )

    content = inv_path.read_text()
    # 必须列出所有 blocks
    for block in ['financial_abstract', 'fund_flow', 'research', 'top_holders']:
        assert block in content, f"inventory 缺 {block}"
    # 必须标记空 block 为 ❌
    assert '❌' in content, "空的 top_holders/news 应该被标记 ❌"
    # 必须列出 Step 字段需求映射
    assert 'Step' in content and '字段需求映射' in content

def test_inventory_marks_latest_dates(tmp_path):
    """inventory 中每个 block 必须显示最新日期。"""
    data_path = tmp_path / 'data.json'
    data_path.write_text((FIXTURES / 'mini_data.json').read_text())
    inv_path = tmp_path / 'data_inventory.md'

    subprocess.run(
        ['python', str(Path(__file__).parent.parent / 'build_inventory.py'),
         '--data', str(data_path), '--out', str(inv_path)],
        check=True,
    )
    content = inv_path.read_text()
    assert '20260331' in content or '2026-03-31' in content
    assert '2026-05-15' in content


def test_inventory_recognizes_top_level_financials(tmp_path):
    """financials 是 data.json 顶层字段，Step 3/4/5/7 应识别它存在（不报 ❌）。"""
    data_path = tmp_path / 'data.json'
    data_path.write_text((FIXTURES / 'mini_data.json').read_text())
    inv_path = tmp_path / 'data_inventory.md'

    subprocess.run(
        ['python', str(Path(__file__).parent.parent / 'build_inventory.py'),
         '--data', str(data_path), '--out', str(inv_path)],
        check=True,
    )
    content = inv_path.read_text()
    # 找 "Step 3" 行，financials 既在顶层 mini_data.json 中存在，就不应该被列入 missing
    step_section = content.split('## Step 字段需求映射')[1].split('##')[0]
    # Step 3 行不应该出现 "缺 financials"（top_holders 是空数组允许缺）
    step3_line = [l for l in step_section.splitlines() if 'Step 3' in l]
    assert step3_line, "Step 3 行未找到"
    # financials 不应出现在缺失项里（top_holders 仍可以缺）
    assert 'financials' not in step3_line[0] or '缺 financials' not in step3_line[0], \
        f"Step 3 行不应误报 financials 缺失: {step3_line[0]}"

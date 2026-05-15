"""测试 build_inventory.py：读 data.json → 输出 data_inventory.md"""
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

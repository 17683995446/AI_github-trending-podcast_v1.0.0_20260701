"""集成测试共享fixture。

集成测试关注多模块协作，可能需要真实文件系统但不依赖外部API。
"""

import pytest
from pathlib import Path
import shutil
import os


@pytest.fixture
def demo_output_dir(tmp_path: Path) -> Path:
    """基于真实demo数据的集成测试目录。"""
    source = Path(__file__).parent.parent.parent / "output_demo"
    if not source.exists():
        pytest.skip("demo数据目录不存在")
    dest = tmp_path / "output_demo"
    shutil.copytree(source, dest)
    return dest

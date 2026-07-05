"""单元测试共享fixture。

单元测试关注单个函数/类的行为，不依赖外部资源。
"""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """临时输出目录，测试后自动清理。"""
    d = tmp_path / "output_test"
    d.mkdir()
    return d

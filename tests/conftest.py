"""共享测试 fixtures（阶段1: 测试基础设施规范化）。

消除 5+ 个测试文件中重复的 mock 项目创建逻辑，
以及 3 个文件中重复的 LLM_API_KEY 环境变量设置。

Fixures:
    - ``mock_output_dir``  → 创建含2个模拟项目的临时目录
    - ``mock_repo``        → 构造测试用 RepoInfo
    - ``output_demo_dir``  → 真实 demo 数据目录（带自动跳过）
    - ``_set_test_llm_key`` → autouse，自动注入测试用 API Key
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════
# autouse: 测试环境隔离
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _set_test_llm_key():
    """自动注入测试用 API Key，避免初始化报错。

    替代 test_phase6_polish.py:17 / test_llm_enhancer.py:7 /
    test_phase5_llm_realtime.py 中重复的 os.environ.setdefault 调用。
    """
    old_val = os.environ.get("LLM_API_KEY")
    os.environ.setdefault("LLM_API_KEY", "sk-test-key-for-unit-tests")
    yield
    if old_val is None:
        os.environ.pop("LLM_API_KEY", None)
    else:
        os.environ["LLM_API_KEY"] = old_val


# ═══════════════════════════════════════════════════════════════════
# mock_output_dir: 模拟项目输出目录
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_output_dir(tmp_path: Path) -> Path:
    """创建含2个模拟项目的临时目录。

    替代 test_stage13_search.py:14-33 / test_stage14_comparison.py:10-26 /
    test_stage6_podcast_feed.py:48-64 / test_stage9_export.py 中重复的
    _setup_projects() 方法。

    目录结构:
        tmp_path/output_test/owner_repo1.md
        tmp_path/output_test/owner_repo1_script.txt
        tmp_path/output_test/owner_repo1.mp3
        tmp_path/output_test/owner_repo2.md
        tmp_path/output_test/owner_repo2_script.txt
        tmp_path/output_test/owner_repo2.mp3
    """
    out_dir = tmp_path / "output_test"
    out_dir.mkdir()

    # 项目1: Python ML 项目
    (out_dir / "owner_repo1.md").write_text(
        "# Project One\n\n"
        "| 描述 | A Python ML library |\n"
        "| 星标 | 500 |\n"
        "| 编程语言 | Python |\n"
        "| 协议 | MIT |\n\n"
        "This is a Python project about machine learning.\n"
        "It uses TensorFlow and PyTorch for deep learning.",
        encoding="utf-8",
    )
    (out_dir / "owner_repo1_script.txt").write_text("A: Hello\nB: Welcome", encoding="utf-8")
    (out_dir / "owner_repo1.mp3").write_bytes(b"fake mp3 data")

    # 项目2: Rust Web 框架
    (out_dir / "owner_repo2.md").write_text(
        "# Project Two\n\n"
        "| 描述 | A Rust web framework |\n"
        "| 星标 | 300 |\n"
        "| 编程语言 | Rust |\n"
        "| 协议 | Apache-2.0 |\n\n"
        "A Rust project for web assembly.\n"
        "Fast and safe memory management.",
        encoding="utf-8",
    )
    (out_dir / "owner_repo2_script.txt").write_text("A: Hi\nB: Greetings", encoding="utf-8")
    (out_dir / "owner_repo2.mp3").write_bytes(b"fake mp3 data")

    return tmp_path


# ═══════════════════════════════════════════════════════════════════
# mock_repo: 测试用 RepoInfo
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_repo():
    """构造测试用 RepoInfo。

    替代 test_phase6_polish.py:22-42 中的 _make_repo() 函数。
    """
    from gh_trending_audio.github_fetcher import RepoInfo
    return RepoInfo(
        full_name="owner/test-repo",
        name="test-repo",
        owner="owner",
        description="A test repository for unit testing",
        url="https://github.com/owner/test-repo",
        homepage="https://test-repo.example.com",
        language="Python",
        stars=1234,
        forks=56,
        open_issues=10,
        watchers=100,
        topics=["web", "api", "testing"],
        created_at="2023-01-15T00:00:00Z",
        license_name="MIT",
    )


# ═══════════════════════════════════════════════════════════════════
# output_demo_dir: 真实 demo 数据目录
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def output_demo_dir() -> Path:
    """返回真实 demo 数据目录（不存在则跳过测试）。

    替代 test_stage7_oss_replacement.py 中 8 处重复的
    output_dir + pytest.skip 模式。
    """
    output_dir = Path(__file__).parent.parent / "output_demo"
    if not output_dir.exists():
        pytest.skip("output_demo 目录不存在")
    return output_dir


# ═══════════════════════════════════════════════════════════════════
# 统一 Mock Fixture（阶段6新增）
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_github_client():
    """统一Mock GitHub客户端，避免真实API调用。"""
    from unittest.mock import MagicMock, patch
    from gh_trending_audio.models import RepoInfo
    
    mock_client = MagicMock()
    mock_repo = RepoInfo(
        full_name="test/repo",
        name="repo",
        url="https://github.com/test/repo",
        stars=100,
        language="Python",
        description="Test repository",
    )
    mock_client.get_repo_info.return_value = mock_repo
    mock_client.fetch_trending.return_value = [mock_repo]
    return mock_client


@pytest.fixture
def mock_llm_backend():
    """统一Mock LLM后端。"""
    from unittest.mock import MagicMock
    
    mock_backend = MagicMock()
    mock_backend.is_available.return_value = True
    mock_backend.model = "test-model"
    mock_backend.get_client.return_value = MagicMock()
    return mock_backend


@pytest.fixture
def mock_tts_engine():
    """统一Mock TTS引擎。"""
    from unittest.mock import MagicMock, patch
    
    mock_tts = MagicMock()
    mock_tts.text_to_speech.return_value = True
    return mock_tts

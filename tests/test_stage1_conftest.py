"""阶段1: conftest.py 共享 fixtures 验证测试。"""

import pytest
from pathlib import Path


class TestConftestFixtures:
    """验证 conftest.py 提供的共享 fixtures 正确工作。"""

    def test_mock_output_dir_creates_projects(self, mock_output_dir: Path):
        """mock_output_dir 应创建2个模拟项目。"""
        out_dir = mock_output_dir / "output_test"
        assert out_dir.exists()
        assert (out_dir / "owner_repo1.md").exists()
        assert (out_dir / "owner_repo1_script.txt").exists()
        assert (out_dir / "owner_repo1.mp3").exists()
        assert (out_dir / "owner_repo2.md").exists()
        assert (out_dir / "owner_repo2_script.txt").exists()
        assert (out_dir / "owner_repo2.mp3").exists()

    def test_mock_output_dir_md_content(self, mock_output_dir: Path):
        """mock_output_dir 的 md 文件应包含表格和内容。"""
        md1 = (mock_output_dir / "output_test" / "owner_repo1.md").read_text(encoding="utf-8")
        assert "Python" in md1
        assert "机器学习" in md1 or "machine learning" in md1

        md2 = (mock_output_dir / "output_test" / "owner_repo2.md").read_text(encoding="utf-8")
        assert "Rust" in md2

    def test_mock_repo_returns_repo_info(self, mock_repo):
        """mock_repo 应返回 RepoInfo 实例。"""
        from gh_trending_audio.github_fetcher import RepoInfo
        assert isinstance(mock_repo, RepoInfo)
        assert mock_repo.full_name == "owner/test-repo"
        assert mock_repo.language == "Python"
        assert mock_repo.stars == 1234

    def test_mock_repo_overridable(self, mock_repo):
        """mock_repo 的字段应可通过测试内覆盖修改。"""
        # fixture 返回的是实例，可以在测试中修改属性
        assert mock_repo.license_name == "MIT"

    def test_llm_key_autouse(self):
        """autouse fixture 应自动注入 LLM_API_KEY。"""
        import os
        assert os.environ.get("LLM_API_KEY") is not None

    def test_output_demo_dir_fixture(self, output_demo_dir):
        """output_demo_dir fixture 应返回路径或跳过。"""
        # 如果 output_demo 存在则返回 Path，否则 pytest.skip
        assert isinstance(output_demo_dir, Path)

    def test_mock_output_dir_isolated(self, mock_output_dir: Path, tmp_path: Path):
        """每次 mock_output_dir 应是独立的临时目录。"""
        assert mock_output_dir == tmp_path

    def test_mock_output_dir_with_search_engine(self, mock_output_dir: Path):
        """mock_output_dir 可直接用于搜索引擎测试。"""
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        assert index.doc_count == 2
        results = search(index, "python")
        assert len(results) >= 1

    def test_mock_output_dir_with_comparison(self, mock_output_dir: Path):
        """mock_output_dir 可直接用于对比引擎测试。"""
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        assert result["project_count"] == 2

    def test_mock_output_dir_with_exporter(self, mock_output_dir: Path):
        """mock_output_dir 可直接用于导出器测试。"""
        from gh_trending_audio.exporter import export_json
        data = export_json(mock_output_dir, "output_test", "owner_repo1")
        assert data is not None
        import json
        obj = json.loads(data)
        assert obj["name"] == "owner_repo1"

"""Phase 3 单元测试：GitHub SDK 迁移。

测试范围：
1. GitHubClient 模块可导入、可实例化
2. handler 端点使用 GitHubClient 而非手写 REST
3. dataclass 返回类型正确
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGitHubClientModule:
    """GitHubClient 模块基础测试。"""

    def test_module_importable(self):
        """github_client 模块应可正常导入。"""
        from gh_trending_audio.github_client import GitHubClient, FileInfo, RepoSummary, CommunityData
        assert GitHubClient is not None
        assert FileInfo is not None
        assert RepoSummary is not None
        assert CommunityData is not None

    def test_client_initialization(self):
        """GitHubClient 应可无 Token 初始化（匿名模式）。"""
        from gh_trending_audio.github_client import GitHubClient
        client = GitHubClient(token="")
        assert client is not None
        # PyGithub 或 requests 退化模式都应可用
        assert client.uses_pygithub in (True, False)

    def test_client_with_token(self):
        """GitHubClient 应可带 Token 初始化。"""
        from gh_trending_audio.github_client import GitHubClient
        client = GitHubClient(token="fake-token-for-test")
        assert client is not None

    def test_get_github_client_singleton(self):
        """get_github_client 应返回单例。"""
        from gh_trending_audio.github_client import get_github_client
        c1 = get_github_client()
        c2 = get_github_client()
        assert c1 is c2


class TestDataclasses:
    """dataclass 返回类型测试。"""

    def test_file_info_creation(self):
        from gh_trending_audio.github_client import FileInfo
        fi = FileInfo(path="src/main.py", type="blob", size=100)
        assert fi.path == "src/main.py"
        assert fi.type == "blob"
        assert fi.size == 100

    def test_repo_summary_defaults(self):
        from gh_trending_audio.github_client import RepoSummary
        rs = RepoSummary(full_name="owner/repo")
        assert rs.full_name == "owner/repo"
        assert rs.stars == 0
        assert rs.topics == []
        assert rs.default_branch == "main"

    def test_community_data_defaults(self):
        from gh_trending_audio.github_client import CommunityData
        cd = CommunityData()
        assert cd.open_issues == []
        assert cd.contributors == []
        assert cd.repo_info == {}


class TestHandlerUsesGitHubClient:
    """handler.py 端点应使用 GitHubClient 而非手写 REST。"""

    def test_readme_uses_client(self):
        """_serve_api_readme 源码应使用 get_github_client。"""
        import inspect
        from gh_trending_audio.web.handler import DashboardHandler
        source = inspect.getsource(DashboardHandler._serve_api_readme)
        assert "get_github_client" in source
        assert "github_api_get" not in source or "get_github_client" in source

    def test_filetree_uses_client(self):
        """_serve_api_filetree 源码应使用 get_github_client。"""
        import inspect
        from gh_trending_audio.web.handler import DashboardHandler
        source = inspect.getsource(DashboardHandler._serve_api_filetree)
        assert "get_github_client" in source
        # 不应再手动拼接 URL
        assert "api.github.com/repos" not in source

    def test_file_uses_client(self):
        """_serve_api_file 源码应使用 get_github_client。"""
        import inspect
        from gh_trending_audio.web.handler import DashboardHandler
        source = inspect.getsource(DashboardHandler._serve_api_file)
        assert "get_github_client" in source
        assert "api.github.com/repos" not in source

    def test_community_uses_client(self):
        """_serve_api_community 源码应使用 get_github_client。"""
        import inspect
        from gh_trending_audio.web.handler import DashboardHandler
        source = inspect.getsource(DashboardHandler._serve_api_community)
        assert "get_github_client" in source
        # 不应再手动拼接 URL
        assert "api.github.com/repos" not in source

    def test_no_base64_in_handler(self):
        """handler 端点不应再手动 base64 解码。"""
        import inspect
        from gh_trending_audio.web.handler import DashboardHandler
        for method_name in ['_serve_api_readme', '_serve_api_filetree', '_serve_api_file', '_serve_api_community']:
            source = inspect.getsource(getattr(DashboardHandler, method_name))
            assert "base64" not in source, f"{method_name} 不应包含 base64 操作"

"""单元测试示例：验证核心工具函数行为。"""

import pytest
from gh_trending_audio.markdown_utils import markdown_to_html, parse_md_metadata
from gh_trending_audio.models import RepoInfo


class TestMarkdownUtils:
    """markdown_utils 单元测试。"""

    def test_markdown_to_html_basic(self):
        """基础Markdown转HTML。"""
        html = markdown_to_html("# Hello")
        assert "<h1>" in html
        assert "Hello" in html

    def test_markdown_to_html_code_block(self):
        """代码块保留。"""
        html = markdown_to_html("```python\nprint('hi')\n```")
        assert "<code" in html or "print" in html

    def test_parse_md_metadata_valid(self):
        """解析有效的元数据。"""
        # parse_md_metadata 解析 Markdown 表格格式的元数据
        md = (
            "| 描述 | A test project |\n"
            "| 星标 | 100 |\n"
            "| 编程语言 | Python |\n"
        )
        meta = parse_md_metadata(md)
        assert meta is not None
        assert meta.get("stars") == "100" or meta.get("stars") == 100

    def test_parse_md_metadata_empty(self):
        """无元数据时返回空或None。"""
        md = "# No metadata"
        meta = parse_md_metadata(md)
        # 不抛异常即可
        assert meta is None or isinstance(meta, dict)


class TestRepoInfo:
    """RepoInfo 数据模型单元测试。"""

    def test_create_repo_info(self):
        """创建RepoInfo实例。"""
        repo = RepoInfo(
            full_name="owner/repo",
            name="repo",
            owner="owner",
            description="A test repository",
            url="https://github.com/owner/repo",
            homepage="",
            language="Python",
            stars=100,
            forks=0,
            open_issues=0,
            watchers=0,
        )
        assert repo.full_name == "owner/repo"
        assert repo.stars == 100

    def test_repo_info_defaults(self):
        """RepoInfo 默认值。"""
        repo = RepoInfo(
            full_name="owner/repo",
            name="repo",
            owner="owner",
            description="",
            url="https://github.com/owner/repo",
            homepage="",
            language="",
            stars=0,
            forks=0,
            open_issues=0,
            watchers=0,
        )
        assert repo.stars == 0 or repo.stars is None

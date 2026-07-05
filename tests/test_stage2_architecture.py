"""阶段2: 架构层级修复 测试。

验证 project_scanner 和 markdown_utils 从 web 上移到核心包后，
所有导入路径正确工作，且不再有核心层反向依赖 web 层。
"""

import pytest
from pathlib import Path


class TestCoreModuleRelocation:
    """核心模块上移验证。"""

    def test_core_project_scanner_exists(self):
        """核心层应有 project_scanner 模块。"""
        from gh_trending_audio import project_scanner
        assert hasattr(project_scanner, "scan_projects")
        assert hasattr(project_scanner, "get_project_detail")
        assert hasattr(project_scanner, "get_audio_duration")

    def test_core_markdown_utils_exists(self):
        """核心层应有 markdown_utils 模块。"""
        from gh_trending_audio import markdown_utils
        assert hasattr(markdown_utils, "parse_md_metadata")
        assert hasattr(markdown_utils, "markdown_to_html")
        assert hasattr(markdown_utils, "build_repo_from_md")

    def test_web_project_scanner_is_shim(self):
        """web/project_scanner 应是兼容垫片。"""
        from gh_trending_audio.web import project_scanner as web_ps
        from gh_trending_audio import project_scanner as core_ps
        # web 版本的函数应与核心版本相同（同一对象）
        assert web_ps.scan_projects is core_ps.scan_projects
        assert web_ps.get_project_detail is core_ps.get_project_detail

    def test_web_markdown_utils_is_shim(self):
        """web/markdown_utils 应是兼容垫片。"""
        from gh_trending_audio.web import markdown_utils as web_mu
        from gh_trending_audio import markdown_utils as core_mu
        assert web_mu.parse_md_metadata is core_mu.parse_md_metadata
        assert web_mu.markdown_to_html is core_mu.markdown_to_html

    def test_subtitle_gen_uses_core_import(self):
        """subtitle_gen 不应再从 web 导入 project_scanner。"""
        import inspect
        from gh_trending_audio import subtitle_gen
        source = inspect.getsource(subtitle_gen)
        assert "from .web.project_scanner" not in source
        assert "from .project_scanner import" in source

    def test_podcast_feed_uses_core_import(self):
        """podcast_feed 不应再从 web 导入 project_scanner。"""
        import inspect
        from gh_trending_audio import podcast_feed
        source = inspect.getsource(podcast_feed)
        assert "from .web.project_scanner" not in source

    def test_exporter_uses_core_import(self):
        """exporter 不应再从 web 导入 project_scanner。"""
        import inspect
        from gh_trending_audio import exporter
        source = inspect.getsource(exporter)
        assert "from .web.project_scanner" not in source

    def test_search_engine_uses_core_import(self):
        """search_engine 不应再从 web 导入 project_scanner。"""
        import inspect
        from gh_trending_audio import search_engine
        source = inspect.getsource(search_engine)
        assert "from .web.project_scanner" not in source

    def test_comparison_engine_uses_core_import(self):
        """comparison_engine 不应再从 web 导入 project_scanner。"""
        import inspect
        from gh_trending_audio import comparison_engine
        source = inspect.getsource(comparison_engine)
        assert "from .web.project_scanner" not in source

    def test_no_core_to_web_dependency(self):
        """核心模块不应有 from .web 导入。"""
        import inspect
        core_modules = [
            "subtitle_gen", "podcast_feed", "exporter",
            "search_engine", "comparison_engine",
        ]
        for mod_name in core_modules:
            mod = __import__(f"gh_trending_audio.{mod_name}", fromlist=[mod_name])
            source = inspect.getsource(mod)
            assert "from .web." not in source, f"{mod_name} 仍依赖 web 层"

    def test_lazy_export_core_modules(self):
        """__init__.py 应导出核心层模块。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "scan_projects")
        assert hasattr(gh_trending_audio, "get_project_detail")
        assert hasattr(gh_trending_audio, "parse_md_metadata")
        assert hasattr(gh_trending_audio, "markdown_to_html")

    def test_core_scan_projects_works(self, mock_output_dir: Path):
        """核心层 scan_projects 应正确工作。"""
        from gh_trending_audio.project_scanner import scan_projects
        projects = scan_projects(mock_output_dir)
        assert len(projects) == 2
        names = [p["name"] for p in projects]
        assert "owner_repo1" in names
        assert "owner_repo2" in names

    def test_core_get_project_detail_works(self, mock_output_dir: Path):
        """核心层 get_project_detail 应正确工作。"""
        from gh_trending_audio.project_scanner import get_project_detail
        detail = get_project_detail(mock_output_dir, "output_test", "owner_repo1")
        assert detail is not None
        assert detail["name"] == "owner_repo1"
        assert "md_content" in detail

    def test_web_shim_still_works(self, mock_output_dir: Path):
        """web 兼容垫片应仍被 web 层模块正常使用。"""
        from gh_trending_audio.web.project_scanner import scan_projects
        projects = scan_projects(mock_output_dir)
        assert len(projects) == 2

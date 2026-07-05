"""阶段3: API处理器模块化拆分 验证测试。"""

import pytest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试：模块结构验证
# ═══════════════════════════════════════════════════════════════════

class TestHandlerPackageStructure:
    """验证 handlers 包结构完整性。"""

    def test_handlers_package_exists(self):
        """handlers 包应存在。"""
        from gh_trending_audio.web import handlers
        assert handlers is not None

    def test_common_module_exists(self):
        """_common 共享模块应存在。"""
        from gh_trending_audio.web.handlers import _common
        assert hasattr(_common, "send_json")
        assert hasattr(_common, "scan_projects")
        assert hasattr(_common, "_FILETREE_CACHE")

    def test_projects_module_exists(self):
        """projects 模块应存在并包含所有项目处理器。"""
        from gh_trending_audio.web.handlers import projects
        for name in ["serve_api_projects", "serve_api_project", "serve_api_stats",
                      "serve_api_status", "serve_sse_events", "delete_project",
                      "find_project_by_name", "handle_quick_route"]:
            assert hasattr(projects, name), f"projects 缺少 {name}"

    def test_pipeline_module_exists(self):
        """pipeline 模块应存在并包含所有流水线处理器。"""
        from gh_trending_audio.web.handlers import pipeline
        for name in ["start_pipeline", "start_comparison", "handle_ask", "handle_onboarding"]:
            assert hasattr(pipeline, name), f"pipeline 缺少 {name}"

    def test_github_browse_module_exists(self):
        """github_browse 模块应存在。"""
        from gh_trending_audio.web.handlers import github_browse
        for name in ["serve_api_readme", "serve_api_filetree", "serve_api_file",
                      "serve_api_community", "handle_search_code"]:
            assert hasattr(github_browse, name), f"github_browse 缺少 {name}"

    def test_files_module_exists(self):
        """files 模块应存在。"""
        from gh_trending_audio.web.handlers import files
        assert hasattr(files, "serve_file")

    def test_feed_module_exists(self):
        """feed 模块应存在。"""
        from gh_trending_audio.web.handlers import feed
        for name in ["serve_podcast_feed", "serve_opml", "serve_feed_stats"]:
            assert hasattr(feed, name), f"feed 缺少 {name}"

    def test_media_export_module_exists(self):
        """media_export 模块应存在。"""
        from gh_trending_audio.web.handlers import media_export
        for name in ["serve_subtitle", "serve_export", "serve_batch_export"]:
            assert hasattr(media_export, name), f"media_export 缺少 {name}"

    def test_system_module_exists(self):
        """system 模块应存在。"""
        from gh_trending_audio.web.handlers import system
        for name in ["serve_system_backends", "serve_code_symbols",
                      "serve_code_intel_status", "serve_preferences_schema"]:
            assert hasattr(system, name), f"system 缺少 {name}"

    def test_search_compare_module_exists(self):
        """search_compare 模块应存在。"""
        from gh_trending_audio.web.handlers import search_compare
        for name in ["serve_search", "serve_search_suggestions",
                      "serve_search_reindex", "serve_compare_projects"]:
            assert hasattr(search_compare, name), f"search_compare 缺少 {name}"


# ═══════════════════════════════════════════════════════════════════
# 兼容性验证
# ═══════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """验证 api_handlers.py 兼容垫片正确 re-export 所有符号。"""

    def test_api_handlers_is_shim(self):
        """api_handlers.py 应为兼容垫片。"""
        import inspect
        from gh_trending_audio.web import api_handlers
        source = inspect.getsource(api_handlers)
        assert "handlers" in source
        assert "re-export" in source.lower() or "兼容" in source

    def test_all_public_functions_accessible(self):
        """所有公共函数应通过 api_handlers 访问。"""
        from gh_trending_audio.web import api_handlers
        public_names = [
            "serve_api_projects", "serve_api_project", "serve_api_stats",
            "serve_api_status", "serve_sse_events", "delete_project",
            "handle_quick_route", "start_pipeline", "start_comparison",
            "handle_ask", "handle_onboarding", "serve_api_readme",
            "serve_api_filetree", "serve_api_file", "serve_api_community",
            "handle_search_code", "serve_file", "serve_podcast_feed",
            "serve_opml", "serve_feed_stats", "serve_subtitle",
            "serve_export", "serve_batch_export", "serve_system_backends",
            "serve_code_symbols", "serve_code_intel_status",
            "serve_preferences_schema", "serve_search",
            "serve_search_suggestions", "serve_search_reindex",
            "serve_compare_projects",
        ]
        for name in public_names:
            assert hasattr(api_handlers, name), f"api_handlers 缺少 {name}"

    def test_private_symbols_accessible(self):
        """私有/共享符号应通过 api_handlers 访问。"""
        from gh_trending_audio.web import api_handlers
        assert hasattr(api_handlers, "_FILETREE_CACHE")
        assert hasattr(api_handlers, "_FILE_CONTENT_CACHE")
        assert hasattr(api_handlers, "send_json")
        assert hasattr(api_handlers, "logger")

    def test_function_identity_matches(self):
        """api_handlers 的函数应与 handlers 包中的同一对象。"""
        from gh_trending_audio.web import api_handlers
        from gh_trending_audio.web.handlers import projects, pipeline
        assert api_handlers.serve_api_projects is projects.serve_api_projects
        assert api_handlers.handle_ask is pipeline.handle_ask

    def test_cache_is_shared_instance(self):
        """缓存实例应在所有模块间共享。"""
        from gh_trending_audio.web.handlers import _common, github_browse
        assert _common._FILETREE_CACHE is github_browse._FILETREE_CACHE
        assert _common._FILE_CONTENT_CACHE is github_browse._FILE_CONTENT_CACHE


# ═══════════════════════════════════════════════════════════════════
# 模块大小验证
# ═══════════════════════════════════════════════════════════════════

class TestModuleSize:
    """验证拆分后各模块大小合理（单一职责原则）。"""

    def test_api_handlers_shim_is_small(self):
        """api_handlers.py 垫片应小于 30 行。"""
        import gh_trending_audio.web.api_handlers as ah
        import inspect
        source = inspect.getsource(ah)
        line_count = len(source.strip().split("\n"))
        assert line_count < 30, f"api_handlers 垫片有 {line_count} 行，应 < 30"

    def test_no_module_exceeds_350_lines(self):
        """拆分后任一子模块不应超过 350 行。"""
        import inspect
        from gh_trending_audio.web.handlers import (
            projects, pipeline, github_browse, files,
            feed, media_export, system, search_compare,
        )
        for mod in [projects, pipeline, github_browse, files,
                     feed, media_export, system, search_compare]:
            source = inspect.getsource(mod)
            line_count = len(source.strip().split("\n"))
            assert line_count < 350, f"{mod.__name__} 有 {line_count} 行，应 < 350"


# ═══════════════════════════════════════════════════════════════════
# 功能验证
# ═══════════════════════════════════════════════════════════════════

class TestHandlerFunctionality:
    """验证拆分后处理器功能正常。"""

    def test_serve_api_projects_works(self, mock_output_dir):
        """serve_api_projects 应正常返回项目列表。"""
        from unittest.mock import MagicMock
        from gh_trending_audio.web.handlers.projects import serve_api_projects

        handler = MagicMock()
        serve_api_projects(handler, mock_output_dir)
        assert handler.send_response.called or handler.wfile.write.called

    def test_serve_api_stats_works(self, mock_output_dir):
        """serve_api_stats 应正常返回统计。"""
        from unittest.mock import MagicMock
        from gh_trending_audio.web.handlers.projects import serve_api_stats

        handler = MagicMock()
        serve_api_stats(handler, mock_output_dir)
        assert handler.send_response.called or handler.wfile.write.called

    def test_find_project_by_name_works(self, mock_output_dir):
        """find_project_by_name 应能找到项目。"""
        from gh_trending_audio.web.handlers.projects import find_project_by_name
        result = find_project_by_name(mock_output_dir, "owner_repo1")
        assert result is not None
        assert result["name"] == "owner_repo1"

    def test_serve_search_works(self, mock_output_dir):
        """serve_search 应能搜索到结果。"""
        from unittest.mock import MagicMock
        from gh_trending_audio.web.handlers.search_compare import serve_search

        handler = MagicMock()
        serve_search(handler, mock_output_dir, {"q": ["python"], "limit": ["10"]})
        assert handler.send_response.called or handler.wfile.write.called

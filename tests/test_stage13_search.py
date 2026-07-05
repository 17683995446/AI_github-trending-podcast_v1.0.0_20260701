"""阶段13: 全文搜索引擎 测试。"""

import pytest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestSearchEngineUnit:
    """全文搜索引擎单元测试。"""

    def test_tokenize_english(self):
        from gh_trending_audio.search_engine import _tokenize
        tokens = _tokenize("hello world python")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens

    def test_tokenize_chinese(self):
        from gh_trending_audio.search_engine import _tokenize
        tokens = _tokenize("机器学习深度学习")
        # 中文 2-gram
        assert len(tokens) > 0
        assert any("机器" in t for t in tokens)

    def test_tokenize_mixed(self):
        from gh_trending_audio.search_engine import _tokenize
        tokens = _tokenize("Python 机器学习 framework")
        assert "python" in tokens
        assert any("机器" in t for t in tokens)
        assert "framework" in tokens

    def test_tokenize_empty(self):
        from gh_trending_audio.search_engine import _tokenize
        assert _tokenize("") == []

    def test_build_index(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index
        index = build_index(mock_output_dir)
        assert index.doc_count == 2
        assert len(index.inverted) > 0
        assert index.avg_doc_length > 0

    def test_build_index_empty(self, tmp_path):
        from gh_trending_audio.search_engine import build_index
        index = build_index(tmp_path)
        assert index.doc_count == 0

    def test_search_english(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "python")
        assert len(results) >= 1
        assert "repo1" in results[0].title

    def test_search_chinese(self, tmp_path):
        from gh_trending_audio.search_engine import build_index, search
        # 创建包含中文内容的项目
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        (out_dir / "owner_repo1.md").write_text(
            "# 项目一\n\n这是一个关于机器学习的Python项目。\n"
            "使用TensorFlow和PyTorch进行深度学习。",
            encoding="utf-8",
        )
        (out_dir / "owner_repo1_script.txt").write_text("A: Hello", encoding="utf-8")
        (out_dir / "owner_repo1.mp3").write_bytes(b"fake")
        index = build_index(tmp_path)
        results = search(index, "机器学习")
        assert len(results) >= 1
        assert "repo1" in results[0].title

    def test_search_no_results(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "nonexistentterm12345")
        assert len(results) == 0

    def test_search_empty_query(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "")
        assert len(results) == 0

    def test_search_max_results(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "project", max_results=1)
        assert len(results) <= 1

    def test_search_result_has_snippet(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "python")
        assert len(results) >= 1
        assert results[0].snippet  # 非空
        assert results[0].score > 0

    def test_search_result_has_path(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, search
        index = build_index(mock_output_dir)
        results = search(index, "python")
        assert len(results) >= 1
        assert results[0].path.startswith("/project/")

    def test_generate_snippet_with_highlight(self):
        from gh_trending_audio.search_engine import _generate_snippet
        content = "This is a test about Python programming language."
        snippet = _generate_snippet(content, ["python"])
        assert "<mark>" in snippet
        assert "Python" in snippet

    def test_generate_snippet_no_match(self):
        from gh_trending_audio.search_engine import _generate_snippet
        content = "This is a test."
        snippet = _generate_snippet(content, ["nonexistent"])
        assert len(snippet) > 0

    def test_get_search_suggestions(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, get_search_suggestions
        index = build_index(mock_output_dir)
        suggestions = get_search_suggestions(index, "py")
        assert len(suggestions) > 0
        assert any("py" in s for s in suggestions)

    def test_get_search_suggestions_empty(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, get_search_suggestions
        index = build_index(mock_output_dir)
        suggestions = get_search_suggestions(index, "")
        assert len(suggestions) == 0

    def test_save_and_load_index(self, mock_output_dir):
        from gh_trending_audio.search_engine import build_index, save_index, load_index
        index = build_index(mock_output_dir)
        save_index(index, str(mock_output_dir / "idx"))
        loaded = load_index(str(mock_output_dir / "idx"))
        assert loaded is not None
        assert loaded.doc_count == index.doc_count

    def test_load_index_nonexistent(self, tmp_path):
        from gh_trending_audio.search_engine import load_index
        result = load_index(str(tmp_path / "nonexistent"))
        assert result is None


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestSearchEngineIntegration:
    """全文搜索 API 端点集成测试。"""

    def test_search_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/search" in r["pattern"] for r in routes)
        assert any("serve_search" in r["handler"] for r in routes)

    def test_search_suggestions_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/search-suggestions" in r["pattern"] for r in routes)

    def test_search_reindex_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/search-reindex" in r["pattern"] for r in routes)

    def test_search_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_search
        assert callable(serve_search)

    def test_dashboard_has_fts_overlay(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "ftsOverlay" in DASHBOARD_HTML
        assert "ftsInput" in DASHBOARD_HTML
        assert "ftsResults" in DASHBOARD_HTML

    def test_dashboard_has_fts_button(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "openFullTextSearch" in DASHBOARD_HTML
        assert "全文搜索" in DASHBOARD_HTML

    def test_dashboard_has_fts_javascript(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "executeFullTextSearch" in DASHBOARD_HTML
        assert "debouncedFts" in DASHBOARD_HTML
        assert "/api/search" in DASHBOARD_HTML

    def test_lazy_export_search(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "build_index")
        assert hasattr(gh_trending_audio, "search")
        assert hasattr(gh_trending_audio, "get_search_suggestions")

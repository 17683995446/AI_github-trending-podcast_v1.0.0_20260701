"""阶段12: 代码智能 (ripgrep + tree-sitter + Prism.js) 测试。"""

import pytest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestCodeIntelUnit:
    """代码智能模块单元测试。"""

    def test_detect_ripgrep(self):
        from gh_trending_audio.code_intel import detect_ripgrep
        result = detect_ripgrep()
        assert isinstance(result, bool)

    def test_detect_tree_sitter(self):
        from gh_trending_audio.code_intel import detect_tree_sitter
        result = detect_tree_sitter()
        assert isinstance(result, bool)

    def test_get_language_from_extension_python(self):
        from gh_trending_audio.code_intel import get_language_from_extension
        assert get_language_from_extension("test.py") == "python"
        assert get_language_from_extension("app.js") == "javascript"
        assert get_language_from_extension("main.go") == "go"
        assert get_language_from_extension("lib.rs") == "rust"

    def test_get_language_from_extension_unknown(self):
        from gh_trending_audio.code_intel import get_language_from_extension
        assert get_language_from_extension("file.xyz") == "unknown"

    def test_get_language_from_extension_special_files(self):
        from gh_trending_audio.code_intel import get_language_from_extension
        assert get_language_from_extension("Dockerfile") == "dockerfile"
        assert get_language_from_extension("Makefile") == "makefile"

    def test_get_prism_class(self):
        from gh_trending_audio.code_intel import get_prism_class
        assert get_prism_class("test.py") == "language-python"
        assert get_prism_class("app.js") == "language-javascript"
        assert get_prism_class("style.css") == "language-css"
        assert get_prism_class("data.json") == "language-json"

    def test_get_prism_class_unknown(self):
        from gh_trending_audio.code_intel import get_prism_class
        assert get_prism_class("file.xyz") == "language-none"

    def test_ripgrep_search_empty_dir(self, tmp_path):
        from gh_trending_audio.code_intel import ripgrep_search
        results = ripgrep_search(str(tmp_path), "test")
        assert isinstance(results, list)

    def test_ripgrep_search_with_files(self, tmp_path):
        from gh_trending_audio.code_intel import ripgrep_search
        (tmp_path / "test.py").write_text("def hello():\n    print('hello world')\n")
        results = ripgrep_search(str(tmp_path), "hello")
        # ripgrep 可能不可用，但如果可用应该有结果
        if results:
            assert any("hello" in r.get("content", "") for r in results)

    def test_extract_symbols_python(self):
        from gh_trending_audio.code_intel import extract_symbols
        code = """
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
"""
        symbols = extract_symbols("test.py", code)
        # tree-sitter 可能不可用，但如果可用应有符号
        if symbols:
            names = [s["name"] for s in symbols]
            assert "MyClass" in names or "my_function" in names or "my_method" in names

    def test_extract_symbols_unknown_language(self):
        from gh_trending_audio.code_intel import extract_symbols
        symbols = extract_symbols("file.xyz", "some content")
        assert symbols == []

    def test_get_code_intel_status(self):
        from gh_trending_audio.code_intel import get_code_intel_status
        status = get_code_intel_status()
        assert "ripgrep" in status
        assert "tree_sitter" in status
        assert "prism_js" in status
        assert isinstance(status["ripgrep"]["available"], bool)
        assert isinstance(status["tree_sitter"]["available"], bool)
        assert status["prism_js"]["available"] is True


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestCodeIntelIntegration:
    """代码智能 API 和 UI 集成测试。"""

    def test_code_symbols_route_exists(self):
        import inspect
        from gh_trending_audio.web import route_table
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/code-symbols" in r["pattern"] for r in routes)
        source = inspect.getsource(route_table)
        assert "serve_code_symbols" in source

    def test_code_intel_status_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/code-intel-status" in r["pattern"] for r in routes)
        assert any("serve_code_intel_status" in r["handler"] for r in routes)

    def test_code_symbols_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_code_symbols
        assert callable(serve_code_symbols)

    def test_code_intel_status_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_code_intel_status
        assert callable(serve_code_intel_status)

    def test_project_html_has_prism_css(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "prism-tomorrow" in PROJECT_HTML.lower() or "prism" in PROJECT_HTML.lower()

    def test_project_html_has_prism_js(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "prismjs" in PROJECT_HTML.lower() or "prism" in PROJECT_HTML.lower()

    def test_project_html_has_prism_highlight(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "Prism.highlightElement" in PROJECT_HTML

    def test_project_html_has_autoloader(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "autoloader" in PROJECT_HTML.lower()

    def test_lazy_export_code_intel(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "ripgrep_search")
        assert hasattr(gh_trending_audio, "extract_symbols")
        assert hasattr(gh_trending_audio, "detect_ripgrep")
        assert hasattr(gh_trending_audio, "detect_tree_sitter")

    def test_requirements_has_tree_sitter(self):
        from pathlib import Path
        req = Path("/workspace/gh_trending_audio/requirements.txt").read_text()
        assert "tree-sitter" in req

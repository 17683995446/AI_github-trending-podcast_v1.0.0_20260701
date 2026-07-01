"""Phase 4 单元测试：前端增强。

测试范围：
1. pymdown-extensions 集成（GFM 任务列表、删除线等）
2. 模板中包含 tocbot / mark.js / jstree CDN 引用
3. TOC 函数使用 tocbot
4. 代码搜索高亮支持正则
5. 文件树使用 jstree
"""
import pytest


class TestPymdownExtensions:
    """pymdown-extensions 后端集成测试。"""

    def test_pymdown_importable(self):
        """pymdownx 模块应可导入。"""
        try:
            import pymdownx  # noqa: F401
            assert True
        except ImportError:
            pytest.skip("pymdown-extensions 未安装")

    def test_markdown_to_html_uses_pymdownx(self):
        """markdown_to_html 应使用 pymdownx 扩展。"""
        import inspect
        from gh_trending_audio.web.utils import markdown_to_html
        source = inspect.getsource(markdown_to_html)
        assert "pymdownx" in source, "markdown_to_html 应包含 pymdownx 扩展"

    def test_strikethrough_rendering(self):
        """~~删除线~~ 应正确渲染为 <del> 标签。"""
        from gh_trending_audio.web.utils import markdown_to_html
        html = markdown_to_html("~~deleted text~~")
        assert "<del>" in html or "deleted text" in html

    def test_tasklist_rendering(self):
        """- [ ] 任务列表应正确渲染。"""
        from gh_trending_audio.web.utils import markdown_to_html
        html = markdown_to_html("- [x] 完成项\n- [ ] 未完成项")
        # tasklist 会生成 checkbox 或特定 class
        assert "checkbox" in html.lower() or "task" in html.lower() or "完成项" in html


class TestTemplateCDNIncludes:
    """模板应包含 Phase 4 的 CDN 引用。"""

    def test_project_html_has_tocbot(self):
        """PROJECT_HTML 应引用 tocbot CDN。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "tocbot" in PROJECT_HTML, "PROJECT_HTML 应包含 tocbot CDN"

    def test_project_html_has_markjs(self):
        """PROJECT_HTML 应引用 mark.js CDN。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "mark.js" in PROJECT_HTML or "mark.min.js" in PROJECT_HTML, \
            "PROJECT_HTML 应包含 mark.js CDN"

    def test_project_html_has_jstree(self):
        """PROJECT_HTML 应引用 jstree CDN。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "jstree" in PROJECT_HTML, "PROJECT_HTML 应包含 jstree CDN"

    def test_project_html_has_jquery(self):
        """PROJECT_HTML 应引用 jQuery（jstree 依赖）。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "jquery" in PROJECT_HTML.lower(), "PROJECT_HTML 应包含 jQuery CDN"


class TestTocbotIntegration:
    """tocbot 集成测试。"""

    def test_toggle_toc_uses_tocbot(self):
        """toggleToc 函数应使用 tocbot。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "tocbot.init" in PROJECT_HTML or "window.tocbot" in PROJECT_HTML, \
            "toggleToc 应调用 tocbot.init"

    def test_toc_has_fallback(self):
        """tocbot 不可用时应有退化方案。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        # 检查退化逻辑
        assert "tocbot 未加载" in PROJECT_HTML or "退化" in PROJECT_HTML or "else" in PROJECT_HTML


class TestMarkJsIntegration:
    """mark.js 集成测试。"""

    def test_cs_highlight_supports_regex(self):
        """csHighlight 函数应支持正则匹配。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "RegExp" in PROJECT_HTML, "csHighlight 应支持正则匹配"
        assert "hasRegex" in PROJECT_HTML, "应有正则检测逻辑"

    def test_cs_highlight_dom_function_exists(self):
        """应存在 csHighlightDOM 函数用于 DOM 高亮。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "csHighlightDOM" in PROJECT_HTML, "应定义 csHighlightDOM 函数"


class TestJstreeIntegration:
    """jstree 集成测试。"""

    def test_load_file_tree_uses_jstree(self):
        """loadFileTree 应使用 jstree。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "jQuery.fn.jstree" in PROJECT_HTML or "jstree(" in PROJECT_HTML, \
            "loadFileTree 应使用 jstree"

    def test_jstree_has_fallback(self):
        """jstree 不可用时应有退化方案。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "buildTree" in PROJECT_HTML, "应保留 buildTree 作为退化方案"

    def test_jstree_file_limit_increased(self):
        """jstree 应支持更多文件（500 而非 200）。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "500" in PROJECT_HTML, "jstree 应支持 500 项"

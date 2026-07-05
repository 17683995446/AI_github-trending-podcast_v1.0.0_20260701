"""Phase 6 单元测试：代码质量与体验打磨。

测试范围：
1. Jinja2 模板渲染（替代 f-string 文档模板）
2. 主题 CSS 去重（_THEME_CSS / _COMMON_CSS 共享常量）
3. Fuse.js 模糊搜索集成
4. lucide-icons 图标集成
5. Q&A 聊天 Markdown 渲染（marked.js + hljs）
"""

import os
import inspect
import pytest
from unittest.mock import patch


# ── 测试辅助 ──

def _make_repo(**overrides):
    """构造测试用 RepoInfo。"""
    from gh_trending_audio.github_fetcher import RepoInfo
    defaults = dict(
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
    defaults.update(overrides)
    return RepoInfo(**defaults)


# ═══════════════════════════════════════════════════════════════════
# 1. Jinja2 模板渲染
# ═══════════════════════════════════════════════════════════════════

class TestJinja2TemplateRendering:
    """Jinja2 模板渲染测试。"""

    def test_jinja2_importable(self):
        """Jinja2 库应可导入。"""
        try:
            import jinja2
            assert True
        except ImportError:
            pytest.skip("Jinja2 未安装")

    def test_render_jinja2_method_exists(self):
        """DocumentGenerator 应有 _render_jinja2 静态方法。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        assert hasattr(DocumentGenerator, "_render_jinja2"), \
            "DocumentGenerator 应有 _render_jinja2 方法"

    def test_render_jinja2_returns_string(self):
        """_render_jinja2 应返回渲染后的字符串。"""
        try:
            import jinja2  # noqa: F401
        except ImportError:
            pytest.skip("Jinja2 未安装")
        from gh_trending_audio.document_generator import DocumentGenerator
        repo = _make_repo()
        result = DocumentGenerator._render_jinja2(
            "doc_zh.j2",
            repo=repo,
            topics_str="web、api",
            readme_excerpt="README excerpt",
            arch_mermaid="graph TD\n  A --> B",
            flow_mermaid="graph LR\n  A --> B",
        )
        assert result is not None, "Jinja2 可用时应返回字符串"
        assert isinstance(result, str)
        assert "owner/test-repo" in result
        assert "web、api" in result

    def test_render_jinja2_returns_none_for_missing_template(self):
        """不存在的模板文件应返回 None。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        result = DocumentGenerator._render_jinja2("nonexistent.j2", foo="bar")
        assert result is None, "模板不存在时应返回 None"

    def test_template_files_exist(self):
        """Jinja2 模板文件应存在于 templates/ 目录。"""
        from pathlib import Path
        templates_dir = Path(__file__).parent.parent / "gh_trending_audio" / "templates"
        assert (templates_dir / "doc_zh.j2").exists(), "doc_zh.j2 应存在"
        assert (templates_dir / "doc_en.j2").exists(), "doc_en.j2 应存在"

    def test_template_zh_uses_jinja2(self):
        """_template_zh 源码应调用 _render_jinja2。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        source = inspect.getsource(DocumentGenerator._template_zh)
        assert "_render_jinja2" in source, "_template_zh 应使用 Jinja2"
        assert "doc_zh.j2" in source, "_template_zh 应引用 doc_zh.j2"

    def test_template_en_uses_jinja2(self):
        """_template_en 源码应调用 _render_jinja2。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        source = inspect.getsource(DocumentGenerator._template_en)
        assert "_render_jinja2" in source, "_template_en 应使用 Jinja2"
        assert "doc_en.j2" in source, "_template_en 应引用 doc_en.j2"

    def test_template_zh_renders_correctly(self):
        """中文模板通过 Jinja2 渲染应包含关键内容。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo()
        doc = gen._template_zh(repo, "README content about the project")
        assert "owner/test-repo" in doc.markdown
        assert "1,234" in doc.markdown  # stars 格式化
        assert "Python" in doc.markdown
        assert "MIT" in doc.markdown
        assert "mermaid" in doc.markdown.lower()

    def test_template_en_renders_correctly(self):
        """英文模板通过 Jinja2 渲染应包含关键内容。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="en")
        repo = _make_repo()
        doc = gen._template_en(repo, "README content about the project")
        assert "owner/test-repo" in doc.markdown
        assert "1,234" in doc.markdown
        assert "Python" in doc.markdown
        assert "MIT" in doc.markdown
        assert "mermaid" in doc.markdown.lower()

    def test_no_duplicate_homepage_jinja2(self):
        """Jinja2 渲染时 homepage 不应重复添加。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo(homepage="https://example.org")
        doc = gen._template_zh(repo, "README")
        homepage_lines = [l for l in doc.markdown.split("\n") if "example.org" in l]
        assert len(homepage_lines) == 1, f"homepage 应只出现 1 行，实际 {len(homepage_lines)} 行"

    def test_no_duplicate_homepage_en_jinja2(self):
        """英文 Jinja2 渲染时 homepage 不应重复添加。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="en")
        repo = _make_repo(homepage="https://example.org")
        doc = gen._template_en(repo, "README")
        homepage_lines = [l for l in doc.markdown.split("\n") if "example.org" in l]
        assert len(homepage_lines) == 1, f"homepage 应只出现 1 行，实际 {len(homepage_lines)} 行"

    def test_no_homepage_when_empty(self):
        """homepage 为空时不应添加主页链接。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo(homepage="")
        doc = gen._template_zh(repo, "README")
        assert "项目主页" not in doc.markdown, "homepage 为空时不应有主页链接"

    def test_fallback_to_fstring_when_jinja2_unavailable(self):
        """Jinja2 不可用时应退化到 f-string 模板。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo()
        # 模拟 _render_jinja2 返回 None（Jinja2 不可用或模板缺失）
        with patch.object(DocumentGenerator, '_render_jinja2', return_value=None):
            doc = gen._template_zh(repo, "README content")
            assert "owner/test-repo" in doc.markdown, "f-string 回退应正常工作"
            assert doc.audio_script, "f-string 回退时音频脚本仍应生成"

    def test_audio_script_generated_with_jinja2(self):
        """Jinja2 渲染后音频脚本仍应正确生成。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo()
        doc = gen._template_zh(repo, "This is a README with some content about the project features.")
        assert doc.audio_script, "音频脚本不应为空"
        assert "test-repo" in doc.audio_script, "音频脚本应包含项目名"
        assert "GitHub 趋势榜" in doc.audio_script, "音频脚本应包含播客开场白"


# ═══════════════════════════════════════════════════════════════════
# 2. 主题 CSS 去重
# ═══════════════════════════════════════════════════════════════════

class TestThemeCssDedup:
    """主题 CSS 去重测试。"""

    def test_theme_css_constant_exists(self):
        """_THEME_CSS 共享常量应存在。"""
        from gh_trending_audio.web.templates import _THEME_CSS
        assert _THEME_CSS is not None
        assert isinstance(_THEME_CSS, str)
        assert len(_THEME_CSS) > 0, "_THEME_CSS 不应为空"

    def test_common_css_constant_exists(self):
        """_COMMON_CSS 共享常量应存在。"""
        from gh_trending_audio.web.templates import _COMMON_CSS
        assert _COMMON_CSS is not None
        assert isinstance(_COMMON_CSS, str)
        assert len(_COMMON_CSS) > 0, "_COMMON_CSS 不应为空"

    def test_theme_css_contains_variables(self):
        """_THEME_CSS 应包含 CSS 变量定义。"""
        from gh_trending_audio.web.templates import _THEME_CSS
        assert "--bg" in _THEME_CSS, "应包含 --bg 变量"
        assert "--accent" in _THEME_CSS, "应包含 --accent 变量"
        assert "--border" in _THEME_CSS, "应包含 --border 变量"

    def test_theme_css_contains_multiple_themes(self):
        """_THEME_CSS 应包含多主题定义。"""
        from gh_trending_audio.web.templates import _THEME_CSS
        assert "data-theme" in _THEME_CSS, "应包含 data-theme 选择器"
        assert "light" in _THEME_CSS, "应包含 light 主题"
        assert "dark" in _THEME_CSS or ":root" in _THEME_CSS, "应包含 dark/默认主题"

    def test_common_css_contains_button_styles(self):
        """_COMMON_CSS 应包含按钮和滚动条样式。"""
        from gh_trending_audio.web.templates import _COMMON_CSS
        assert ".btn" in _COMMON_CSS, "应包含 .btn 样式"
        assert "scrollbar" in _COMMON_CSS, "应包含滚动条样式"

    def test_all_html_templates_exist(self):
        """三个 HTML 模板常量应存在。"""
        from gh_trending_audio.web import templates
        assert hasattr(templates, "DASHBOARD_HTML"), "DASHBOARD_HTML 应存在"
        assert hasattr(templates, "PROJECT_HTML"), "PROJECT_HTML 应存在"
        assert hasattr(templates, "PLAYER_HTML"), "PLAYER_HTML 应存在"

    def test_dashboard_has_style_block(self):
        """DASHBOARD_HTML 应包含 <style> 块。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "<style>" in DASHBOARD_HTML, "应包含 <style> 标签"
        assert "</style>" in DASHBOARD_HTML, "应包含 </style> 标签"

    def test_project_has_style_block(self):
        """PROJECT_HTML 应包含 <style> 块。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "<style>" in PROJECT_HTML, "应包含 <style> 标签"
        assert "</style>" in PROJECT_HTML, "应包含 </style> 标签"


# ═══════════════════════════════════════════════════════════════════
# 3. Fuse.js 模糊搜索集成
# ═══════════════════════════════════════════════════════════════════

class TestFuseJsIntegration:
    """Fuse.js 模糊搜索集成测试。"""

    def test_fuse_js_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 Fuse.js CDN 引用。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "fuse.js" in DASHBOARD_HTML.lower(), "应引用 Fuse.js"

    def test_fuse_search_in_render_projects(self):
        """renderProjects 函数应使用 Fuse 搜索（缓存实例后用 _fuseInstance.search）。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert ".search(search)" in DASHBOARD_HTML, "应调用 Fuse 实例的 search 方法"

    def test_fuse_has_fallback(self):
        """Fuse.js 不可用时应有退化方案。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "window.Fuse" in DASHBOARD_HTML, "应检测 window.Fuse 是否存在"

    def test_fuse_config_has_threshold(self):
        """Fuse.js 配置应包含 threshold 参数。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "threshold" in DASHBOARD_HTML, "Fuse.js 应配置 threshold"


# ═══════════════════════════════════════════════════════════════════
# 4. 依赖清理（lucide 死依赖已移除）
# ═══════════════════════════════════════════════════════════════════

class TestLucideIconsIntegration:
    """lucide-icons 集成验证（UI 优化：使用 Lucide SVG 图标替代 Emoji）。"""

    def test_lucide_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 lucide CDN 引用（活跃使用中）。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "lucide" in DASHBOARD_HTML.lower(), "lucide CDN 应存在"
        assert "cdn.jsdelivr.net" in DASHBOARD_HTML, "应使用 jsdelivr CDN"

    def test_lucide_script_tag(self):
        """DASHBOARD_HTML 应包含 lucide.createIcons() 调用。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "createIcons" in DASHBOARD_HTML, "应调用 createIcons()"
        assert "data-lucide" in DASHBOARD_HTML, "应使用 data-lucide 属性"

    def test_lucide_in_player(self):
        """PLAYER_HTML 应包含 lucide CDN 和 data-lucide 属性。"""
        from gh_trending_audio.web.templates import PLAYER_HTML
        assert "lucide" in PLAYER_HTML.lower(), "player 应包含 lucide CDN"
        assert "data-lucide" in PLAYER_HTML, "player 应使用 data-lucide 属性"

    def test_lucide_in_project(self):
        """PROJECT_HTML 应包含 lucide CDN 和 data-lucide 属性。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "lucide" in PROJECT_HTML.lower(), "project 应包含 lucide CDN"
        assert "data-lucide" in PROJECT_HTML, "project 应使用 data-lucide 属性"

    def test_lucide_mutation_observer(self):
        """所有模板应包含 MutationObserver 自动刷新图标。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML, PLAYER_HTML, PROJECT_HTML
        for name, html in [("dashboard", DASHBOARD_HTML), ("player", PLAYER_HTML), ("project", PROJECT_HTML)]:
            assert "MutationObserver" in html, f"{name} 应包含 MutationObserver"


# ═══════════════════════════════════════════════════════════════════
# 5. Q&A 聊天 Markdown 渲染
# ═══════════════════════════════════════════════════════════════════

class TestQAMarkdownRendering:
    """Q&A 聊天 Markdown 渲染测试。"""

    def test_marked_parse_in_project_html(self):
        """PROJECT_HTML 应使用 marked.parse 渲染 Q&A 回答。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "marked.parse" in PROJECT_HTML, "应使用 marked.parse 渲染 Markdown"

    def test_hljs_in_project_html(self):
        """PROJECT_HTML 应使用 hljs.highlightElement 高亮代码。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "hljs" in PROJECT_HTML, "应使用 hljs 高亮代码"

    def test_marked_has_fallback(self):
        """marked 不可用时应有退化方案。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "window.marked" in PROJECT_HTML, "应检测 window.marked 是否存在"

    def test_marked_cdn_in_project_html(self):
        """PROJECT_HTML 应引入 marked.js CDN。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "marked.min.js" in PROJECT_HTML, "应引入 marked.min.js CDN"

    def test_qa_bubble_uses_innerhtml(self):
        """Q&A 回答应使用 innerHTML 渲染（而非 textContent）。"""
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "innerHTML" in PROJECT_HTML, "应使用 innerHTML 渲染 Markdown HTML"


# ═══════════════════════════════════════════════════════════════════
# 6. 端到端集成测试
# ═══════════════════════════════════════════════════════════════════

class TestPhase6Integration:
    """Phase 6 端到端集成测试。"""

    def test_generate_zh_document_full_pipeline(self):
        """中文模板模式完整流程应正常工作。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh", use_llm=False)
        repo = _make_repo()
        doc = gen.generate(repo, "## Features\n\n- Fast and lightweight\n- Easy to use\n- Well documented")
        assert doc.markdown, "Markdown 不应为空"
        assert doc.audio_script, "音频脚本不应为空"
        assert "mermaid" in doc.markdown.lower(), "应包含 Mermaid 图"
        assert "owner/test-repo" in doc.markdown

    def test_generate_en_document_full_pipeline(self):
        """英文模板模式完整流程应正常工作。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="en", use_llm=False)
        repo = _make_repo()
        doc = gen.generate(repo, "## Features\n\n- Fast and lightweight\n- Easy to use")
        assert doc.markdown, "Markdown 不应为空"
        assert doc.audio_script, "音频脚本不应为空"
        assert "mermaid" in doc.markdown.lower(), "应包含 Mermaid 图"

    def test_document_save(self):
        """AudioDocument.save 应正确写入文件。"""
        import tempfile
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo()
        doc = gen._template_zh(repo, "README content")
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "test.md")
            script_path = os.path.join(tmpdir, "test_script.txt")
            doc.save(md_path, script_path)
            assert os.path.exists(md_path), "Markdown 文件应存在"
            assert os.path.exists(script_path), "脚本文件应存在"
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "owner/test-repo" in content

    def test_jinja2_template_has_mermaid_blocks(self):
        """Jinja2 模板渲染后应包含 mermaid 代码块。"""
        from gh_trending_audio.document_generator import DocumentGenerator
        gen = DocumentGenerator(language="zh")
        repo = _make_repo()
        doc = gen._template_zh(repo, "README")
        assert "```mermaid" in doc.markdown, "应包含 mermaid 代码块"
        # 应有至少两个 mermaid 块（架构图 + 流程图）
        mermaid_count = doc.markdown.count("```mermaid")
        assert mermaid_count >= 2, f"应有至少 2 个 mermaid 块，实际 {mermaid_count}"

    def test_requirements_has_jinja2(self):
        """requirements.txt 应包含 Jinja2。"""
        from pathlib import Path
        req_path = Path(__file__).parent.parent / "requirements.txt"
        content = req_path.read_text(encoding="utf-8")
        assert "Jinja2" in content, "requirements.txt 应包含 Jinja2"

    def test_all_phase6_dependencies_in_requirements(self):
        """requirements.txt 应包含所有依赖分组且与 pyproject.toml 对齐。"""
        from pathlib import Path
        req_path = Path(__file__).parent.parent / "requirements.txt"
        content = req_path.read_text(encoding="utf-8")
        # 验证依赖分组结构（阶段2规范化后以 pyproject.toml 对齐标注）
        assert "pyproject.toml" in content, "requirements.txt 应标注与 pyproject.toml 对齐"
        assert "Jinja2" in content, "requirements.txt 应包含 Jinja2"
        assert "edge-tts" in content, "requirements.txt 应包含 edge-tts"
        assert "openai" in content, "requirements.txt 应包含 openai"
        # 验证版本上限（规范化要求）
        assert "<3.0" in content or "<4.0" in content, "依赖应有版本上限"

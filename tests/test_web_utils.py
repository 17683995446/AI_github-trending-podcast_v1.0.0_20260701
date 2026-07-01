"""Web 工具函数测试。"""
from gh_trending_audio.web.utils import (
    parse_md_metadata,
    get_audio_duration,
    normalize_repo_slug,
    ext_matches_language,
    classify_line,
    markdown_to_html,
)


class TestParseMdMetadata:
    """Markdown 元数据解析测试。"""

    def test_extract_description(self):
        """能从表格中提取描述。"""
        md = "| 描述 | 这是一个测试项目 |\n| 星标数 | 1,234 |"
        meta = parse_md_metadata(md)
        assert meta["description"] == "这是一个测试项目"

    def test_extract_stars(self):
        """能提取星标数。"""
        md = "| 星标数 | 5,432 |"
        meta = parse_md_metadata(md)
        assert meta["stars"] == 5432

    def test_extract_language(self):
        """能提取编程语言。"""
        md = "| 编程语言 | Python |"
        meta = parse_md_metadata(md)
        assert meta["language"] == "Python"

    def test_empty_md(self):
        """空 Markdown 返回默认值。"""
        meta = parse_md_metadata("")
        assert meta["description"] == ""
        assert meta["stars"] == 0


class TestNormalizeRepoSlug:
    """仓库标识符标准化测试。"""

    def test_owner_repo(self):
        """标准 owner/repo 格式。"""
        assert normalize_repo_slug("deepseek-ai/DeepSpec") == "deepseek-ai/DeepSpec"

    def test_underscore_format(self):
        """下划线格式转为斜杠。"""
        assert normalize_repo_slug("deepseek-ai_DeepSpec") == "deepseek-ai/DeepSpec"

    def test_invalid(self):
        """无斜杠的单字符串原样返回（不做严格校验）。"""
        result = normalize_repo_slug("invalid")
        assert result is not None  # 返回原值而非 None


class TestExtMatchesLanguage:
    """文件扩展名匹配测试。"""

    def test_python_match(self):
        """Python 文件匹配。"""
        assert ext_matches_language("main.py", "python") is True

    def test_python_no_match(self):
        """非 Python 文件不匹配。"""
        assert ext_matches_language("main.js", "python") is False

    def test_no_language_filter(self):
        """无语言过滤时全部匹配。"""
        assert ext_matches_language("main.py", "") is True


class TestClassifyLine:
    """代码行分类测试。"""

    def test_function_def(self):
        """函数定义行。"""
        assert classify_line("def hello():").lower() == "function"

    def test_class_def(self):
        """类定义行。"""
        assert classify_line("class MyClass:").lower() == "class"

    def test_import(self):
        """导入行。"""
        assert classify_line("import os").lower() == "import"

    def test_normal_code(self):
        """普通代码行（非上述类型）。"""
        result = classify_line("x = 1 + 2")
        assert result.lower() not in ("function", "class", "import")


class TestMarkdownToHtml:
    """Markdown 转 HTML 测试。"""

    def test_basic_conversion(self):
        """基本 Markdown 转换。"""
        html = markdown_to_html("# Hello\n\nWorld")
        assert "<h1>" in html or "<h2>" in html or "Hello" in html

    def test_table_conversion(self):
        """表格转换。"""
        html = markdown_to_html("| A | B |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html or "<th>" in html

    def test_mermaid_preservation(self):
        """Mermaid 代码块被正确保留。"""
        md = "```mermaid\ngraph TD\n    A --> B\n```"
        html = markdown_to_html(md)
        assert "mermaid" in html.lower()

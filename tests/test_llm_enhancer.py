"""LLM 增强器测试（不调用真实 API）。"""
import pytest
from gh_trending_audio.llm_enhancer import LLMEnhancer


class TestLLMEnhancerInit:
    """LLM 增强器初始化测试。"""

    def test_default_style(self):
        """默认风格为 dialogue。"""
        enhancer = LLMEnhancer()
        assert enhancer.style == "dialogue"

    def test_custom_style(self):
        """自定义风格生效。"""
        enhancer = LLMEnhancer(style="debate")
        assert enhancer.style == "debate"

    def test_invalid_style_fallback(self):
        """无效风格回退到 dialogue。"""
        enhancer = LLMEnhancer(style="nonexistent")
        assert enhancer.style == "dialogue"

    def test_styles_accessible(self):
        """STYLES 字典可通过类访问。"""
        assert "dialogue" in LLMEnhancer.STYLES
        assert "debate" in LLMEnhancer.STYLES

    def test_language_setting(self):
        """语言设置正确。"""
        enhancer = LLMEnhancer(language="en")
        assert enhancer.language == "en"


class TestMermaidExtraction:
    """Mermaid 图表提取测试。"""

    def setup_method(self):
        self.enhancer = LLMEnhancer()

    def test_extract_fenced_mermaid(self):
        """从 ```mermaid 围栏中提取。"""
        analysis = "```mermaid\ngraph TD\n    A --> B\n```"
        mermaid = self.enhancer._extract_mermaid(analysis)
        assert mermaid is not None
        assert "graph TD" in mermaid
        assert "A --> B" in mermaid

    def test_extract_no_mermaid(self):
        """无 Mermaid 内容返回 None。"""
        analysis = "这是一个普通的技术分析，没有图表。"
        mermaid = self.enhancer._extract_mermaid(analysis)
        assert mermaid is None or mermaid == ""

    def test_insert_mermaid_into_md(self):
        """Mermaid 插入到 Markdown 正确位置。"""
        md = "# 项目\n\n## 核心亮点\n- 亮点1\n\n## 创新点\n- 创新1"
        mermaid = "graph TD\n    A --> B"
        result = self.enhancer._insert_mermaid_into_md(md, mermaid)
        assert "```mermaid" in result
        assert "## 架构图" in result
        # 架构图在核心亮点之后
        assert result.index("架构图") > result.index("核心亮点")

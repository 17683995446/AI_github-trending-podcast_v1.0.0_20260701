"""Prompt 模板测试。"""
from gh_trending_audio.prompts import (
    system_prompt,
    dialogue_prompt,
    comparison_system_prompt,
    onboarding_user_prompt,
)


class TestSystemPrompt:
    """System prompt 生成测试。"""

    def test_dialogue_zh(self):
        """中文对话风格 prompt 包含关键要素。"""
        p = system_prompt("dialogue", "zh")
        assert "主持人" in p
        assert "技术专家" in p
        assert "===AUDIO===" in p
        assert "A:" in p or "A：" in p

    def test_debate_zh(self):
        """辩论风格 prompt 包含对抗结构。"""
        p = system_prompt("debate", "zh")
        assert "辩论" in p
        assert "质疑" in p or "反驳" in p

    def test_news_zh(self):
        """新闻风格 prompt 要求正式语气。"""
        p = system_prompt("news", "zh")
        assert "新闻" in p or "主播" in p
        assert "正式" in p

    def test_story_zh(self):
        """故事风格 prompt 有叙事弧线。"""
        p = system_prompt("story", "zh")
        assert "故事" in p or "旁白" in p

    def test_english_prompt(self):
        """英文 prompt 也能生成。"""
        p = system_prompt("dialogue", "en")
        assert "podcast" in p.lower() or "dialogue" in p.lower()

    def test_unknown_style_fallback(self):
        """未知风格回退到 dialogue。"""
        p = system_prompt("nonexistent", "zh")
        assert "主持人" in p


class TestComparisonPrompt:
    """对比播客 prompt 测试。"""

    def test_comparison_system_prompt(self):
        """对比 prompt 包含对比维度。"""
        p = comparison_system_prompt("dialogue", "zh")
        assert "对比" in p or "比较" in p
        assert "定位" in p or "架构" in p


class TestOnboardingPrompt:
    """入门指南 prompt 测试。"""

    def test_beginner_audience(self):
        """新手受众包含安装步骤。"""
        p = onboarding_user_prompt(None, "技术分析内容", "beginner", "zh")
        assert len(p) > 100

    def test_developer_audience(self):
        """开发者受众包含 API 相关内容。"""
        p = onboarding_user_prompt(None, "技术分析内容", "developer", "zh")
        assert len(p) > 100

    def test_architect_audience(self):
        """架构师受众包含架构相关内容。"""
        p = onboarding_user_prompt(None, "技术分析内容", "architect", "zh")
        assert len(p) > 100

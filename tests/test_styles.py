"""播客风格定义测试。"""
import pytest
from gh_trending_audio.styles import STYLES, PodcastStyle, SpeakerRole, get_style


class TestStyles:
    """风格定义完整性测试。"""

    EXPECTED_STYLES = ["dialogue", "debate", "interview", "news", "story"]

    def test_all_styles_present(self):
        """5 种风格全部存在。"""
        for key in self.EXPECTED_STYLES:
            assert key in STYLES, f"缺少风格: {key}"

    def test_style_structure(self):
        """每个风格有完整的结构和角色定义。"""
        for key, style in STYLES.items():
            assert isinstance(style, PodcastStyle)
            assert style.name, f"{key} 缺少 name"
            assert style.desc, f"{key} 缺少 desc"
            assert "A" in style.speakers, f"{key} 缺少说话人 A"
            assert "B" in style.speakers, f"{key} 缺少说话人 B"
            assert style.speakers["A"].role, f"{key} 的 A 缺少 role"
            assert style.speakers["B"].trait, f"{key} 的 B 缺少 trait"

    def test_get_style_valid(self):
        """get_style 返回正确的风格。"""
        style = get_style("debate")
        assert style.name == "辩论式"

    def test_get_style_fallback(self):
        """未知风格回退到 dialogue。"""
        style = get_style("nonexistent")
        assert style.name == "双人对话"

    def test_debate_has_adversarial_roles(self):
        """辩论式的角色有对抗性。"""
        style = STYLES["debate"]
        assert "支持" in style.speakers["A"].role or "看好" in style.speakers["A"].trait
        assert "质疑" in style.speakers["B"].role or "问题" in style.speakers["B"].trait

    def test_interview_uses_first_person(self):
        """采访式的 B 角色用第一人称。"""
        style = STYLES["interview"]
        assert "第一人称" in style.speakers["B"].trait or "作者" in style.speakers["B"].role

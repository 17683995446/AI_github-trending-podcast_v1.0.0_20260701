"""
styles.py —— 播客风格定义和配置

把原本散落在 LLMEnhancer.STYLES 字典中的风格定义抽取为独立的数据类，
让结构更清晰、便于在 prompts.py / cli.py / web_dashboard 等模块间复用。

设计原则：
  - 纯数据，无副作用，无 I/O
  - 使用 dataclass 让字段语义显式化
  - STYLES 保留与原字典相同的键（dialogue / debate / interview / news / story）
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerRole:
    """对话中单个说话者的角色与特征。"""

    role: str   # 角色名，如「主持人」「技术专家」
    trait: str  # 性格/语气特征，用于引导 LLM 的台词风格


@dataclass(frozen=True)
class PodcastStyle:
    """一种播客风格的完整定义。"""

    name: str                       # 风格中文名（如「双人对话」）
    desc: str                       # 风格简述
    speakers: dict[str, SpeakerRole]  # 说话人配置，键为 "A" / "B"


# ── 5 种播客风格定义 ──────────────────────────────────────────────
STYLES: dict[str, PodcastStyle] = {
    "dialogue": PodcastStyle(
        name="双人对话",
        desc="主持人与专家对谈，自然有节奏",
        speakers={
            "A": SpeakerRole(role="主持人", trait="活泼好奇，负责提问引导"),
            "B": SpeakerRole(role="技术专家", trait="沉稳专业，负责讲解干货"),
        },
    ),
    "debate": PodcastStyle(
        name="辩论式",
        desc="正反方就项目优缺点展开辩论",
        speakers={
            "A": SpeakerRole(role="支持方", trait="看好项目前景，强调创新点和优势"),
            "B": SpeakerRole(role="质疑方", trait="挑刺质疑，指出局限、风险和改进空间"),
        },
    ),
    "interview": PodcastStyle(
        name="采访式",
        desc="记者采访项目作者，深挖设计决策",
        speakers={
            "A": SpeakerRole(role="记者", trait="追问设计动机和技术选型原因"),
            "B": SpeakerRole(role="项目作者", trait="以第一人称分享开发思路和踩坑经验"),
        },
    ),
    "news": PodcastStyle(
        name="新闻播报",
        desc="双主播新闻联播式报道项目动态",
        speakers={
            "A": SpeakerRole(role="主播甲", trait="播报新闻事实，语气正式"),
            "B": SpeakerRole(role="主播乙", trait="补充评论和分析，语气沉稳"),
        },
    ),
    "story": PodcastStyle(
        name="故事式",
        desc="以故事叙述方式讲述项目的前世今生",
        speakers={
            "A": SpeakerRole(role="旁白", trait="叙述背景和情节发展"),
            "B": SpeakerRole(role="主角", trait="以开发者视角讲述心路历程"),
        },
    ),
}


def get_style(style: str) -> PodcastStyle:
    """按名称获取风格定义，未知风格回退到 dialogue。"""
    return STYLES.get(style, STYLES["dialogue"])

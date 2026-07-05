"""抽象接口与注册机制（Phase 5: 可扩展化）。

提供 TTS 引擎、播客风格的抽象基类和注册器，
新增引擎/风格只需实现接口 + 注册，无需修改 if-elif 链。

使用方式：
    # 注册新 TTS 引擎
    @register_tts_engine("my-engine")
    class MyTTSEngine(TTSBackend):
        def synthesize(self, text, output_path, **kwargs): ...

    # 注册新播客风格
    @register_style("my-style")
    def my_style() -> PodcastStyle:
        return PodcastStyle(...)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from .exceptions import ConfigError

__all__ = [
    # 播客风格
    "SpeakerRole",
    "PodcastStyle",
    "register_style",
    "get_style",
    "list_styles",
    "get_all_styles",
    # TTS 引擎
    "TTSBackend",
    "register_tts_engine",
    "get_tts_engine",
    "get_tts_engine_priority",
    "list_tts_engines",
    "get_tts_engines_sorted_by_priority",
    "get_available_engines",
    # LLM 后端
    "LLMBackend",
    "register_llm_backend",
    "get_llm_backend",
    "get_llm_backend_priority",
    "list_llm_backends",
    "get_llm_backends_sorted_by_priority",
    "get_available_llm_backends",
    "get_auto_llm_backend",
]


# ═══════════════════════════════════════════════════════════════════
# 播客风格注册器
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SpeakerRole:
    """播客角色定义。

    Attributes:
        role: 角色名（如 "主持人"、"技术专家"）
        trait: 角色特质描述（如 "热情引导"、"深度分析"）
    """

    role: str
    trait: str


@dataclass
class PodcastStyle:
    """播客风格定义。

    Attributes:
        name: 风格中文显示名（如 "双人对话"、"辩论式"）
        desc: 风格简述
        speakers: 角色映射，键为 "A"/"B"
        label_en: 英文显示名（可选）
        identifier: 风格标识符（如 "dialogue"），可选用于注册键
    """

    name: str
    desc: str = ""
    speakers: dict[str, SpeakerRole] = field(default_factory=dict)
    label_en: str = ""
    identifier: str = ""


# 风格注册表
_STYLE_REGISTRY: dict[str, PodcastStyle] = {}


def register_style(name: str) -> Callable:
    """装饰器：注册播客风格。

    Args:
        name: 风格标识符

    Example:
        @register_style("debate")
        def create_debate_style() -> PodcastStyle:
            return PodcastStyle(name="debate", ...)
    """
    def decorator(func: Callable[[], PodcastStyle]) -> Callable[[], PodcastStyle]:
        style = func()
        _STYLE_REGISTRY[name] = style
        return func
    return decorator


def get_style(name: str) -> Optional[PodcastStyle]:
    """获取已注册的播客风格。

    Args:
        name: 风格标识符

    Returns:
        PodcastStyle 实例，未注册返回 None
    """
    return _STYLE_REGISTRY.get(name)


def list_styles() -> list[str]:
    """列出所有已注册的风格标识符。"""
    return list(_STYLE_REGISTRY.keys())


def get_all_styles() -> dict[str, PodcastStyle]:
    """获取所有已注册的风格。"""
    return dict(_STYLE_REGISTRY)


# ═══════════════════════════════════════════════════════════════════
# TTS 引擎注册器
# ═══════════════════════════════════════════════════════════════════

class TTSBackend(ABC):
    """TTS 引擎抽象基类。

    所有 TTS 引擎实现此接口，通过 ``register_tts_engine`` 注册后，
    可被 TTSEngine 自动发现和使用。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """引擎标识符（如 "edge-tts"、"siliconflow"）。"""
        ...

    @property
    @abstractmethod
    def requires_network(self) -> bool:
        """是否需要网络连接。"""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str = "",
        rate: str = "+0%",
        volume: str = "+0%",
        language: str = "zh",
    ) -> str:
        """将文本合成为音频文件。

        Args:
            text: 待合成文本
            output_path: 输出文件路径
            voice: 音色名称
            rate: 语速（如 "+10%"）
            volume: 音量（如 "+0%"）
            language: 语言 zh/en

        Returns:
            实际输出文件路径
        """
        ...

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """检查引擎是否可用（依赖已安装、可联网等）。"""
        ...


# TTS 引擎注册表
# 每个条目存储 {"class": 引擎类, "priority": 优先级}，priority 越大越优先（auto 模式）
_TTS_REGISTRY: dict[str, dict] = {}


def register_tts_engine(name: str, priority: int = 0) -> Callable:
    """装饰器：注册 TTS 引擎。

    Args:
        name: 引擎标识符
        priority: 优先级（数字越大优先级越高，auto 模式按降序选择）。
            不指定时默认为 0，保持向后兼容。

    Example:
        @register_tts_engine("my-engine", priority=100)
        class MyEngine(TTSBackend):
            ...
    """
    def decorator(cls: type[TTSBackend]) -> type[TTSBackend]:
        _TTS_REGISTRY[name] = {"class": cls, "priority": priority}
        return cls
    return decorator


def get_tts_engine(name: str) -> Optional[type[TTSBackend]]:
    """获取已注册的 TTS 引擎类。

    Args:
        name: 引擎标识符

    Returns:
        引擎类，未注册返回 None
    """
    info = _TTS_REGISTRY.get(name)
    return info["class"] if info else None


def get_tts_engine_priority(name: str) -> int:
    """获取已注册 TTS 引擎的优先级（未注册返回 0）。"""
    info = _TTS_REGISTRY.get(name)
    return info.get("priority", 0) if info else 0


def list_tts_engines() -> list[str]:
    """列出所有已注册的引擎标识符。"""
    return list(_TTS_REGISTRY.keys())


def get_tts_engines_sorted_by_priority() -> list[tuple[str, type[TTSBackend]]]:
    """按 priority 降序返回所有已注册 TTS 引擎的 ``(name, cls)`` 列表。

    auto 模式据此顺序尝试可用引擎，新增引擎自带 priority 即可参与自动选择，
    无需修改任何硬编码列表（开闭原则）。
    """
    items = sorted(
        _TTS_REGISTRY.items(),
        key=lambda kv: kv[1].get("priority", 0),
        reverse=True,
    )
    return [(name, info["class"]) for name, info in items]


def get_available_engines() -> dict[str, bool]:
    """列出所有引擎及其可用性状态（按 priority 降序排列）。

    Returns:
        {引擎名: 是否可用} 字典
    """
    return {
        name: info["class"].is_available()
        for name, info in sorted(
            _TTS_REGISTRY.items(),
            key=lambda kv: kv[1].get("priority", 0),
            reverse=True,
        )
    }


# ═══════════════════════════════════════════════════════════════════
# LLM 后端注册器（阶段4: 与 TTS 注册器对称设计）
# ═══════════════════════════════════════════════════════════════════

class LLMBackend(ABC):
    """LLM 后端抽象基类。

    所有 LLM 后端实现此接口，通过 ``register_llm_backend`` 注册后，
    可被 ``LLMEnhancer`` 自动发现和使用。

    后端负责封装客户端创建逻辑（OpenAI 兼容 API、Ollama 直连等），
    使 ``LLMEnhancer`` 无需关心具体 LLM 供应商。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """后端标识符（如 "openai"、"ollama"）。"""
        ...

    @property
    @abstractmethod
    def requires_network(self) -> bool:
        """是否需要网络连接。"""
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """当前使用的模型名称。"""
        ...

    @property
    @abstractmethod
    def api_key(self) -> str:
        """API Key（Ollama 等本地后端可为占位符）。"""
        ...

    @property
    @abstractmethod
    def base_url(self) -> str:
        """API 基础 URL。"""
        ...

    @abstractmethod
    def get_client(self):
        """创建并返回 OpenAI 兼容客户端实例。

        Returns:
            OpenAI 客户端对象（支持 ``chat.completions.create`` 接口）
        """
        ...

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """检查后端是否可用（依赖已安装、可联网等）。"""
        ...


# LLM 后端注册表
# 每个条目存储 {"class": 后端类, "priority": 优先级}，priority 越大越优先（auto 模式）
_LLM_REGISTRY: dict[str, dict] = {}


def register_llm_backend(name: str, priority: int = 0) -> Callable:
    """装饰器：注册 LLM 后端。

    Args:
        name: 后端标识符
        priority: 优先级（数字越大优先级越高，auto 模式按降序选择）。
            不指定时默认为 0，保持向后兼容。

    Example:
        @register_llm_backend("my-llm", priority=100)
        class MyLLMBackend(LLMBackend):
            ...
    """
    def decorator(cls: type[LLMBackend]) -> type[LLMBackend]:
        _LLM_REGISTRY[name] = {"class": cls, "priority": priority}
        return cls
    return decorator


def get_llm_backend(name: str) -> Optional[type[LLMBackend]]:
    """获取已注册的 LLM 后端类。

    Args:
        name: 后端标识符

    Returns:
        后端类，未注册返回 None
    """
    info = _LLM_REGISTRY.get(name)
    return info["class"] if info else None


def get_llm_backend_priority(name: str) -> int:
    """获取已注册 LLM 后端的优先级（未注册返回 0）。"""
    info = _LLM_REGISTRY.get(name)
    return info.get("priority", 0) if info else 0


def list_llm_backends() -> list[str]:
    """列出所有已注册的 LLM 后端标识符。"""
    return list(_LLM_REGISTRY.keys())


def get_llm_backends_sorted_by_priority() -> list[tuple[str, type[LLMBackend]]]:
    """按 priority 降序返回所有已注册 LLM 后端的 ``(name, cls)`` 列表。

    auto 模式据此顺序尝试可用后端，新增后端自带 priority 即可参与自动选择，
    无需修改任何硬编码列表（开闭原则）。
    """
    items = sorted(
        _LLM_REGISTRY.items(),
        key=lambda kv: kv[1].get("priority", 0),
        reverse=True,
    )
    return [(name, info["class"]) for name, info in items]


def get_available_llm_backends() -> dict[str, bool]:
    """列出所有 LLM 后端及其可用性状态（按 priority 降序排列）。

    Returns:
        {后端名: 是否可用} 字典
    """
    return {
        name: info["class"].is_available()
        for name, info in sorted(
            _LLM_REGISTRY.items(),
            key=lambda kv: kv[1].get("priority", 0),
            reverse=True,
        )
    }


# [Deprecated] LLM 后端优先级（auto 模式按此顺序尝试）
# 已被后端自注册的 ``priority`` 参数取代（见 register_llm_backend），
# 保留此列表仅为向后兼容，新后端应通过 ``priority`` 参数声明优先级。
_LLM_BACKEND_PRIORITY: list[str] = ["openai", "ollama"]


def get_auto_llm_backend() -> Optional[LLMBackend]:
    """按优先级自动选择可用的 LLM 后端。

    遍历所有已注册后端（按各自 ``priority`` 降序），返回第一个 ``is_available()``
    且可成功实例化的后端。不再依赖硬编码的 ``_LLM_BACKEND_PRIORITY`` 列表，
    新增后端只需在注册时声明 ``priority`` 即可参与 auto 选择（开闭原则）。

    Returns:
        第一个可用的 LLMBackend 实例，全部不可用返回 None
    """
    for _name, cls in get_llm_backends_sorted_by_priority():
        if cls.is_available():
            try:
                return cls()
            except (ImportError, RuntimeError, ConfigError):
                pass
    return None


# ═══════════════════════════════════════════════════════════════════
# 注册内置风格
# ═══════════════════════════════════════════════════════════════════

@register_style("dialogue")
def _register_dialogue() -> PodcastStyle:
    """注册对话风格。"""
    return PodcastStyle(
        name="双人对话",
        desc="主持人与专家对谈，自然有节奏",
        speakers={
            "A": SpeakerRole(role="主持人", trait="活泼好奇，负责提问引导"),
            "B": SpeakerRole(role="技术专家", trait="沉稳专业，负责讲解干货"),
        },
        label_en="Dialogue",
        identifier="dialogue",
    )


@register_style("debate")
def _register_debate() -> PodcastStyle:
    """注册辩论风格。"""
    return PodcastStyle(
        name="辩论式",
        desc="正反方就项目优缺点展开辩论",
        speakers={
            "A": SpeakerRole(role="支持方", trait="看好项目前景，强调创新点和优势"),
            "B": SpeakerRole(role="质疑方", trait="挑刺质疑，指出局限、风险和改进空间"),
        },
        label_en="Debate",
        identifier="debate",
    )


@register_style("interview")
def _register_interview() -> PodcastStyle:
    """注册访谈风格。"""
    return PodcastStyle(
        name="采访式",
        desc="记者采访项目作者，深挖设计决策",
        speakers={
            "A": SpeakerRole(role="记者", trait="追问设计动机和技术选型原因"),
            "B": SpeakerRole(role="项目作者", trait="以第一人称分享开发思路和踩坑经验"),
        },
        label_en="Interview",
        identifier="interview",
    )


@register_style("news")
def _register_news() -> PodcastStyle:
    """注册新闻播报风格。"""
    return PodcastStyle(
        name="新闻播报",
        desc="双主播新闻联播式报道项目动态",
        speakers={
            "A": SpeakerRole(role="主播甲", trait="播报新闻事实，语气正式"),
            "B": SpeakerRole(role="主播乙", trait="补充评论和分析，语气沉稳"),
        },
        label_en="News Report",
        identifier="news",
    )


@register_style("story")
def _register_story() -> PodcastStyle:
    """注册故事风格。"""
    return PodcastStyle(
        name="故事式",
        desc="以故事叙述方式讲述项目的前世今生",
        speakers={
            "A": SpeakerRole(role="旁白", trait="叙述背景和情节发展"),
            "B": SpeakerRole(role="主角", trait="以开发者视角讲述心路历程"),
        },
        label_en="Story",
        identifier="story",
    )

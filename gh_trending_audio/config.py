"""
config.py —— 集中配置管理（Phase 6: 配置对象化）

所有配置优先从环境变量读取，环境变量未设置时使用此处的默认值。
修改默认值后无需再手动设置环境变量。

Phase 6 改进：
  - 引入 ``AppConfig`` dataclass 封装所有配置，支持依赖注入
  - 保留模块级常量以兼容现有 ``from .config import XXX`` 调用
  - 敏感信息（API Key、Token）通过 .env 文件或环境变量设置

安全提示：敏感信息（API Key、Token）请通过 .env 文件或环境变量设置，
切勿硬编码在源码中。
"""

import os
from dataclasses import dataclass, field

from .constants import GITHUB_API_URL

try:
    from dotenv import load_dotenv
    load_dotenv()  # 从 .env 文件加载环境变量
except ImportError:
    pass  # python-dotenv 未安装时退化到纯环境变量


# ═══════════════════════════════════════════════════════════════════
# 配置对象（Phase 6: 可注入、可测试）
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LLMConfig:
    """LLM 配置。

    Attributes:
        api_key: API 密钥（从环境变量或 .env 读取）
        base_url: API 基础 URL
        model: 模型名称
    """

    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "THUDM/GLM-4-9B-0414"


@dataclass(frozen=True)
class TTSConfig:
    """TTS 配置。

    Attributes:
        engine: 引擎选择（auto/siliconflow/edge-tts/espeak-ng）
        rate: 语速（如 "+10%"）
        api_key: TTS API 密钥（默认复用 LLM_API_KEY）
        base_url: TTS API 基础 URL
        model: TTS 模型名称
        voice_zh: 中文音色
        voice_en: 英文音色
    """

    engine: str = "auto"
    rate: str = "+0%"
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "FunAudioLLM/CosyVoice2-0.5B"
    voice_zh: str = "FunAudioLLM/CosyVoice2-0.5B:alex"
    voice_en: str = "FunAudioLLM/CosyVoice2-0.5B:alex"


@dataclass(frozen=True)
class GitHubConfig:
    """GitHub 配置。

    Attributes:
        token: GitHub 个人访问令牌
        api_url: GitHub API 基础 URL
    """

    token: str = ""
    api_url: str = GITHUB_API_URL


@dataclass(frozen=True)
class AppConfig:
    """应用全局配置（Phase 6: 依赖注入入口）。

    所有子配置聚合在此对象中，方便传递和测试。

    Attributes:
        llm: LLM 配置
        tts: TTS 配置
        github: GitHub 配置
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)


def _validate_config(config: AppConfig) -> None:
    """验证配置项的格式和必填性。

    验证策略为**非破坏性**：只对明确的格式错误抛出 ``ConfigError``，
    对可能的问题（如语速格式不规范、可选 Token 缺失）仅记录 warning/debug 日志，
    不阻断配置加载流程。

    Args:
        config: 已加载的配置对象。

    Raises:
        ConfigError: 配置项格式错误或必填项缺失时。
    """
    from .exceptions import ConfigError
    from .logging_config import get_logger

    logger = get_logger(__name__)

    # LLM_BASE_URL 格式验证（如果提供了API Key）
    if config.llm.api_key and config.llm.base_url:
        if not config.llm.base_url.startswith(("http://", "https://")):
            raise ConfigError(
                f"LLM_BASE_URL 必须以 http:// 或 https:// 开头，当前值: {config.llm.base_url}"
            )

    # TTS_RATE 格式验证（如果提供了）
    if config.tts.rate:
        rate = config.tts.rate.strip()
        if not (rate.endswith("%") and rate[:-1].lstrip("+-").isdigit()):
            logger.warning("TTS_RATE 格式可能不正确（期望如 '+0%'/'-10%'），当前值: %s", rate)

    # GitHub Token 警告（非必填，但缺失时会有速率限制）
    if not config.github.token:
        logger.debug("未设置 GITHUB_TOKEN，GitHub API 调用将受限于匿名速率（60次/小时）")


def load_config() -> AppConfig:
    """从环境变量加载应用配置。

    Returns:
        AppConfig 实例，所有字段从环境变量读取

    Raises:
        ConfigError: 配置项存在明确格式错误时（如 LLM_BASE_URL 非 http(s) 协议）。
    """
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_base_url = os.environ.get("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
    llm_model = os.environ.get("LLM_MODEL", "THUDM/GLM-4-9B-0414")

    # TTS 凭证：仅在 LLM 提供商同为硅基流动时自动复用 LLM_API_KEY。
    # 如果用户用 DeepSeek/OpenAI 等非硅基流动 LLM，TTS_API_KEY 默认为空，
    # 引擎会自动降级到免费的 edge-tts，而不是拿错误的 key 去请求 siliconflow。
    tts_api_key = os.environ.get("TTS_API_KEY", "")
    tts_base_url = os.environ.get("TTS_BASE_URL", "https://api.siliconflow.cn/v1")
    if not tts_api_key and "siliconflow" in llm_base_url:
        # LLM 和 TTS 同为硅基流动，安全复用
        tts_api_key = llm_api_key
        tts_base_url = llm_base_url

    config = AppConfig(
        llm=LLMConfig(
            api_key=llm_api_key,
            base_url=llm_base_url,
            model=llm_model,
        ),
        tts=TTSConfig(
            engine=os.environ.get("TTS_ENGINE", "auto"),
            rate=os.environ.get("TTS_RATE", "+0%"),
            api_key=tts_api_key,
            base_url=tts_base_url,
            model=os.environ.get("TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B"),
            voice_zh=os.environ.get("TTS_VOICE_ZH", "FunAudioLLM/CosyVoice2-0.5B:alex"),
            voice_en=os.environ.get("TTS_VOICE_EN", "FunAudioLLM/CosyVoice2-0.5B:alex"),
        ),
        github=GitHubConfig(
            token=os.environ.get("GITHUB_TOKEN", ""),
            api_url=os.environ.get("GITHUB_API_URL", GITHUB_API_URL),
        ),
    )

    # 验证配置（非破坏性：仅对明确格式错误抛异常）
    _validate_config(config)
    return config


# ═══════════════════════════════════════════════════════════════════
# 模块级常量（兼容现有 from .config import XXX 调用）
# ═══════════════════════════════════════════════════════════════════

# 延迟加载：首次访问时才读取环境变量，便于测试注入
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """获取当前应用配置对象（延迟加载，支持测试重置）。

    Returns:
        AppConfig 实例
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """重置配置缓存（测试用：修改环境变量后重新加载）。"""
    global _config
    _config = None


# ── 兼容属性：通过 __getattr__ 延迟读取 ──────────────────────────────

def __getattr__(name: str) -> str:
    """模块级属性延迟加载（PEP 562）。

    支持 ``from .config import LLM_API_KEY`` 等兼容调用，
    但不再在导入时即执行 load_config()。
    不缓存到 globals()，确保 importlib.reload 后能读取新环境变量。
    """
    _compat_map = {
        "LLM_API_KEY": lambda c: c.llm.api_key,
        "LLM_BASE_URL": lambda c: c.llm.base_url,
        "LLM_MODEL": lambda c: c.llm.model,
        "GITHUB_TOKEN": lambda c: c.github.token,
        "TTS_ENGINE": lambda c: c.tts.engine,
        "TTS_RATE": lambda c: c.tts.rate,
        "TTS_API_KEY": lambda c: c.tts.api_key,
        "TTS_BASE_URL": lambda c: c.tts.base_url,
        "TTS_MODEL": lambda c: c.tts.model,
        "TTS_VOICE_ZH": lambda c: c.tts.voice_zh,
        "TTS_VOICE_EN": lambda c: c.tts.voice_en,
    }
    if name in _compat_map:
        return _compat_map[name](get_config())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

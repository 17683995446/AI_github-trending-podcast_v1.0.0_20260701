"""LLM 后端实现（阶段4: 注册机制内置后端）。

提供两个内置 LLM 后端，通过 ``register_llm_backend`` 装饰器注册：

- ``openai``  — OpenAI 兼容 API（硅基流动 / OpenAI / 其他兼容服务）
- ``ollama``  — 本地 Ollama 服务（零成本离线推理）

新增后端只需实现 ``LLMBackend`` 接口并注册，无需修改 ``LLMEnhancer``。
"""

from __future__ import annotations

from typing import Any

from .exceptions import LLMError
from .registry import LLMBackend, register_llm_backend
from .logging_config import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# OpenAI 兼容后端
# ═══════════════════════════════════════════════════════════════════

@register_llm_backend("openai", priority=100)
class OpenAIBackend(LLMBackend):
    """OpenAI 兼容 API 后端。

    支持所有兼容 OpenAI Chat Completions API 的服务，
    包括 OpenAI 官方、硅基流动 SiliconFlow、Azure OpenAI 等。

    配置通过 ``gh_trending_audio.config`` 模块读取：
    - ``LLM_API_KEY``  — API 密钥
    - ``LLM_BASE_URL`` — API 基础 URL
    - ``LLM_MODEL``    — 模型名称
    """

    def __init__(self) -> None:
        """初始化 OpenAI 兼容后端。

        从 ``gh_trending_audio.config`` 读取以下配置：
        - ``LLM_API_KEY``  — API 密钥
        - ``LLM_BASE_URL`` — API 基础 URL
        - ``LLM_MODEL``    — 模型名称
        """
        from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        self._api_key = LLM_API_KEY
        self._base_url = LLM_BASE_URL
        self._model = LLM_MODEL

    @property
    def name(self) -> str:
        return "openai"

    @property
    def requires_network(self) -> bool:
        return True

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_client(self) -> Any:
        """创建 OpenAI 兼容客户端。

        Returns:
            ``openai.OpenAI`` 客户端实例，支持 ``chat.completions.create`` 接口。
        """
        from openai import OpenAI
        return OpenAI(api_key=self._api_key, base_url=self._base_url)

    @staticmethod
    def is_available() -> bool:
        """检查 OpenAI 后端是否可用（API Key 已配置）。"""
        try:
            from .config import LLM_API_KEY
            return bool(LLM_API_KEY)
        except ImportError:
            return False


# ═══════════════════════════════════════════════════════════════════
# Ollama 本地后端
# ═══════════════════════════════════════════════════════════════════

@register_llm_backend("ollama", priority=50)
class OllamaBackend(LLMBackend):
    """Ollama 本地 LLM 后端。

    通过 Ollama 的 OpenAI 兼容端点（``/v1``）接入，
    无需 API Key，完全离线运行。

    前提条件：
    1. Ollama 服务在本地运行（默认 ``http://localhost:11434``）
    2. 至少安装一个模型（如 ``ollama pull qwen2.5:7b``）
    """

    def __init__(self) -> None:
        """初始化 Ollama 本地后端。

        通过 ``get_llm_config_for_ollama`` 探测本地 Ollama 服务并读取配置
        （api_key、base_url、model）。

        Raises:
            LLMError: Ollama 服务未运行或未安装模型时抛出。
        """
        from .local_backends import get_llm_config_for_ollama
        cfg = get_llm_config_for_ollama()
        if cfg is None:
            raise LLMError(
                "Ollama 后端不可用：服务未运行或未安装模型。"
                "请启动 Ollama 并拉取模型（如 ollama pull qwen2.5:7b）。"
            )
        self._api_key = cfg["api_key"]
        self._base_url = cfg["base_url"]
        self._model = cfg["model"]

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def requires_network(self) -> bool:
        return False

    @property
    def model(self) -> str:
        return self._model

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_client(self) -> Any:
        """创建 OpenAI 兼容客户端（指向 Ollama 端点）。

        Returns:
            ``openai.OpenAI`` 客户端实例，base_url 指向本地 Ollama 服务。
        """
        from openai import OpenAI
        return OpenAI(api_key=self._api_key, base_url=self._base_url)

    @staticmethod
    def is_available() -> bool:
        """检查 Ollama 后端是否可用。"""
        try:
            from .local_backends import detect_ollama, list_ollama_models
            return detect_ollama() and len(list_ollama_models()) > 0
        except ImportError:
            return False

"""本地后端检测与集成（阶段10: 零成本本地部署）。

自动检测并集成本地 LLM（Ollama）和本地 TTS（Piper），
让用户无需 API Key 即可使用完整功能。

核心功能：
    - ``detect_ollama()``    → 检测 Ollama 服务是否可用
    - ``list_ollama_models()`` → 列出已安装的 Ollama 模型
    - ``detect_piper()``     → 检测 Piper TTS 是否可用
    - ``get_system_backends()`` → 返回所有可用后端信息

设计原则：
    - 第一性原理：工具应能在无网络环境下工作
    - 优雅降级：本地后端不可用时自动回退到云服务
    - 零配置：自动检测已安装的本地工具
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from .constants import LOCAL_BACKEND_QUICK_TIMEOUT, LOCAL_BACKEND_FULL_TIMEOUT
from .logging_config import get_logger

logger = get_logger(__name__)

_OLLAMA_BASE_URL = "http://localhost:11434"
_PIPER_BIN_CANDIDATES = ["piper", "piper-tts"]


def detect_ollama() -> bool:
    """检测 Ollama 服务是否在本地运行。

    Returns:
        True 如果 Ollama 服务可用
    """
    try:
        import requests
        resp = requests.get(f"{_OLLAMA_BASE_URL}/api/tags", timeout=LOCAL_BACKEND_QUICK_TIMEOUT)
        return resp.status_code == 200
    except (ImportError, OSError, RuntimeError):
        return False


def list_ollama_models() -> list[dict[str, Any]]:
    """列出已安装的 Ollama 模型。

    Returns:
        模型列表，每项含 name/size/modified 等信息
    """
    if not detect_ollama():
        return []
    try:
        import requests
        resp = requests.get(f"{_OLLAMA_BASE_URL}/api/tags", timeout=LOCAL_BACKEND_FULL_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("models", [])
    except (ConnectionError, OSError, RuntimeError):
        logger.debug("列出 Ollama 模型失败", exc_info=True)
    return []


def get_llm_config_for_ollama() -> dict[str, str] | None:
    """获取 Ollama 的 LLM 配置（OpenAI 兼容格式）。

    Ollama 提供 OpenAI 兼容端点 ``http://localhost:11434/v1/``，
    可直接用于现有的 ``LLMEnhancer``。

    Returns:
        配置字典含 base_url/model/api_key，Ollama 不可用返回 None
    """
    if not detect_ollama():
        return None

    models = list_ollama_models()
    if not models:
        logger.info("Ollama 运行中但未安装模型")
        return None

    # 优先选择适合的模型
    preferred = ["qwen2.5:7b", "qwen2.5:14b", "llama3.1:8b", "glm4:9b",
                 "qwen2.5:3b", "phi3:14b", "mistral:7b"]
    model_names = [m.get("name", "") for m in models]

    selected = None
    for pref in preferred:
        for name in model_names:
            if pref in name:
                selected = name
                break
        if selected:
            break

    if not selected:
        selected = model_names[0]  # 使用第一个可用模型

    return {
        "base_url": f"{_OLLAMA_BASE_URL}/v1",
        "model": selected,
        "api_key": "ollama",  # Ollama 不需要真实 Key，但 OpenAI 客户端需要非空值
    }


def detect_piper() -> bool:
    """检测 Piper TTS 是否已安装。

    Returns:
        True 如果 piper 二进制可用
    """
    for bin_name in _PIPER_BIN_CANDIDATES:
        if shutil.which(bin_name):
            return True
    return False


def get_piper_models_dir() -> str | None:
    """获取 Piper 模型目录。"""
    import os
    # 常见模型目录
    candidates = [
        os.environ.get("PIPER_MODELS", ""),
        os.path.expanduser("~/.local/share/piper"),
        "/usr/share/piper/models",
    ]
    for path in candidates:
        if path and os.path.isdir(path):
            return path
    return None


def list_piper_models() -> list[str]:
    """列出可用的 Piper 模型文件。"""
    models_dir = get_piper_models_dir()
    if not models_dir:
        return []
    from pathlib import Path
    models = []
    for onnx_file in Path(models_dir).rglob("*.onnx"):
        models.append(str(onnx_file))
    return models


def get_system_backends() -> dict[str, Any]:
    """获取所有可用后端信息（用于系统状态展示）。

    Returns:
        包含 LLM 和 TTS 后端可用性信息的字典
    """
    ollama_available = detect_ollama()
    ollama_models = list_ollama_models() if ollama_available else []
    piper_available = detect_piper()
    piper_models = list_piper_models() if piper_available else []

    # 检查云端后端
    from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    cloud_llm_available = bool(LLM_API_KEY)

    # 检查 TTS 后端
    from .config import TTS_API_KEY
    cloud_tts_available = bool(TTS_API_KEY) or "siliconflow" in (LLM_BASE_URL or "")

    try:
        import edge_tts
        edge_tts_available = True
    except ImportError:
        edge_tts_available = False

    try:
        import pydub
        pydub_available = True
    except ImportError:
        pydub_available = False

    return {
        "llm": {
            "ollama": {
                "available": ollama_available,
                "models": [m.get("name", "") for m in ollama_models],
                "model_count": len(ollama_models),
            },
            "cloud": {
                "available": cloud_llm_available,
                "provider": "siliconflow" if "siliconflow" in (LLM_BASE_URL or "") else "openai-compatible",
                "model": LLM_MODEL or "not configured",
            },
            # 阶段4: 注册表后端状态（LLMEnhancer 实际使用的数据源）
            "registered_backends": _get_registered_llm_backends(),
        },
        "tts": {
            "piper": {
                "available": piper_available,
                "models": piper_models,
                "model_count": len(piper_models),
            },
            "siliconflow": {
                "available": cloud_tts_available,
            },
            "edge_tts": {
                "available": edge_tts_available,
            },
            "espeak": {
                "available": bool(shutil.which("espeak-ng") or shutil.which("espeak")),
            },
            "pydub": {
                "available": pydub_available,
            },
        },
        "ffmpeg": {
            "available": bool(shutil.which("ffmpeg")),
        },
        "repomix": {
            "available": bool(shutil.which("repomix")),
        },
    }


def _get_registered_llm_backends() -> dict[str, dict[str, Any]]:
    """获取已注册的 LLM 后端状态（阶段4: 注册机制集成）。

    Returns:
        {后端名: {available: bool, requires_network: bool}} 字典
    """
    try:
        # 确保内置后端已注册
        from .llm_backends import OpenAIBackend, OllamaBackend  # noqa: F401
        from .registry import get_available_llm_backends, _LLM_REGISTRY

        result = {}
        for name, info in _LLM_REGISTRY.items():
            cls = info["class"]
            available = False
            requires_network = True
            try:
                available = cls.is_available()
            except (AttributeError, TypeError):
                pass
            # 尝试从类属性获取 requires_network（property 的 fget）
            try:
                prop = getattr(cls, "requires_network", None)
                if isinstance(prop, property):
                    requires_network = prop.fget(cls.__new__(cls)) if prop.fget else True
                elif isinstance(prop, bool):
                    requires_network = prop
            except (AttributeError, TypeError):
                pass
            result[name] = {
                "available": available,
                "requires_network": requires_network,
            }
        return result
    except ImportError:
        return {}

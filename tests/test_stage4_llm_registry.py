"""阶段4: LLM后端注册机制 验证测试。"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试：注册表基础设施
# ═══════════════════════════════════════════════════════════════════

class TestLLMRegistry:
    """LLM 后端注册表测试。"""

    def test_llm_backend_abc_exists(self):
        """LLMBackend 抽象基类应存在。"""
        from gh_trending_audio.registry import LLMBackend
        assert LLMBackend is not None

    def test_llm_backend_is_abc(self):
        """LLMBackend 应为抽象基类。"""
        from abc import ABC
        from gh_trending_audio.registry import LLMBackend
        assert issubclass(LLMBackend, ABC)

    def test_llm_backend_has_required_abstract_methods(self):
        """LLMBackend 应定义所有必需的抽象方法。"""
        from gh_trending_audio.registry import LLMBackend
        abstract_methods = LLMBackend.__abstractmethods__
        expected = {"name", "requires_network", "model", "api_key",
                     "base_url", "get_client", "is_available"}
        assert expected.issubset(abstract_methods), \
            f"缺少抽象方法: {expected - abstract_methods}"

    def test_register_llm_backend_decorator_exists(self):
        """register_llm_backend 装饰器应存在且可调用。"""
        from gh_trending_audio.registry import register_llm_backend
        assert callable(register_llm_backend)

    def test_get_llm_backend_function_exists(self):
        """get_llm_backend 函数应存在。"""
        from gh_trending_audio.registry import get_llm_backend
        assert callable(get_llm_backend)

    def test_list_llm_backends_function_exists(self):
        """list_llm_backends 函数应存在。"""
        from gh_trending_audio.registry import list_llm_backends
        assert callable(list_llm_backends)

    def test_get_auto_llm_backend_function_exists(self):
        """get_auto_llm_backend 函数应存在。"""
        from gh_trending_audio.registry import get_auto_llm_backend
        assert callable(get_auto_llm_backend)

    def test_registry_dict_exists(self):
        """_LLM_REGISTRY 注册表字典应存在。"""
        from gh_trending_audio.registry import _LLM_REGISTRY
        assert isinstance(_LLM_REGISTRY, dict)

    def test_backend_priority_exists(self):
        """_LLM_BACKEND_PRIORITY 优先级列表应存在。"""
        from gh_trending_audio.registry import _LLM_BACKEND_PRIORITY
        assert isinstance(_LLM_BACKEND_PRIORITY, list)
        assert "openai" in _LLM_BACKEND_PRIORITY
        assert "ollama" in _LLM_BACKEND_PRIORITY


# ═══════════════════════════════════════════════════════════════════
# 内置后端验证
# ═══════════════════════════════════════════════════════════════════

class TestBuiltinBackends:
    """内置 LLM 后端测试。"""

    def test_openai_backend_registered(self):
        """OpenAI 后端应已注册。"""
        from gh_trending_audio.registry import get_llm_backend
        from gh_trending_audio.llm_backends import OpenAIBackend  # 触发注册
        cls = get_llm_backend("openai")
        assert cls is not None
        assert cls is OpenAIBackend

    def test_ollama_backend_registered(self):
        """Ollama 后端应已注册。"""
        from gh_trending_audio.registry import get_llm_backend
        from gh_trending_audio.llm_backends import OllamaBackend  # 触发注册
        cls = get_llm_backend("ollama")
        assert cls is not None
        assert cls is OllamaBackend

    def test_list_llm_backends_includes_builtins(self):
        """list_llm_backends 应包含内置后端。"""
        from gh_trending_audio.registry import list_llm_backends
        from gh_trending_audio.llm_backends import OpenAIBackend, OllamaBackend  # 触发注册
        backends = list_llm_backends()
        assert "openai" in backends
        assert "ollama" in backends

    def test_openai_backend_properties(self):
        """OpenAIBackend 属性应正确。"""
        from gh_trending_audio.llm_backends import OpenAIBackend
        assert OpenAIBackend.name.fget(OpenAIBackend) == "openai" or \
               OpenAIBackend().name == "openai"
        assert OpenAIBackend.requires_network.fget(OpenAIBackend) is True or \
               OpenAIBackend().requires_network is True

    def test_ollama_backend_properties(self):
        """OllamaBackend 属性应正确。"""
        from gh_trending_audio.llm_backends import OllamaBackend
        assert OllamaBackend.name.fget(OllamaBackend) == "ollama" or \
               OllamaBackend().name == "ollama"
        assert OllamaBackend.requires_network.fget(OllamaBackend) is False or \
               OllamaBackend().requires_network is False

    def test_openai_backend_is_available_with_key(self):
        """配置了 API Key 时 OpenAIBackend 应可用。"""
        from gh_trending_audio.llm_backends import OpenAIBackend
        with patch("gh_trending_audio.config.LLM_API_KEY", "sk-test-key"):
            assert OpenAIBackend.is_available() is True

    def test_openai_backend_not_available_without_key(self):
        """未配置 API Key 时 OpenAIBackend 应不可用。"""
        from gh_trending_audio.llm_backends import OpenAIBackend
        with patch("gh_trending_audio.config.LLM_API_KEY", ""):
            assert OpenAIBackend.is_available() is False

    def test_openai_backend_get_client(self):
        """OpenAIBackend.get_client 应返回客户端对象。"""
        try:
            import openai  # noqa: F401
        except ImportError:
            pytest.skip("openai 库未安装")
        from gh_trending_audio.llm_backends import OpenAIBackend
        with patch("gh_trending_audio.config.LLM_API_KEY", "sk-test-key"), \
             patch("gh_trending_audio.config.LLM_BASE_URL", "https://api.test.com/v1"), \
             patch("gh_trending_audio.config.LLM_MODEL", "test-model"):
            backend = OpenAIBackend()
            client = backend.get_client()
            assert client is not None

    def test_get_available_llm_backends(self):
        """get_available_llm_backends 应返回所有后端状态。"""
        from gh_trending_audio.registry import get_available_llm_backends
        from gh_trending_audio.llm_backends import OpenAIBackend, OllamaBackend  # 触发注册
        result = get_available_llm_backends()
        assert "openai" in result
        assert "ollama" in result
        assert isinstance(result["openai"], bool)
        assert isinstance(result["ollama"], bool)


# ═══════════════════════════════════════════════════════════════════
# LLMEnhancer 集成验证
# ═══════════════════════════════════════════════════════════════════

class TestLLMEnhancerRegistry:
    """LLMEnhancer 与注册表集成测试。"""

    def test_llm_enhancer_uses_registry(self):
        """LLMEnhancer 应使用注册表自动选择后端。"""
        import inspect
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        source = inspect.getsource(LLMEnhancer.__init__)
        assert "get_auto_llm_backend" in source or "_backend" in source

    def test_llm_enhancer_stores_backend(self):
        """LLMEnhancer 应存储 _backend 实例。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        with patch("gh_trending_audio.config.LLM_API_KEY", "sk-test-key"):
            enhancer = LLMEnhancer()
            assert hasattr(enhancer, "_backend")
            assert enhancer._backend is not None

    def test_llm_enhancer_backend_name_is_openai(self):
        """配置 API Key 时应选择 openai 后端。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        with patch("gh_trending_audio.config.LLM_API_KEY", "sk-test-key"):
            enhancer = LLMEnhancer()
            assert enhancer._backend.name == "openai"

    def test_llm_enhancer_backward_compatible_attrs(self):
        """api_key/base_url/model 属性应保持向后兼容。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        with patch("gh_trending_audio.config.LLM_API_KEY", "sk-test-key"), \
             patch("gh_trending_audio.config.LLM_BASE_URL", "https://api.test.com/v1"), \
             patch("gh_trending_audio.config.LLM_MODEL", "test-model"):
            enhancer = LLMEnhancer()
            assert enhancer.api_key == "sk-test-key"
            assert enhancer.base_url == "https://api.test.com/v1"
            assert enhancer.model == "test-model"

    def test_llm_enhancer_falls_back_to_ollama(self):
        """无 API Key 但 Ollama 可用时应回退到 Ollama 后端。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        ollama_cfg = {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:7b",
            "api_key": "ollama",
        }
        with patch("gh_trending_audio.config.LLM_API_KEY", ""), \
             patch("gh_trending_audio.local_backends.get_llm_config_for_ollama", return_value=ollama_cfg), \
             patch("gh_trending_audio.llm_backends.OllamaBackend.is_available", return_value=True):
            enhancer = LLMEnhancer()
            assert enhancer._backend.name == "ollama"
            assert enhancer.api_key == "ollama"

    def test_llm_enhancer_raises_without_any_backend(self):
        """无任何可用后端时应抛出 ConfigError。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        from gh_trending_audio.exceptions import ConfigError
        with patch("gh_trending_audio.config.LLM_API_KEY", ""), \
             patch("gh_trending_audio.llm_backends.OpenAIBackend.is_available", return_value=False), \
             patch("gh_trending_audio.llm_backends.OllamaBackend.is_available", return_value=False):
            with pytest.raises(ConfigError, match="LLM API Key"):
                LLMEnhancer()


# ═══════════════════════════════════════════════════════════════════
# 对称性验证（与 TTS 注册表对比）
# ═══════════════════════════════════════════════════════════════════

class TestRegistrySymmetry:
    """验证 LLM 注册表与 TTS 注册表设计对称。"""

    def test_llm_and_tts_both_have_abc(self):
        """LLM 和 TTS 都应有抽象基类。"""
        from gh_trending_audio.registry import LLMBackend, TTSBackend
        from abc import ABC
        assert issubclass(LLMBackend, ABC)
        assert issubclass(TTSBackend, ABC)

    def test_llm_and_tms_both_have_register_decorator(self):
        """LLM 和 TTS 都应有注册装饰器。"""
        from gh_trending_audio.registry import register_llm_backend, register_tts_engine
        assert callable(register_llm_backend)
        assert callable(register_tts_engine)

    def test_llm_and_tts_both_have_get_function(self):
        """LLM 和 TTS 都应有 get_xxx 查找函数。"""
        from gh_trending_audio.registry import get_llm_backend, get_tts_engine
        assert callable(get_llm_backend)
        assert callable(get_tts_engine)

    def test_llm_and_tts_both_have_list_function(self):
        """LLM 和 TTS 都应有 list_xxx 列表函数。"""
        from gh_trending_audio.registry import list_llm_backends, list_tts_engines
        assert callable(list_llm_backends)
        assert callable(list_tts_engines)

    def test_llm_and_tts_both_have_available_function(self):
        """LLM 和 TTS 都应有可用性查询函数。"""
        from gh_trending_audio.registry import (
            get_available_llm_backends, get_available_engines
        )
        assert callable(get_available_llm_backends)
        assert callable(get_available_engines)

    def test_llm_backend_has_is_available_static(self):
        """LLMBackend 和 TTSBackend 都应有 is_available 静态方法。"""
        from gh_trending_audio.registry import LLMBackend, TTSBackend
        assert hasattr(LLMBackend, "is_available")
        assert hasattr(TTSBackend, "is_available")

    def test_llm_backend_has_name_property(self):
        """LLMBackend 和 TTSBackend 都应有 name 属性。"""
        from gh_trending_audio.registry import LLMBackend, TTSBackend
        assert "name" in LLMBackend.__abstractmethods__
        assert "name" in TTSBackend.__abstractmethods__


# ═══════════════════════════════════════════════════════════════════
# 懒加载导出验证
# ═══════════════════════════════════════════════════════════════════

class TestLazyExports:
    """验证注册表函数可通过包顶层访问。"""

    def test_llm_backend_exported(self):
        """LLMBackend 应可通过顶层包访问。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "LLMBackend")

    def test_register_llm_backend_exported(self):
        """register_llm_backend 应可通过顶层包访问。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "register_llm_backend")

    def test_get_auto_llm_backend_exported(self):
        """get_auto_llm_backend 应可通过顶层包访问。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "get_auto_llm_backend")

    def test_list_llm_backends_exported(self):
        """list_llm_backends 应可通过顶层包访问。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "list_llm_backends")

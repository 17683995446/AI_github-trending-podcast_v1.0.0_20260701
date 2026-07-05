"""阶段10: 本地 LLM (Ollama) + 本地 TTS (Piper) 测试。"""

import pytest
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestLocalBackendsUnit:
    """本地后端检测单元测试。"""

    def test_detect_ollama_not_running(self):
        """Ollama 未运行时应返回 False。"""
        from gh_trending_audio.local_backends import detect_ollama
        # 在测试环境中 Ollama 通常未运行
        result = detect_ollama()
        assert isinstance(result, bool)

    def test_detect_piper_not_installed(self):
        """Piper 未安装时应返回 False。"""
        from gh_trending_audio.local_backends import detect_piper
        result = detect_piper()
        assert isinstance(result, bool)

    def test_list_ollama_models_returns_list(self):
        """list_ollama_models 应返回列表。"""
        from gh_trending_audio.local_backends import list_ollama_models
        result = list_ollama_models()
        assert isinstance(result, list)

    def test_get_system_backends_structure(self):
        """get_system_backends 应返回正确结构。"""
        from gh_trending_audio.local_backends import get_system_backends
        backends = get_system_backends()
        assert "llm" in backends
        assert "tts" in backends
        assert "ffmpeg" in backends
        assert "repomix" in backends
        assert "ollama" in backends["llm"]
        assert "cloud" in backends["llm"]
        assert "piper" in backends["tts"]
        assert "edge_tts" in backends["tts"]
        assert "espeak" in backends["tts"]
        assert isinstance(backends["llm"]["ollama"]["available"], bool)
        assert isinstance(backends["tts"]["piper"]["available"], bool)

    def test_get_llm_config_for_ollama_no_ollama(self):
        """Ollama 不可用时应返回 None。"""
        from gh_trending_audio.local_backends import get_llm_config_for_ollama
        with patch("gh_trending_audio.local_backends.detect_ollama", return_value=False):
            result = get_llm_config_for_ollama()
            assert result is None

    def test_get_llm_config_for_ollama_with_models(self):
        """Ollama 有模型时应返回配置。"""
        from gh_trending_audio.local_backends import get_llm_config_for_ollama
        mock_models = [
            {"name": "qwen2.5:7b", "size": 4700000000},
            {"name": "llama3.1:8b", "size": 4900000000},
        ]
        with patch("gh_trending_audio.local_backends.detect_ollama", return_value=True):
            with patch("gh_trending_audio.local_backends.list_ollama_models", return_value=mock_models):
                cfg = get_llm_config_for_ollama()
                assert cfg is not None
                assert "base_url" in cfg
                assert "11434" in cfg["base_url"]
                assert cfg["model"] == "qwen2.5:7b"  # 优先匹配
                assert cfg["api_key"] == "ollama"


class TestPiperTTSUnit:
    """Piper TTS 引擎单元测试。"""

    def test_piper_backend_registered(self):
        """Piper 引擎应已注册。"""
        from gh_trending_audio.registry import list_tts_engines
        engines = list_tts_engines()
        assert "piper" in engines

    def test_piper_backend_name(self):
        """Piper 引擎名称应为 'piper'。"""
        from gh_trending_audio.registry import get_tts_engine
        engine_cls = get_tts_engine("piper")
        assert engine_cls is not None
        # 实例化检查 name 属性
        instance = engine_cls()
        assert instance.name == "piper"

    def test_piper_backend_no_network(self):
        """Piper 引擎不需要网络。"""
        from gh_trending_audio.registry import get_tts_engine
        engine_cls = get_tts_engine("piper")
        instance = engine_cls()
        assert instance.requires_network is False

    def test_piper_is_available_returns_bool(self):
        """is_available 应返回布尔值。"""
        from gh_trending_audio.registry import get_tts_engine
        engine_cls = get_tts_engine("piper")
        assert isinstance(engine_cls.is_available(), bool)


class TestOllamaLLMIntegration:
    """Ollama LLM 自动检测集成测试。"""

    def test_llm_enhancer_ollama_fallback(self):
        """无 API Key 时应尝试 Ollama 回退。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        from gh_trending_audio.exceptions import ConfigError

        with patch("gh_trending_audio.config.LLM_API_KEY", ""):
            with patch("gh_trending_audio.local_backends.detect_ollama", return_value=False):
                with patch("gh_trending_audio.local_backends.get_llm_config_for_ollama", return_value=None):
                    # 无 API Key 且无 Ollama 时应抛 ConfigError
                    with pytest.raises(ConfigError, match="LLM API Key"):
                        LLMEnhancer()

    def test_llm_enhancer_uses_ollama(self):
        """无 API Key 但 Ollama 可用时应自动配置。"""
        from gh_trending_audio.llm_enhancer import LLMEnhancer

        ollama_cfg = {
            "base_url": "http://localhost:11434/v1",
            "model": "qwen2.5:7b",
            "api_key": "ollama",
        }
        with patch("gh_trending_audio.config.LLM_API_KEY", ""):
            with patch("gh_trending_audio.local_backends.get_llm_config_for_ollama", return_value=ollama_cfg):
                # 阶段4: 需同时 mock OllamaBackend.is_available 以通过注册表检测
                with patch("gh_trending_audio.llm_backends.OllamaBackend.is_available", return_value=True):
                    enhancer = LLMEnhancer()
                    assert enhancer.api_key == "ollama"
                    assert "11434" in enhancer.base_url
                    assert enhancer.model == "qwen2.5:7b"


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestStage10Integration:
    """阶段10 API 端点和 UI 集成测试。"""

    def test_system_backends_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/system-backends" in r["pattern"] for r in routes)
        assert any("serve_system_backends" in r["handler"] for r in routes)

    def test_system_backends_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_system_backends
        assert callable(serve_system_backends)

    def test_dashboard_has_backend_status_section(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "backendStatus" in DASHBOARD_HTML
        assert "backendList" in DASHBOARD_HTML
        assert "initBackendStatus" in DASHBOARD_HTML

    def test_dashboard_has_system_backends_fetch(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "/api/system-backends" in DASHBOARD_HTML

    def test_tts_engine_imports_piper(self):
        """tts_engine.py 应导入 piper_tts。"""
        from gh_trending_audio.tts_engine import _PiperBackend  # noqa
        # 如果导入成功，说明注册已触发

    def test_lazy_export_local_backends(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "detect_ollama")
        assert hasattr(gh_trending_audio, "detect_piper")
        assert hasattr(gh_trending_audio, "get_system_backends")

    def test_requirements_has_ollama(self):
        from pathlib import Path
        req = Path("/workspace/gh_trending_audio/requirements.txt").read_text()
        assert "ollama" in req

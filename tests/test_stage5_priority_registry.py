"""阶段5：优先级表外置测试。"""

import pytest
from gh_trending_audio.registry import (
    register_llm_backend, register_tts_engine,
    get_auto_llm_backend, get_available_engines,
    LLMBackend, TTSBackend,
)


class TestPriorityRegistration:
    """优先级注册测试。"""

    def test_llm_backend_with_priority(self):
        """LLM后端注册时带优先级。"""
        @register_llm_backend("test_priority_high", priority=200)
        class HighPriorityBackend(LLMBackend):
            @staticmethod
            def is_available():
                return False
            def get_client(self):
                pass
            @property
            def model(self):
                return "test"
        
        # 验证注册信息中包含priority
        from gh_trending_audio.registry import _LLM_REGISTRY
        info = _LLM_REGISTRY.get("test_priority_high")
        assert info is not None
        assert info.get("priority", 0) == 200

    def test_tts_engine_with_priority(self):
        """TTS引擎注册时带优先级。"""
        @register_tts_engine("test_priority_engine", priority=200)
        class HighPriorityEngine(TTSBackend):
            @staticmethod
            def is_available():
                return False
            def synthesize(self, text, output_path, voice=None, rate=None):
                pass
            @property
            def requires_network(self):
                return False
        
        from gh_trending_audio.registry import _TTS_REGISTRY
        info = _TTS_REGISTRY.get("test_priority_engine")
        assert info is not None
        assert info.get("priority", 0) == 200

    def test_default_priority_is_zero(self):
        """不指定priority时默认为0。"""
        @register_llm_backend("test_default_prio")
        class DefaultBackend(LLMBackend):
            @staticmethod
            def is_available():
                return False
            def get_client(self):
                pass
            @property
            def model(self):
                return "test"
        
        from gh_trending_audio.registry import _LLM_REGISTRY
        info = _LLM_REGISTRY.get("test_default_prio")
        assert info.get("priority", -1) == 0

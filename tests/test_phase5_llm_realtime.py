"""Phase 5 单元测试：LLM 质量与实时性。

测试范围：
1. mutagen 替代 ffprobe 获取音频时长
2. instructor 结构化输出（PodcastScript 模型）
3. SSE 端点存在
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestMutagenAudioDuration:
    """mutagen 替代 ffprobe 测试。"""

    def test_mutagen_importable(self):
        """mutagen 模块应可导入。"""
        try:
            import mutagen
            assert True
        except ImportError:
            pytest.skip("mutagen 未安装")

    def test_get_audio_duration_uses_mutagen(self):
        """get_audio_duration 源码应优先使用 mutagen。"""
        import inspect
        from gh_trending_audio.web.utils import get_audio_duration
        source = inspect.getsource(get_audio_duration)
        assert "mutagen" in source

    def test_get_audio_duration_has_fallback(self):
        """get_audio_duration 应保留 ffprobe 作为退化方案。"""
        import inspect
        from gh_trending_audio.web.utils import get_audio_duration
        source = inspect.getsource(get_audio_duration)
        assert "ffprobe" in source

    def test_get_audio_duration_nonexistent_file(self):
        """不存在的文件应返回 None。"""
        from gh_trending_audio.web.utils import get_audio_duration
        result = get_audio_duration("/nonexistent/file.mp3")
        assert result is None


class TestInstructorStructuredOutput:
    """instructor 结构化输出测试。"""

    def test_pydantic_importable(self):
        """pydantic 应可导入。"""
        try:
            from pydantic import BaseModel, Field
            assert True
        except ImportError:
            pytest.skip("pydantic 未安装")

    def test_instructor_importable(self):
        """instructor 应可导入。"""
        try:
            import instructor
            assert True
        except ImportError:
            pytest.skip("instructor 未安装")

    def test_podcast_script_model_exists(self):
        """PodcastScript 模型应在 llm_enhancer 模块中定义。"""
        os.environ.setdefault("LLM_API_KEY", "sk-test-key-for-unit-tests")
        from gh_trending_audio.llm_enhancer import PodcastScript
        assert PodcastScript is not None

    def test_podcast_script_fields(self):
        """PodcastScript 应有 markdown 和 audio_script 字段。"""
        os.environ.setdefault("LLM_API_KEY", "sk-test-key-for-unit-tests")
        from gh_trending_audio.llm_enhancer import PodcastScript
        ps = PodcastScript(markdown="# Test", audio_script="A: Hello")
        assert ps.markdown == "# Test"
        assert ps.audio_script == "A: Hello"

    def test_generate_script_has_instructor_path(self):
        """generate_script 方法应包含 instructor 集成。"""
        import inspect
        os.environ.setdefault("LLM_API_KEY", "sk-test-key-for-unit-tests")
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        source = inspect.getsource(LLMEnhancer.generate_script)
        assert "instructor" in source
        assert "PodcastScript" in source

    def test_generate_script_has_fallback(self):
        """instructor 失败时应有字符串分割退化方案。"""
        import inspect
        os.environ.setdefault("LLM_API_KEY", "sk-test-key-for-unit-tests")
        from gh_trending_audio.llm_enhancer import LLMEnhancer
        source = inspect.getsource(LLMEnhancer.generate_script)
        assert "===AUDIO===" in source


class TestSSEEndpoint:
    """SSE 实时进度推送测试（Phase 1 重构后位于 api_handlers.py）。"""

    def test_sse_route_exists(self):
        """/api/events 路由应存在。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/events" in r["pattern"] for r in routes), "应有 /api/events 路由"

    def test_serve_sse_events_method_exists(self):
        """serve_sse_events 函数应存在。"""
        from gh_trending_audio.web import api_handlers
        assert hasattr(api_handlers, 'serve_sse_events'), \
            "api_handlers 应有 serve_sse_events 函数"

    def test_sse_sets_content_type(self):
        """serve_sse_events 应设置 text/event-stream Content-Type。"""
        import inspect
        from gh_trending_audio.web import api_handlers
        source = inspect.getsource(api_handlers.serve_sse_events)
        assert "text/event-stream" in source, \
            "serve_sse_events 应设置 text/event-stream Content-Type"

    def test_sse_has_heartbeat(self):
        """serve_sse_events 应有心跳保活机制。"""
        import inspect
        from gh_trending_audio.web import api_handlers
        source = inspect.getsource(api_handlers.serve_sse_events)
        assert "heartbeat" in source

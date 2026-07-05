"""Phase 2 单元测试：缓存与 LLM 一致性。

测试范围：
1. cachetools TTLCache 替换内存字典（自动过期、容量限制）
2. /api/ask 统一使用 openai 库（不再用 urllib 手写）
"""
import time
import pytest
from unittest.mock import patch, MagicMock


class TestCachetoolsIntegration:
    """cachetools TTLCache 集成测试。"""

    def test_cache_uses_ttlcache(self):
        """缓存对象应为 TTLCache 类型（或退化字典）。"""
        from gh_trending_audio.web.api_handlers import _FILETREE_CACHE, _FILE_CONTENT_CACHE
        # 验证缓存对象存在且可用
        assert _FILETREE_CACHE is not None
        assert _FILE_CONTENT_CACHE is not None
        # 如果 cachetools 已安装，应为 TTLCache
        try:
            from cachetools import TTLCache
            assert isinstance(_FILETREE_CACHE, TTLCache)
            assert isinstance(_FILE_CONTENT_CACHE, TTLCache)
        except ImportError:
            pass  # 退化模式也接受

    def test_cache_ttl_expiration(self):
        """TTLCache 应在 TTL 后自动过期。"""
        try:
            from cachetools import TTLCache
        except ImportError:
            pytest.skip("cachetools 未安装")

        cache = TTLCache(maxsize=10, ttl=1)
        cache["key1"] = {"data": "test"}
        assert "key1" in cache
        time.sleep(1.1)
        assert "key1" not in cache

    def test_cache_maxsize_eviction(self):
        """TTLCache 应在超过 maxsize 时淘汰最旧条目。"""
        try:
            from cachetools import TTLCache
        except ImportError:
            pytest.skip("cachetools 未安装")

        cache = TTLCache(maxsize=3, ttl=300)
        cache["a"] = 1
        cache["b"] = 2
        cache["c"] = 3
        cache["d"] = 4  # 超出 maxsize，淘汰 "a"
        assert "a" not in cache
        assert "d" in cache

    def test_cache_write_and_read(self):
        """缓存应能正确写入和读取数据。"""
        from gh_trending_audio.web.api_handlers import _FILETREE_CACHE
        test_key = "test:owner/repo"
        test_data = {"tree": [{"path": "README.md", "type": "blob"}]}
        _FILETREE_CACHE[test_key] = test_data
        assert _FILETREE_CACHE[test_key] == test_data
        # 清理
        del _FILETREE_CACHE[test_key]


class TestApiAskUsesOpenAI:
    """/api/ask 应使用 openai 库而非 urllib（Phase 1 重构后位于 api_handlers.py）。"""

    def test_no_urllib_import_in_ask(self):
        """handle_ask 函数源码中不应包含 urllib 导入。"""
        import inspect
        from gh_trending_audio.web import api_handlers
        source = inspect.getsource(api_handlers.handle_ask)
        assert "urllib.request" not in source, \
            "handle_ask 不应再使用 urllib.request"
        assert "urllib.error" not in source, \
            "handle_ask 不应再使用 urllib.error"

    def test_uses_openai_client(self):
        """handle_ask 函数源码应使用 LLM 后端注册表。"""
        import inspect
        from gh_trending_audio.web import api_handlers
        source = inspect.getsource(api_handlers.handle_ask)
        assert "get_auto_llm_backend" in source or "backend.get_client" in source, \
            "handle_ask 应通过注册表获取 LLM 后端（阶段4: 注册机制）"

    def test_ask_handles_missing_key(self):
        """无 API Key 时应返回友好错误。"""
        import os
        from pathlib import Path
        from gh_trending_audio.web.handlers import pipeline as pipeline_mod
        from gh_trending_audio.web import api_handlers
        from unittest.mock import MagicMock, patch

        # 创建 mock handler
        handler = MagicMock()
        handler.server = MagicMock()

        # Patch send_json 以捕获调用（阶段3: handle_ask 已移至 pipeline 模块）
        with patch.object(pipeline_mod, 'send_json') as mock_send_json:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("LLM_API_KEY", None)
                import gh_trending_audio.config as config
                config.reset_config()
                api_handlers.handle_ask(handler, Path("/tmp"), {
                    "question": "test",
                    "project": "test_project",
                    "dir": "",
                })
                mock_send_json.assert_called()
                args = mock_send_json.call_args[0]
                assert args[1] == 500 or args[1] == 404
                config.reset_config()  # 清理

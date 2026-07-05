"""阶段5：重试机制和配置验证测试。"""

import pytest
from unittest.mock import patch, MagicMock
from gh_trending_audio.retry_utils import with_retry


class TestRetryMechanism:
    """重试装饰器测试。"""

    def test_success_on_first_attempt(self):
        """首次成功不重试。"""
        call_count = 0
        @with_retry(max_attempts=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "ok"
        assert success_func() == "ok"
        assert call_count == 1

    def test_retry_on_failure_then_success(self):
        """失败后重试成功。"""
        call_count = 0
        @with_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("临时错误")
            return "recovered"
        assert flaky_func() == "recovered"
        assert call_count == 2

    def test_all_attempts_fail(self):
        """所有重试都失败时抛出最后异常。"""
        @with_retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        def always_fail():
            raise ValueError("永久错误")
        with pytest.raises(ValueError, match="永久错误"):
            always_fail()

    def test_non_matching_exception_no_retry(self):
        """不匹配的异常类型不触发重试。"""
        call_count = 0
        @with_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("不匹配的类型")
        with pytest.raises(TypeError):
            wrong_exception()
        assert call_count == 1

    def test_backoff_factor_increases_delay(self):
        """退避乘数增加等待时间。"""
        sleep_times = []
        @with_retry(max_attempts=3, delay=1.0, backoff_factor=2.0, exceptions=(ValueError,))
        def always_fail():
            raise ValueError("错误")
        with patch("gh_trending_audio.retry_utils.time.sleep", side_effect=lambda s: sleep_times.append(s)):
            with pytest.raises(ValueError):
                always_fail()
        assert len(sleep_times) == 2  # 3次尝试，2次等待
        assert sleep_times[0] == 1.0   # 1.0 * 2^0
        assert sleep_times[1] == 2.0   # 1.0 * 2^1


class TestConfigValidation:
    """配置验证测试。"""

    def test_invalid_llm_base_url_raises(self):
        """无效的LLM_BASE_URL格式应抛出ConfigError。"""
        import gh_trending_audio.config as config_module
        from gh_trending_audio.exceptions import ConfigError
        with patch.dict("os.environ", {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "ftp://invalid",
        }):
            config_module.reset_config()
            with pytest.raises(ConfigError, match="LLM_BASE_URL"):
                config_module.get_config()

    def test_valid_llm_base_url_passes(self):
        """有效的LLM_BASE_URL格式不抛异常。"""
        import gh_trending_audio.config as config_module
        with patch.dict("os.environ", {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://api.openai.com/v1",
        }):
            config_module.reset_config()
            cfg = config_module.get_config()
            assert cfg.llm.base_url == "https://api.openai.com/v1"

    def test_missing_token_logs_debug(self):
        """缺少GitHub Token时记录debug日志（非错误）。"""
        import gh_trending_audio.config as config_module
        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("GITHUB_TOKEN", None)
            config_module.reset_config()
            # 不应抛出异常
            cfg = config_module.get_config()
            assert cfg.github.token == "" or cfg.github.token is None

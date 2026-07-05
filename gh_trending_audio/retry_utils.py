"""轻量级重试工具（不依赖外部库）。

提供 ``@with_retry`` 装饰器，对外部 API 调用（GitHub/LLM/TTS）
添加指数退避重试，提升瞬时故障下的韧性。

设计目标：
  - 零外部依赖：仅使用 Python 标准库（functools/time/typing）。
  - 可配置：最大尝试次数、初始延迟、退避乘数、触发重试的异常类型。
  - 透明：被装饰函数的签名与返回值保持不变（``functools.wraps``）。
  - 可观测：每次重试与最终失败均通过集中日志器记录。

使用示例::

    from gh_trending_audio.retry_utils import with_retry

    @with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
    def fetch_api(url):
        ...
"""

from __future__ import annotations

import functools
import time
from typing import Callable, Type

from .logging_config import get_logger

logger = get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """指数退避重试装饰器。

    被装饰函数在抛出 ``exceptions`` 中任一异常时，按指数退避策略
    （``delay * backoff_factor ** attempt``）等待后重试，直至达到
    ``max_attempts`` 次后抛出最后一次异常。

    Args:
        max_attempts: 最大重试次数（含首次），默认3次。
        delay: 首次重试前等待秒数，默认1.0。
        backoff_factor: 退避乘数，每次重试等待时间 = delay * (backoff_factor ** attempt)。
        exceptions: 触发重试的异常类型元组。

    Returns:
        装饰器函数。

    Example:
        @with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def fetch_api(url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait = delay * (backoff_factor ** attempt)
                        logger.warning(
                            "第%d次尝试失败: %s，%.1f秒后重试（共%d次）",
                            attempt + 1, e, wait, max_attempts,
                        )
                        time.sleep(wait)
                    else:
                        logger.error("重试%d次后仍失败: %s", max_attempts, e)
            raise last_exception
        return wrapper
    return decorator

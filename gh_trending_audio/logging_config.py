"""集中化日志配置（阶段1: 秩序化）。

消除项目中 7 个模块各自 ``console = Console()`` 的散落日志，
统一为标准库 ``logging`` 模块 + Rich 格式化输出。

使用方式::

    from gh_trending_audio.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("信息")
    logger.warning("警告")
    logger.error("错误", exc_info=True)

配置通过环境变量 ``GTA_LOG_LEVEL`` 控制（默认 INFO）。
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Literal

_LOG_LEVEL = os.environ.get("GTA_LOG_LEVEL", "INFO").upper()
_LOG_FORMAT = os.environ.get("GTA_LOG_FORMAT", "rich")

_configured = False
_loggers: dict[str, logging.Logger] = {}


def _configure_root() -> None:
    """配置根日志处理器（仅执行一次）。"""
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, _LOG_LEVEL, logging.INFO)

    if _LOG_FORMAT == "plain":
        handler: logging.Handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    else:
        # Rich 格式化（默认）
        try:
            from rich.logging import RichHandler

            handler = RichHandler(
                level=level,
                show_path=False,
                show_time=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
            )
        except ImportError:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
            )

    handler.setLevel(level)
    root = logging.getLogger("gh_trending_audio")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    """获取模块级日志器。

    Args:
        name: 通常传 ``__name__``，如 ``gh_trending_audio.tts_engine``

    Returns:
        配置好的 Logger 实例
    """
    _configure_root()

    # 确保名称在 gh_trending_audio 命名空间下
    if not name.startswith("gh_trending_audio"):
        name = f"gh_trending_audio.{name}"

    if name not in _loggers:
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
        _loggers[name] = logger

    return _loggers[name]


def set_log_level(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]) -> None:
    """运行时动态调整日志级别（测试用）。"""
    global _LOG_LEVEL
    _LOG_LEVEL = level
    numeric = getattr(logging, level, logging.INFO)
    logging.getLogger("gh_trending_audio").setLevel(numeric)
    for logger in _loggers.values():
        logger.setLevel(numeric)

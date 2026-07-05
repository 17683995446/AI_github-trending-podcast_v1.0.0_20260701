"""API 处理器共享基础设施。

提供跨域共享的：
- HTTP 工具函数（send_json / send_xml / send_file_download）
- 缓存实例（文件树、文件内容）
- 日志器
- 异常类型

各子模块通过 ``from ._common import *`` 或具名导入复用。
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ..http_utils import send_json, send_xml, send_file_download
from ..markdown_utils import build_repo_from_md
from ..project_scanner import get_project_detail, scan_projects

from ...exceptions import (
    CodeSearchError, FileOperationError, GitHubAPIError,
    LLMError, NetworkError, PipelineError, TTSError,
)
from ...logging_config import get_logger
from ...constants import API_CACHE_MAXSIZE, API_CACHE_TTL, STATIC_CACHE_MAXSIZE, STATIC_CACHE_TTL

logger = get_logger(__name__)

# ── 共享缓存 ──
try:
    from cachetools import TTLCache
    _FILETREE_CACHE: TTLCache = TTLCache(maxsize=API_CACHE_MAXSIZE, ttl=API_CACHE_TTL)
    _FILE_CONTENT_CACHE: TTLCache = TTLCache(maxsize=STATIC_CACHE_MAXSIZE, ttl=STATIC_CACHE_TTL)
except ImportError:
    _FILETREE_CACHE: dict = {}
    _FILE_CONTENT_CACHE: dict = {}

__all__ = [
    # HTTP 工具
    "send_json", "send_xml", "send_file_download",
    # 核心工具
    "build_repo_from_md", "get_project_detail", "scan_projects",
    # 异常
    "CodeSearchError", "FileOperationError", "GitHubAPIError",
    "LLMError", "NetworkError", "PipelineError", "TTSError",
    # 日志
    "logger",
    # 缓存
    "_FILETREE_CACHE", "_FILE_CONTENT_CACHE",
]

"""项目扫描器（兼容垫片）。

此模块已上移到 ``gh_trending_audio.project_scanner``（核心层）。
本文件仅保持向后兼容，re-export 核心模块的所有公共函数。
"""

from ..project_scanner import (  # noqa: F401
    get_audio_duration,
    scan_projects,
    get_project_detail,
)

__all__ = ["get_audio_duration", "scan_projects", "get_project_detail"]

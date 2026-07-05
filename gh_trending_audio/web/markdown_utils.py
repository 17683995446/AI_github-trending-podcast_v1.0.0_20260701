"""Markdown 解析与转换工具（兼容垫片）。

此模块已上移到 ``gh_trending_audio.markdown_utils``（核心层）。
本文件仅保持向后兼容，re-export 核心模块的所有公共函数。
"""

from ..markdown_utils import (  # noqa: F401
    parse_md_metadata,
    markdown_to_html,
    build_repo_from_md,
)

__all__ = ["parse_md_metadata", "markdown_to_html", "build_repo_from_md"]

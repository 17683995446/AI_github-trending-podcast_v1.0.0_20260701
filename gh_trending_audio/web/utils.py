"""Web 仪表盘工具函数（兼容层）。

阶段5 拆分后，原 ``utils.py`` 的功能分散到三个聚焦模块：
  - ``markdown_utils.py``  Markdown 解析与转换
  - ``project_scanner.py`` 项目扫描与详情
  - ``code_search.py``     代码搜索

本文件保留为向后兼容的重新导出层，现有 ``from .utils import xxx``
调用无需修改。新代码请直接从聚焦模块导入。
"""
# DEPRECATED: 此文件为纯兼容垫片（重新导出层），仅被测试文件引用。计划在后续版本中移除。

from __future__ import annotations

# ── Markdown 工具 ──────────────────────────────────────────────────
from .markdown_utils import (
    parse_md_metadata,
    markdown_to_html,
    build_repo_from_md,
)

# ── 项目扫描 ──────────────────────────────────────────────────────
from .project_scanner import (
    get_audio_duration,
    scan_projects,
    get_project_detail,
)

# ── 代码搜索 ──────────────────────────────────────────────────────
from .code_search import (
    CodeSearchUnavailable,
    normalize_repo_slug,
    github_api_get,
    github_code_search,
    ext_matches_language,
    classify_line,
    regex_search_in_xml,
    local_code_search,
)

__all__ = [
    # markdown_utils
    "parse_md_metadata",
    "markdown_to_html",
    "build_repo_from_md",
    # project_scanner
    "get_audio_duration",
    "scan_projects",
    "get_project_detail",
    # code_search
    "CodeSearchUnavailable",
    "normalize_repo_slug",
    "github_api_get",
    "github_code_search",
    "ext_matches_language",
    "classify_line",
    "regex_search_in_xml",
    "local_code_search",
]

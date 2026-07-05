"""API 处理器包（阶段3: 从 api_handlers.py 按领域拆分）。

按业务领域拆分为独立子模块，每个模块负责一组相关 API 端点：

- ``projects``       — 项目列表、详情、统计、状态、删除、快捷路由
- ``pipeline``       — 流水线启动、多仓库对比、项目问答、入门指南
- ``github_browse``  — GitHub README、文件树、文件内容、社区洞察、代码搜索
- ``files``          — 本地文件下载/预览
- ``feed``           — RSS 播客订阅源、OPML、订阅统计
- ``media_export``   — 字幕生成、多格式导出、批量导出
- ``system``         — 系统后端状态、代码智能、用户偏好
- ``search_compare`` — 全文搜索、搜索建议、重建索引、项目对比
"""

from __future__ import annotations

# 项目数据与管理
from .projects import (
    serve_api_projects,
    serve_api_project,
    serve_api_stats,
    serve_api_status,
    serve_sse_events,
    delete_project,
    find_project_by_name,
    handle_quick_route,
)

# 流水线任务
from .pipeline import (
    start_pipeline,
    start_comparison,
    handle_ask,
    handle_onboarding,
)

# GitHub 仓库浏览
from .github_browse import (
    serve_api_readme,
    serve_api_filetree,
    serve_api_file,
    serve_api_community,
    handle_search_code,
)

# 本地文件服务
from .files import serve_file

# 播客 RSS 订阅源
from .feed import (
    serve_podcast_feed,
    serve_opml,
    serve_feed_stats,
)

# 字幕与导出
from .media_export import (
    serve_subtitle,
    serve_export,
    serve_batch_export,
)

# 系统状态与代码智能
from .system import (
    serve_system_backends,
    serve_code_symbols,
    serve_code_intel_status,
    serve_preferences_schema,
)

# 全文搜索与项目对比
from .search_compare import (
    serve_search,
    serve_search_suggestions,
    serve_search_reindex,
    serve_compare_projects,
)

__all__ = [
    # projects
    "serve_api_projects", "serve_api_project", "serve_api_stats",
    "serve_api_status", "serve_sse_events", "delete_project",
    "find_project_by_name", "handle_quick_route",
    # pipeline
    "start_pipeline", "start_comparison", "handle_ask", "handle_onboarding",
    # github_browse
    "serve_api_readme", "serve_api_filetree", "serve_api_file",
    "serve_api_community", "handle_search_code",
    # files
    "serve_file",
    # feed
    "serve_podcast_feed", "serve_opml", "serve_feed_stats",
    # media_export
    "serve_subtitle", "serve_export", "serve_batch_export",
    # system
    "serve_system_backends", "serve_code_symbols",
    "serve_code_intel_status", "serve_preferences_schema",
    # search_compare
    "serve_search", "serve_search_suggestions",
    "serve_search_reindex", "serve_compare_projects",
]

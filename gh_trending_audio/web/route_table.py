"""声明式路由表（阶段5: 替代 if/elif 路由链）。

通过数据驱动的路由表实现 URL 分发，新增路由只需在表中添加一行条目，
无需修改分发逻辑。遵循开闭原则（对扩展开放，对修改关闭）。

路由表结构::

    RouteEntry(
        pattern="/api/projects",       # 精确匹配
        handler=api_handlers.serve_api_projects,
        args=lambda h, p, d, pp: (h, d),  # 参数提取器
    )
    RouteEntry(
        pattern="/api/project/*",      # 前缀匹配（* 通配剩余路径）
        handler=api_handlers.serve_api_project,
        args=lambda h, p, d, pp: (h, d, pp[0], pp[1]) if len(pp) == 2 else (h, d, "", pp[0]),
    )
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Callable, Any

from . import api_handlers
from .http_utils import read_post_body, send_json, send_xml
from .renderer import render_dashboard, render_player, render_project
from ..constants import STATIC_CACHE_MAX_AGE

__all__ = [
    # 常量
    "BASE_DIR",
    "OUTPUT_DIR",
    # 路由条目
    "RouteEntry",
    # 路由分发
    "route_get",
    "route_post",
    "route_delete",
    # 路由管理
    "list_routes",
    "add_route",
]


# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
OUTPUT_DIR = BASE_DIR


def _parse_path_parts(path: str, prefix: str) -> list[str]:
    """从路径中提取前缀后的分段。"""
    remaining = urllib.parse.unquote(path.replace(prefix, "", 1))
    # 去除前导斜杠，避免 split 产生空首元素
    if remaining.startswith("/"):
        remaining = remaining[1:]
    return remaining.split("/", 1) if remaining else [""]


# ═══════════════════════════════════════════════════════════════════
# 路由条目定义
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RouteEntry:
    """单条路由声明。

    Attributes:
        pattern: URL 模式。精确匹配用完整路径（如 "/api/projects"），
                 前缀匹配用 ``/*`` 结尾（如 "/api/project/*"）。
        handler: 处理函数。
        args: 参数提取器，接收 (handler, parsed, output_dir, path_parts)，
              返回调用 handler 所需的位置参数元组。
              path_parts 为前缀匹配时 ``*`` 部分的路径分段。
    """
    pattern: str
    handler: Callable
    args: Callable[[BaseHTTPRequestHandler, Any, Path, list[str]], tuple]

    @property
    def is_prefix(self) -> bool:
        """是否为前缀匹配路由。"""
        return self.pattern.endswith("/*")

    @property
    def prefix(self) -> str:
        """前缀匹配时的前缀字符串（不含 /*）。"""
        return self.pattern[:-2] if self.is_prefix else self.pattern

    def matches(self, path: str) -> tuple[bool, list[str]]:
        """检查路径是否匹配此路由。

        Returns:
            (是否匹配, 路径分段列表)
        """
        if self.is_prefix:
            if path.startswith(self.prefix):
                parts = _parse_path_parts(path, self.prefix)
                return True, parts
            return False, []
        else:
            if path == self.pattern:
                return True, []
            return False, []


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _qs(parsed) -> dict:
    """解析查询字符串。"""
    return urllib.parse.parse_qs(parsed.query)


def _post_body(handler: BaseHTTPRequestHandler) -> dict:
    """读取 POST 请求体。"""
    return read_post_body(handler)


# ── 参数提取器 ──

# 透传所有参数（用于 lambda 处理器）
_args_all = lambda h, p, d, pp: (h, p, d, pp)
# 简单路由：handler(handler, output_dir)
_args_outdir = lambda h, p, d, pp: (h, d)
# 简单路由：handler(handler)
_args_handler_only = lambda h, p, d, pp: (h,)
# 查询路由：handler(handler, output_dir, query_dict)
_args_outdir_qs = lambda h, p, d, pp: (h, d, _qs(p))
# 查询路由：handler(handler, query_dict)
_args_qs_only = lambda h, p, d, pp: (h, _qs(p))
# POST 查询路由：handler(handler, output_dir, body)
_args_outdir_body = lambda h, p, d, pp: (h, d, _post_body(h))
# POST 查询路由：handler(handler, body)
_args_body_only = lambda h, p, d, pp: (h, _post_body(h))


def _args_two_parts_outdir(h, p, d, pp):
    """两段路径 + output_dir：handler(handler, output_dir, part0, part1)。"""
    if len(pp) == 2:
        return (h, d, pp[0], pp[1])
    return (h, d, "", pp[0])


def _args_two_parts_outdir_qs(h, p, d, pp):
    """两段路径 + output_dir + query：handler(handler, output_dir, part0, part1, query)。"""
    if len(pp) == 2:
        return (h, d, pp[0], pp[1], _qs(p))
    return (h, d, "", pp[0], _qs(p))


# ═══════════════════════════════════════════════════════════════════
# GET 路由表
# ═══════════════════════════════════════════════════════════════════

_GET_ROUTES: list[RouteEntry] = [
    # ── 页面路由 ──
    RouteEntry("/", lambda h, p, d, pp: h._send_html(render_dashboard(d)), _args_all),
    RouteEntry("/dashboard", lambda h, p, d, pp: h._send_html(render_dashboard(d)), _args_all),
    RouteEntry("/player", lambda h, p, d, pp: h._send_html(render_player()), _args_all),

    # ── 项目 API ──
    RouteEntry("/api/projects", api_handlers.serve_api_projects, _args_outdir),
    RouteEntry("/api/project/*", api_handlers.serve_api_project, _args_two_parts_outdir),
    RouteEntry("/project/*",
               lambda h, p, d, pp: h._send_html(render_project(d, pp[0], pp[1])) if len(pp) == 2
               else h._send_html(render_project(d, "", pp[0])),
               _args_all),

    # ── 快捷路由 ──
    RouteEntry("/r/*", lambda h, p, d, pp: api_handlers.handle_quick_route(h, d, p), _args_all),

    # ── 文件服务 ──
    RouteEntry("/file/*",
               lambda h, p, d, pp: api_handlers.serve_file(h, d, urllib.parse.unquote(
                   p.path.replace("/file/", ""))),
               _args_all),

    # ── 统计与状态 ──
    RouteEntry("/api/stats", api_handlers.serve_api_stats, _args_outdir),
    RouteEntry("/api/status", api_handlers.serve_api_status, _args_handler_only),
    RouteEntry("/api/events", api_handlers.serve_sse_events, _args_handler_only),

    # ── 流水线 ──
    RouteEntry("/api/run", api_handlers.start_pipeline, _args_outdir_qs),

    # ── GitHub 浏览 ──
    RouteEntry("/api/filetree", api_handlers.serve_api_filetree, _args_qs_only),
    RouteEntry("/api/file", api_handlers.serve_api_file, _args_qs_only),
    RouteEntry("/api/community", api_handlers.serve_api_community, _args_qs_only),
    RouteEntry("/api/readme", api_handlers.serve_api_readme, _args_qs_only),

    # ── 播客订阅 ──
    RouteEntry("/feed.xml", api_handlers.serve_podcast_feed, _args_outdir),
    RouteEntry("/opml.xml", api_handlers.serve_opml, _args_outdir),
    RouteEntry("/api/feed-stats", api_handlers.serve_feed_stats, _args_outdir),

    # ── 系统与代码智能 ──
    RouteEntry("/api/system-backends", api_handlers.serve_system_backends, _args_outdir),
    RouteEntry("/api/code-intel-status", api_handlers.serve_code_intel_status, _args_outdir),
    RouteEntry("/api/code-symbols",
               lambda h, p, d, pp: api_handlers.serve_code_symbols(h, d, _qs(p)),
               _args_all),

    # ── 搜索 ──
    RouteEntry("/api/search", api_handlers.serve_search, _args_outdir_qs),
    RouteEntry("/api/search-suggestions", api_handlers.serve_search_suggestions, _args_outdir_qs),
    RouteEntry("/api/search-reindex", api_handlers.serve_search_reindex, _args_outdir),

    # ── 对比 ──
    RouteEntry("/api/compare-projects", api_handlers.serve_compare_projects, _args_outdir_qs),

    # ── 偏好与导出 ──
    RouteEntry("/api/preferences-schema", api_handlers.serve_preferences_schema, _args_outdir),
    RouteEntry("/api/batch-export", api_handlers.serve_batch_export, _args_outdir_qs),

    # ── 字幕与导出 ──
    RouteEntry("/api/subtitle/*", api_handlers.serve_subtitle, _args_two_parts_outdir_qs),
    RouteEntry("/api/export/*", api_handlers.serve_export, _args_two_parts_outdir_qs),

    # ── PWA ──
    RouteEntry("/manifest.json",
               lambda h, p, d, pp: _serve_pwa_manifest(h),
               _args_all),
    RouteEntry("/sw.js",
               lambda h, p, d, pp: _serve_pwa_sw(h),
               _args_all),
    RouteEntry("/icon-512.jpg",
               lambda h, p, d, pp: _serve_icon(h),
               _args_all),
]


# ═══════════════════════════════════════════════════════════════════
# POST 路由表
# ═══════════════════════════════════════════════════════════════════

_POST_ROUTES: list[RouteEntry] = [
    RouteEntry("/api/run", api_handlers.start_pipeline, _args_outdir_body),
    RouteEntry("/api/compare", api_handlers.start_comparison, _args_outdir_body),
    RouteEntry("/api/ask", api_handlers.handle_ask, _args_outdir_body),
    RouteEntry("/api/search-code", api_handlers.handle_search_code, _args_body_only),
    RouteEntry("/api/onboarding", api_handlers.handle_onboarding, _args_outdir_body),
    RouteEntry("/api/delete/*", api_handlers.delete_project, _args_two_parts_outdir),
]


# ═══════════════════════════════════════════════════════════════════
# DELETE 路由表
# ═══════════════════════════════════════════════════════════════════

_DELETE_ROUTES: list[RouteEntry] = [
    RouteEntry("/api/project/*", api_handlers.delete_project, _args_two_parts_outdir),
]


# ═══════════════════════════════════════════════════════════════════
# PWA 辅助函数
# ═══════════════════════════════════════════════════════════════════

def _serve_pwa_manifest(handler: BaseHTTPRequestHandler) -> None:
    from .pwa import get_manifest
    send_xml(handler, get_manifest(), content_type="application/manifest+json; charset=utf-8")


def _serve_pwa_sw(handler: BaseHTTPRequestHandler) -> None:
    from .pwa import get_service_worker
    send_xml(handler, get_service_worker(), content_type="application/javascript; charset=utf-8")


def _serve_icon(handler: BaseHTTPRequestHandler) -> None:
    icon_path = Path(__file__).parent / "static" / "icon-512.jpg"
    if icon_path.exists():
        data = icon_path.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", "image/jpeg")
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Cache-Control", f"public, max-age={STATIC_CACHE_MAX_AGE}")
        handler.end_headers()
        handler.wfile.write(data)
    else:
        send_json(handler, 404, {"error": "Icon not found"})


# ═══════════════════════════════════════════════════════════════════
# 路由分发器
# ═══════════════════════════════════════════════════════════════════

def _dispatch(routes: list[RouteEntry], handler: BaseHTTPRequestHandler,
              parsed: Any, output_dir: Path = OUTPUT_DIR) -> bool:
    """在路由表中查找并分发请求。

    Returns:
        True 如果找到匹配路由，False 如果未匹配
    """
    path = parsed.path
    for entry in routes:
        matched, parts = entry.matches(path)
        if matched:
            args = entry.args(handler, parsed, output_dir, parts)
            entry.handler(*args)
            return True
    return False


def route_get(handler: BaseHTTPRequestHandler, parsed: Any) -> None:
    """GET 请求路由分发（声明式路由表驱动）。"""
    if not _dispatch(_GET_ROUTES, handler, parsed):
        send_json(handler, 404, {"error": "Not found"})


def route_post(handler: BaseHTTPRequestHandler, parsed: Any) -> None:
    """POST 请求路由分发（声明式路由表驱动）。"""
    if not _dispatch(_POST_ROUTES, handler, parsed):
        send_json(handler, 404, {"error": "Not found"})


def route_delete(handler: BaseHTTPRequestHandler, parsed: Any) -> None:
    """DELETE 请求路由分发（声明式路由表驱动）。"""
    if not _dispatch(_DELETE_ROUTES, handler, parsed):
        send_json(handler, 404, {"error": "Not found"})


# ═══════════════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════════════

def list_routes(method: str = "GET") -> list[dict[str, Any]]:
    """列出所有已注册的路由（用于调试和文档）。

    Args:
        method: HTTP 方法（"GET"/"POST"/"DELETE"）

    Returns:
        路由信息列表
    """
    routes_map = {"GET": _GET_ROUTES, "POST": _POST_ROUTES, "DELETE": _DELETE_ROUTES}
    routes = routes_map.get(method.upper(), [])
    return [
        {
            "pattern": entry.pattern,
            "type": "prefix" if entry.is_prefix else "exact",
            "handler": getattr(entry.handler, "__name__", str(entry.handler)),
        }
        for entry in routes
    ]


def add_route(method: str, pattern: str, handler: Callable,
              args: Callable = _args_handler_only) -> None:
    """运行时添加路由（用于插件扩展）。

    Args:
        method: HTTP 方法
        pattern: URL 模式
        handler: 处理函数
        args: 参数提取器
    """
    entry = RouteEntry(pattern=pattern, handler=handler, args=args)
    routes_map = {
        "GET": _GET_ROUTES, "POST": _POST_ROUTES, "DELETE": _DELETE_ROUTES
    }
    routes = routes_map.get(method.upper())
    if routes is None:
        raise ValueError(f"不支持的 HTTP 方法: {method}")
    routes.append(entry)

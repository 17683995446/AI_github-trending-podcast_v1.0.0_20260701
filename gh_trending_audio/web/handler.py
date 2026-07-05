"""HTTP request handler for the web dashboard.

重构后的架构（Phase 1: 秩序化）：
  - ``DashboardHandler`` 保留 HTTP 请求/响应周期的 ``self`` 方法
  - 路由分发 → ``routes.py``
  - API 处理器 → ``api_handlers.py``
  - HTML 渲染 → ``renderer.py``
  - HTTP 工具方法 → ``http_utils.py``
  - 纯辅助函数 → ``utils.py``
"""

from __future__ import annotations

import urllib.parse
from http.server import BaseHTTPRequestHandler

from .routes import route_get, route_post, route_delete
from .http_utils import send_html, send_json, send_redirect


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 — 仅负责 HTTP 协议层，路由分发委托给 routes 模块。"""

    # 使用 HTTP/1.1 协议版本，支持 keep-alive 连接
    # 解决代理转发时 "connection closed before message completed" 错误
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args) -> None:
        """记录请求日志（用于调试代理转发问题）。"""
        from ..logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        """处理GET请求，委托给路由分发器。"""
        parsed = urllib.parse.urlparse(self.path)
        route_get(self, parsed)

    def do_POST(self) -> None:
        """处理POST请求，委托给路由分发器。"""
        parsed = urllib.parse.urlparse(self.path)
        route_post(self, parsed)

    def do_DELETE(self) -> None:
        """处理DELETE请求，委托给路由分发器。"""
        parsed = urllib.parse.urlparse(self.path)
        route_delete(self, parsed)

    # ------------------------------------------------------------------
    # HTTP 辅助方法（委托给 http_utils 模块）
    # ------------------------------------------------------------------

    def _send_html(self, html: str, status: int = 200):
        send_html(self, html, status)

    def _send_json(self, status: int, obj: dict):
        send_json(self, status, obj)

    def _send_redirect(self, location: str, status: int = 302):
        send_redirect(self, location, status)

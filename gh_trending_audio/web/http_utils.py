"""HTTP 协议层工具方法（Phase 1: 从 handler.py 拆分）。

将 HTTP 响应发送逻辑从 DashboardHandler 中提取为独立函数，
消除 handler 与 HTTP 细节的耦合。
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


def send_html(handler: BaseHTTPRequestHandler, html: str, status: int = 200) -> None:
    """发送 HTML 响应。"""
    data = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(data)


def send_json(handler: BaseHTTPRequestHandler, status: int, obj: dict) -> None:
    """发送 JSON 响应。"""
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(data)


def send_xml(handler: BaseHTTPRequestHandler, xml: str, status: int = 200,
             content_type: str = "application/xml; charset=utf-8") -> None:
    """发送 XML 响应（用于 RSS/OPML 等订阅源）。"""
    data = xml.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(data)


def send_file_download(handler: BaseHTTPRequestHandler, data: bytes,
                       filename: str, content_type: str = "application/octet-stream") -> None:
    """发送文件下载响应（带 Content-Disposition）。"""
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(data)


def send_redirect(handler: BaseHTTPRequestHandler, location: str, status: int = 302) -> None:
    """发送 HTTP 重定向。"""
    handler.send_response(status)
    handler.send_header("Location", location)
    handler.send_header("Content-Length", "0")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Connection", "close")
    handler.end_headers()


def read_post_body(handler: BaseHTTPRequestHandler) -> dict:
    """读取并解析 POST 请求的 JSON body。

    Returns:
        解析后的字典，解析失败返回空字典。
    """
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length).decode("utf-8")
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {}

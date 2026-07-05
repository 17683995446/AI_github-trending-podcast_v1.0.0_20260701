"""播客 RSS 订阅源 API 处理器。"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import send_json, send_xml

__all__ = [
    "_get_base_url",
    "serve_podcast_feed",
    "serve_opml",
    "serve_feed_stats",
]


def _get_base_url(handler: BaseHTTPRequestHandler) -> str:
    """从请求头构建服务器基础 URL。"""
    host = handler.headers.get("Host", "localhost:8000")
    return f"http://{host}"


def serve_podcast_feed(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """生成并返回 RSS 2.0 播客订阅源。"""
    from ...podcast_feed import generate_podcast_feed

    base_url = _get_base_url(handler)
    xml = generate_podcast_feed(output_dir, base_url=base_url)
    send_xml(handler, xml, content_type="application/rss+xml; charset=utf-8")


def serve_opml(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """生成并返回 OPML 订阅列表。"""
    from ...podcast_feed import generate_opml

    base_url = _get_base_url(handler)
    xml = generate_opml(output_dir, base_url=base_url)
    send_xml(handler, xml)


def serve_feed_stats(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回播客订阅源统计数据（JSON）。"""
    from ...podcast_feed import get_feed_stats

    stats = get_feed_stats(output_dir)
    send_json(handler, 200, stats)

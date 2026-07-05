"""系统状态与代码智能 API 处理器。"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import send_json

__all__ = [
    "serve_system_backends",
    "serve_code_symbols",
    "serve_code_intel_status",
    "serve_preferences_schema",
]


def serve_system_backends(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回系统可用的 LLM/TTS 后端信息。"""
    from ...local_backends import get_system_backends
    backends = get_system_backends()
    send_json(handler, 200, backends)


def serve_code_symbols(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """使用 tree-sitter 提取代码符号（函数/类/方法）。"""
    from ...code_intel import extract_symbols

    repo = params.get("repo", [""])[0]
    path = params.get("path", [""])[0]
    if not repo or not path:
        send_json(handler, 400, {"error": "Missing repo or path parameter"})
        return

    from ...github_client import get_github_client
    try:
        client = get_github_client()
        content = client.get_file_content(repo, path)
        if not content:
            send_json(handler, 404, {"error": "File not found or empty"})
            return
        symbols = extract_symbols(path, content)
        send_json(handler, 200, {"symbols": symbols, "file": path})
    except Exception as e:
        send_json(handler, 500, {"error": str(e)})


def serve_code_intel_status(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回代码智能工具状态。"""
    from ...code_intel import get_code_intel_status
    status = get_code_intel_status()
    send_json(handler, 200, status)


def serve_preferences_schema(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回偏好字段定义（前端用于渲染设置表单）。"""
    from ...user_prefs import get_preferences_schema, DEFAULT_PREFERENCES
    send_json(handler, 200, {
        "schema": get_preferences_schema(),
        "defaults": DEFAULT_PREFERENCES,
    })

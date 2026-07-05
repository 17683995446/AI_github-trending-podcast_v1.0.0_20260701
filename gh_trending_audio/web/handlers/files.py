"""本地文件服务 API 处理器。"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import send_json

__all__ = ["serve_file"]


def serve_file(handler: BaseHTTPRequestHandler, output_dir: Path, filepath: str) -> None:
    """提供文件下载/预览（含路径穿越防护）。"""
    safe_path = Path(filepath)
    full_path = (output_dir / safe_path).resolve()
    try:
        full_path.relative_to(output_dir.resolve())
    except ValueError:
        send_json(handler, 403, {"error": "Access denied: path traversal detected"})
        return

    if not full_path.exists() or not full_path.is_file():
        send_json(handler, 404, {"error": "File not found"})
        return

    ext = full_path.suffix.lower()
    content_type = {
        ".mp3": "audio/mpeg",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")

    with open(full_path, "rb") as f:
        data = f.read()

    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Content-Disposition", f"inline; filename=\"{full_path.name}\"")
    handler.end_headers()
    handler.wfile.write(data)

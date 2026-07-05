"""字幕生成与多格式导出 API 处理器。"""

from __future__ import annotations

import io
import zipfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import send_json, send_file_download, scan_projects

__all__ = [
    "serve_subtitle",
    "serve_export",
    "serve_batch_export",
]


def serve_subtitle(handler: BaseHTTPRequestHandler, output_dir: Path,
                   dir_name: str, proj_name: str, params: dict) -> None:
    """生成并返回 SRT/VTT 字幕文件。"""
    from ...subtitle_gen import generate_subtitle_for_project

    fmt = params.get("format", ["srt"])[0].lower()
    if fmt not in ("srt", "vtt"):
        fmt = "srt"

    content = generate_subtitle_for_project(output_dir, dir_name, proj_name, fmt=fmt)
    if content is None:
        send_json(handler, 404, {"error": "Project or script not found"})
        return

    content_type = "text/vtt" if fmt == "vtt" else "application/x-subrip"
    filename = f"{proj_name}.{fmt}"
    send_file_download(
        handler,
        content.encode("utf-8"),
        filename,
        content_type=content_type,
    )


def serve_export(handler: BaseHTTPRequestHandler, output_dir: Path,
                 dir_name: str, proj_name: str, params: dict) -> None:
    """导出项目为 JSON/ZIP/PDF/EPUB 格式。"""
    from ...exporter import export_project

    fmt = params.get("format", ["json"])[0].lower()
    data, filename, content_type = export_project(output_dir, dir_name, proj_name, fmt=fmt)
    if data is None:
        send_json(handler, 404, {"error": "Project not found or format unsupported"})
        return

    send_file_download(handler, data, filename, content_type=content_type)


def serve_batch_export(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """批量导出所有项目为 ZIP。"""
    from ...exporter import export_zip

    projects = scan_projects(output_dir)
    projects = [p for p in projects if p.get("has_audio") or p.get("has_md")]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in projects:
            dir_name = p.get("dir", "")
            name = p.get("name", "")
            if not dir_name or not name:
                continue
            try:
                data = export_zip(output_dir, dir_name, name)
                if data:
                    zf.writestr(f"{name}.zip", data)
            except (OSError, ValueError):
                pass

    result = buf.getvalue()
    send_file_download(handler, result, "all_projects.zip", "application/zip")

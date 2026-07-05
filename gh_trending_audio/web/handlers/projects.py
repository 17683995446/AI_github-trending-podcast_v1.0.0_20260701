"""项目数据与管理 API 处理器。

包含项目列表、详情、统计、状态、删除、快捷路由等端点。
"""

from __future__ import annotations

import json
import shutil
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import (
    send_json, scan_projects, get_project_detail, logger,
)

__all__ = [
    "serve_api_projects",
    "serve_api_project",
    "serve_api_stats",
    "serve_api_status",
    "serve_sse_events",
    "delete_project",
    "find_project_by_name",
    "handle_quick_route",
]


def serve_api_projects(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回所有项目列表（JSON）。"""
    projects = scan_projects(output_dir)
    send_json(handler, 200, {"projects": projects, "total": len(projects)})


def serve_api_project(handler: BaseHTTPRequestHandler, output_dir: Path,
                      dir_name: str, proj_name: str) -> None:
    """返回单个项目详情（JSON）。"""
    project = get_project_detail(output_dir, dir_name, proj_name)
    if project:
        send_json(handler, 200, project)
    else:
        send_json(handler, 404, {"error": "Project not found"})


def serve_api_stats(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """返回统计数据。"""
    projects = scan_projects(output_dir)
    total_md = sum(1 for p in projects if p.get("has_md"))
    total_script = sum(1 for p in projects if p.get("has_script"))
    total_audio = sum(1 for p in projects if p.get("has_audio"))
    total_size = sum(p.get("total_size", 0) for p in projects)

    send_json(handler, 200, {
        "total_projects": len(projects),
        "total_markdown": total_md,
        "total_scripts": total_script,
        "total_audio": total_audio,
        "total_size_kb": round(total_size / 1024, 1),
    })


def serve_api_status(handler: BaseHTTPRequestHandler) -> None:
    """返回任务状态。"""
    send_json(handler, 200, {
        "running": getattr(handler.server, "pipeline_running", False),
        "last_result": getattr(handler.server, "last_result", None),
        "last_error": getattr(handler.server, "last_error", None),
    })


def serve_sse_events(handler: BaseHTTPRequestHandler) -> None:
    """GET /api/events — Server-Sent Events 实时进度推送。"""
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()

    last_status = None
    try:
        while True:
            running = getattr(handler.server, "pipeline_running", False)
            last_result = getattr(handler.server, "last_result", None)
            last_error = getattr(handler.server, "last_error", None)

            current_status = {
                "running": running,
                "last_result": last_result,
                "last_error": last_error,
            }

            if current_status != last_status:
                event_data = json.dumps(current_status, ensure_ascii=False)
                handler.wfile.write(f"data: {event_data}\n\n".encode("utf-8"))
                handler.wfile.flush()
                last_status = current_status.copy()

            handler.wfile.write(b": heartbeat\n\n")
            handler.wfile.flush()
            time.sleep(2)
    except (BrokenPipeError, ConnectionResetError):
        pass  # 客户端断开连接，正常退出
    except (OSError, UnicodeDecodeError):
        logger.debug("SSE 事件流写入失败", exc_info=True)


def delete_project(handler: BaseHTTPRequestHandler, output_dir: Path,
                   dir_name: str, proj_name: str) -> None:
    """删除项目的所有文件（md、script、mp3）。"""
    if not dir_name:
        projects = scan_projects(output_dir)
        for p in projects:
            if p["name"] == proj_name:
                dir_name = p["dir"]
                break

    if not dir_name:
        send_json(handler, 404, {"error": "项目未找到"})
        return

    proj_dir = output_dir / dir_name
    if not proj_dir.exists() or not proj_dir.is_dir():
        send_json(handler, 404, {"error": "目录不存在"})
        return

    deleted = []
    for suffix in [".md", "_script.txt", ".mp3"]:
        filepath = proj_dir / f"{proj_name}{suffix}"
        if filepath.exists():
            filepath.unlink()
            deleted.append(filepath.name)

    for f in proj_dir.iterdir():
        if f.name.startswith(proj_name) and f.name.endswith(".mp3") and "_seg" in f.name:
            f.unlink()
            deleted.append(f.name)

    remaining = list(proj_dir.iterdir())
    if not remaining:
        shutil.rmtree(proj_dir)

    send_json(handler, 200, {"deleted": deleted, "project": proj_name})


def find_project_by_name(output_dir: Path, name: str) -> dict | None:
    """按项目名快速查找已存在的项目（优化版，避免 ffprobe 开销）。"""
    if not name:
        return None
    try:
        out_dirs = [d for d in output_dir.iterdir()
                    if d.is_dir() and d.name.startswith("output")]
    except OSError:
        logger.debug("目录扫描失败", exc_info=True)
        return None

    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0

    best: tuple[float, Path, str] | None = None
    for d in out_dirs:
        f = d / f"{name}.md"
        if f.exists():
            m = _mtime(f)
            if best is None or m > best[0]:
                best = (m, d, name)
    if best:
        return {"dir": best[1].name, "name": best[2]}

    low = name.lower()
    for d in out_dirs:
        try:
            for f in d.iterdir():
                if f.suffix == ".md" and f.stem.lower() == low:
                    m = _mtime(f)
                    if best is None or m > best[0]:
                        best = (m, d, f.stem)
        except (OSError, UnicodeDecodeError):
            logger.debug("文件匹配失败", exc_info=True)
            continue
    if best:
        return {"dir": best[1].name, "name": best[2]}
    return None


def handle_quick_route(handler: BaseHTTPRequestHandler, output_dir: Path, parsed) -> None:
    """快捷 URL 跳转 /r/owner/repo 或 /r/owner_repo。"""
    import urllib.parse as up

    raw = up.unquote(parsed.path[len("/r/"):]).strip().strip("/")
    if not raw:
        handler._send_redirect("/")
        return

    if "/" in raw:
        segs = [s for s in raw.split("/") if s]
        if len(segs) >= 2:
            owner, repo = segs[0], segs[1]
            proj_name = f"{owner}_{repo}"
            slug = f"{owner}/{repo}"
        else:
            proj_name = segs[0]
            slug = segs[0]
    else:
        proj_name = raw
        if "_" in raw:
            owner, _, repo = raw.partition("_")
            slug = f"{owner}/{repo}" if repo else raw
        else:
            slug = raw

    project = find_project_by_name(output_dir, proj_name)
    if project:
        target = "/project/{}/{}".format(
            up.quote(project["dir"], safe=""),
            up.quote(project["name"], safe=""),
        )
    else:
        target = "/?auto_generate={}".format(up.quote(slug, safe="/"))
    handler._send_redirect(target)

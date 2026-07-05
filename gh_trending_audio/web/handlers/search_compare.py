"""全文搜索与项目对比 API 处理器。"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

from ._common import send_json, send_xml

__all__ = [
    "serve_search",
    "serve_search_suggestions",
    "serve_search_reindex",
    "serve_compare_projects",
]

# 模块级索引缓存
_search_index = None


def _get_or_build_index(output_dir: Path) -> Any:
    """获取或构建搜索索引（带缓存）。"""
    global _search_index
    if _search_index is None or _search_index.doc_count == 0:
        from ...search_engine import build_index
        _search_index = build_index(output_dir)
    return _search_index


def serve_search(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """全文搜索 API。"""
    query = params.get("q", [""])[0]
    if not query.strip():
        send_json(handler, 400, {"error": "Missing query parameter 'q'"})
        return

    max_results = int(params.get("limit", ["20"])[0])
    max_results = min(max_results, 100)

    index = _get_or_build_index(output_dir)
    from ...search_engine import search as do_search
    results = do_search(index, query, max_results=max_results)

    send_json(handler, 200, {
        "query": query,
        "total": len(results),
        "results": [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "language": r.language,
                "score": r.score,
                "snippet": r.snippet,
                "path": r.path,
            }
            for r in results
        ],
    })


def serve_search_suggestions(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """搜索建议 API（自动补全）。"""
    prefix = params.get("q", [""])[0]
    if not prefix.strip():
        send_json(handler, 200, {"suggestions": []})
        return

    index = _get_or_build_index(output_dir)
    from ...search_engine import get_search_suggestions
    suggestions = get_search_suggestions(index, prefix)

    send_json(handler, 200, {"suggestions": suggestions})


def serve_search_reindex(handler: BaseHTTPRequestHandler, output_dir: Path) -> None:
    """重建搜索索引。"""
    global _search_index
    from ...search_engine import build_index, save_index
    _search_index = build_index(output_dir)
    save_index(_search_index)
    send_json(handler, 200, {
        "status": "ok",
        "doc_count": _search_index.doc_count,
        "term_count": len(_search_index.inverted),
    })


def serve_compare_projects(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """项目对比 API。"""
    from ...comparison_engine import compare_projects, generate_comparison_table, generate_radar_data

    projects_param = params.get("projects", [""])[0]
    if not projects_param:
        send_json(handler, 400, {"error": "Missing 'projects' parameter (comma-separated names)"})
        return

    project_names = [n.strip() for n in projects_param.split(",") if n.strip()]
    if len(project_names) < 2:
        send_json(handler, 400, {"error": "At least 2 projects required for comparison"})
        return

    fmt = params.get("format", ["json"])[0].lower()
    comparison = compare_projects(output_dir, project_names)

    if fmt == "html":
        html_table = generate_comparison_table(comparison)
        send_xml(handler, html_table, content_type="text/html; charset=utf-8")
    elif fmt == "radar":
        radar_data = generate_radar_data(comparison)
        send_json(handler, 200, radar_data)
    else:
        comparison["html_table"] = generate_comparison_table(comparison)
        comparison["radar_data"] = generate_radar_data(comparison)
        send_json(handler, 200, comparison)

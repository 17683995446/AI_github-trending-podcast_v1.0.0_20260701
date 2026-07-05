"""GitHub 仓库浏览 API 处理器。

包含 README 获取、文件树浏览、文件内容、社区洞察、代码搜索等端点。
"""

from __future__ import annotations

import time
from http.server import BaseHTTPRequestHandler

from ._common import (
    send_json, logger,
    _FILETREE_CACHE, _FILE_CONTENT_CACHE,
    CodeSearchError,
)
from ..code_search import (
    _CodeSearchUnavailable,
    github_code_search,
    local_code_search,
    normalize_repo_slug,
)

__all__ = [
    "serve_api_readme",
    "serve_api_filetree",
    "serve_api_file",
    "serve_api_community",
    "handle_search_code",
]


def serve_api_readme(handler: BaseHTTPRequestHandler, params: dict) -> None:
    """GET /api/readme?repo=owner/repo — 返回仓库 README 原文。"""
    repo = (params.get("repo", [""])[0] or "").strip()
    if not repo or "/" not in repo:
        send_json(handler, 400, {"error": "缺少 repo 参数（格式：owner/repo）"})
        return

    cache_key = f"readme:{repo}"
    if cache_key in _FILE_CONTENT_CACHE:
        send_json(handler, 200, _FILE_CONTENT_CACHE[cache_key])
        return

    try:
        from gh_trending_audio.github_client import get_github_client
        client = get_github_client()
        readme_text, readme_path, html_url = client.get_readme(repo)

        if len(readme_text) > 204800:
            readme_text = readme_text[:204800] + "\n\n... (README 已截断，完整内容请访问 GitHub)"

        result = {
            "repo": repo,
            "path": readme_path,
            "content": readme_text,
            "html_url": html_url,
            "size": len(readme_text),
        }
        _FILE_CONTENT_CACHE[cache_key] = result
        send_json(handler, 200, result)
    except Exception as e:
        send_json(handler, 502, {"error": f"获取 README 失败: {str(e)[:300]}"})


def serve_api_filetree(handler: BaseHTTPRequestHandler, params: dict) -> None:
    """GET /api/filetree?repo=owner/repo — 返回仓库递归文件树。"""
    repo = (params.get("repo", [""])[0] or "").strip()
    if not repo or "/" not in repo:
        send_json(handler, 400, {"error": "缺少 repo 参数（格式：owner/repo）"})
        return

    cache_key = repo
    if cache_key in _FILETREE_CACHE:
        send_json(handler, 200, _FILETREE_CACHE[cache_key])
        return

    try:
        from gh_trending_audio.github_client import get_github_client
        client = get_github_client()
        files, truncated = client.get_file_tree(repo)

        result = {
            "repo": repo,
            "default_branch": "",
            "tree": [
                {"path": f.path, "type": f.type, "size": f.size}
                for f in files
            ],
            "truncated": truncated,
        }
        _FILETREE_CACHE[cache_key] = result
        send_json(handler, 200, result)
    except Exception as e:
        err_msg = str(e)
        logger.warning("文件树获取失败", exc_info=True)
        if "rate limit" in err_msg.lower() or "403" in err_msg:
            from gh_trending_audio.config import GITHUB_TOKEN
            hint = (
                "GitHub API 速率限制（未认证 60 次/小时已用完）。"
                "请在 .env 文件中设置 GITHUB_TOKEN（认证后 5000 次/小时）。"
                if not GITHUB_TOKEN
                else "GitHub API 速率限制（Token 配额已用完），请稍后重试。"
            )
            send_json(handler, 429, {"error": hint, "rate_limited": True})
        else:
            send_json(handler, 502, {"error": f"获取文件树失败: {err_msg[:200]}"})


def serve_api_file(handler: BaseHTTPRequestHandler, params: dict) -> None:
    """GET /api/file?repo=owner/repo&path=src/main.py — 返回文件内容。"""
    repo = (params.get("repo", [""])[0] or "").strip()
    file_path = (params.get("path", [""])[0] or "").strip()
    if not repo or "/" not in repo:
        send_json(handler, 400, {"error": "缺少 repo 参数（格式：owner/repo）"})
        return
    if not file_path:
        send_json(handler, 400, {"error": "缺少 path 参数"})
        return

    cache_key = f"{repo}:{file_path}"
    if cache_key in _FILE_CONTENT_CACHE:
        send_json(handler, 200, _FILE_CONTENT_CACHE[cache_key])
        return

    try:
        from gh_trending_audio.github_client import get_github_client
        client = get_github_client()
        content = client.get_file_content(repo, file_path, max_size=102400)

        result = {
            "path": file_path,
            "size": len(content),
            "content": content,
            "encoding": "utf-8",
        }
        _FILE_CONTENT_CACHE[cache_key] = result
        send_json(handler, 200, result)
    except Exception as e:
        logger.warning("文件内容获取失败", exc_info=True)
        err_msg = str(e)[:300]
        if "413" in err_msg or "too large" in err_msg.lower():
            send_json(handler, 413, {"error": "文件过大，限制 100KB 以内"})
        else:
            send_json(handler, 502, {"error": f"获取文件内容失败: {err_msg}"})


def serve_api_community(handler: BaseHTTPRequestHandler, params: dict) -> None:
    """GET /api/community?repo=owner/repo — 社区洞察。"""
    repo = (params.get("repo", [""])[0] or "").strip()
    if not repo or "/" not in repo:
        send_json(handler, 400, {"error": "缺少 repo 参数（格式：owner/repo）"})
        return

    try:
        from gh_trending_audio.github_client import get_github_client
        client = get_github_client()
        data = client.get_community_data(repo, max_items=5)

        results = {
            "repo_info": data.repo_info,
            "hot_issues": data.open_issues,
            "active_prs": data.open_pulls,
            "contributors": data.contributors,
            "releases": data.releases,
        }
        send_json(handler, 200, results)
    except Exception as e:
        logger.warning("社区数据获取失败", exc_info=True)
        send_json(handler, 502, {"error": f"获取社区数据失败: {str(e)[:300]}"})


def handle_search_code(handler: BaseHTTPRequestHandler, params: dict) -> None:
    """POST /api/search-code — 自然语言/代码模式搜索项目源码。"""
    start = time.time()
    repo_input = (params.get("repo") or params.get("project") or "").strip()
    query = params.get("query") or ""
    language = (params.get("language") or "").strip()

    if not query.strip():
        send_json(handler, 400, {"error": "搜索词不能为空"})
        return

    repo = normalize_repo_slug(repo_input)
    if not repo or "/" not in repo:
        send_json(handler, 400, {"error": "无法解析仓库名称，请提供 owner/repo 或 owner_repo 形式的项目名"})
        return

    from gh_trending_audio.config import GITHUB_TOKEN as DEFAULT_TOKEN
    token = (params.get("token") or DEFAULT_TOKEN or "").strip()

    source = "github"
    fallback_reason = ""
    results: list[dict] = []
    total = 0
    try:
        results, total = github_code_search(repo, query, language, token)
    except _CodeSearchUnavailable as e:
        fallback_reason = str(e)
        source = "local"
        results, total = local_code_search(repo, query, language)
    except (CodeSearchError, OSError) as e:
        send_json(handler, 500, {"error": f"代码搜索失败: {e}"})
        return

    elapsed_ms = int((time.time() - start) * 1000)

    message = ""
    if source == "local" and total == 0:
        if not fallback_reason:
            fallback_reason = "GitHub Code Search API 不可用"
        message = (
            "本地回退搜索未返回结果。可能原因：未安装 repomix、仓库不可访问，"
            "或关键词未匹配。（回退原因：" + fallback_reason + "）"
        )

    send_json(handler, 200, {
        "results": results,
        "total": total,
        "source": source,
        "query": query,
        "elapsed_ms": elapsed_ms,
        "fallback_reason": fallback_reason,
        "message": message,
    })

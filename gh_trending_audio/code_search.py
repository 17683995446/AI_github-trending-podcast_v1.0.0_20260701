"""代码搜索工具（阶段5: 从 utils.py 拆分）。

提供 GitHub Code Search API 调用、本地 Repomix 正则搜索、
以及相关的辅助函数（语言扩展名匹配、代码行分类等）。
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests

from .constants import GITHUB_API_URL, GITHUB_CODE_SEARCH_TIMEOUT, CODE_SEARCH_TIMEOUT
from .exceptions import CodeSearchError
from .logging_config import get_logger

logger = get_logger(__name__)


class CodeSearchUnavailable(CodeSearchError):
    """GitHub Code Search API 不可用（无 Token / 超出配额 / 网络错误）时抛出，
    用于触发到 Repomix + 本地正则的回退搜索。"""
    pass


# 向后兼容别名（原 utils._CodeSearchUnavailable）
_CodeSearchUnavailable = CodeSearchUnavailable


def normalize_repo_slug(repo: str) -> str | None:
    """将 owner_repo 或 owner/repo 规范化为 owner/repo。

    项目名约定为 owner_repo（如 deepseek-ai_DeepSpec → deepseek-ai/DeepSpec），
    故以第一个下划线作为 owner/repo 分隔符。
    """
    if not repo:
        return None
    repo = repo.strip()
    if "/" in repo:
        return repo
    idx = repo.find("_")
    if idx == -1:
        return repo
    return repo[:idx] + "/" + repo[idx + 1:]


def github_api_get(url: str) -> tuple[int, Any]:
    """发起 GitHub API GET 请求，返回 (status_code, data)。

    Phase 3: 统一委托给 github_client，消除 urllib 手写实现。
    保留函数签名以兼容现有调用方。
    """
    try:
        from gh_trending_audio.github_client import get_github_client

        client = get_github_client()
        # 从完整 URL 提取 owner/repo 和 path
        # URL 格式: https://api.github.com/repos/owner/repo/contents/path
        if "/repos/" in url:
            parts = url.split("/repos/", 1)[1].split("/", 2)
            if len(parts) >= 2:
                repo_slug = f"{parts[0]}/{parts[1]}"
                if len(parts) >= 3 and parts[2].startswith("contents/"):
                    file_path = parts[2][len("contents/"):]
                    content = client.get_file_content(repo_slug, file_path, max_size=51200)
                    return 200, {"content": content, "encoding": "utf-8"}
                elif len(parts) >= 3 and parts[2].startswith("releases"):
                    return 200, []
                elif len(parts) >= 3 and "search/issues" in parts[2]:
                    return 200, {"items": []}
        return 200, {}
    except (OSError, requests.RequestException) as e:
        return 0, str(e)


def github_code_search(repo: str, query: str, language: str, token: str) -> tuple[list[dict], int]:
    """调用 GitHub Code Search API。

    无 Token 或被限流/鉴权失败时抛出 _CodeSearchUnavailable，由上层回退。
    使用 text-match 媒体类型以拿到匹配片段（fragment）。
    """
    import urllib.error
    import urllib.request

    if not token:
        raise _CodeSearchUnavailable("未配置 GitHub Token，跳过 Code Search API")

    # 组装查询：query repo:owner/repo [language:xxx]
    q = f"{query} repo:{repo}"
    if language and not re.search(r"\s", language):
        q += f" language:{language.lower()}"

    url = f"{GITHUB_API_URL}/search/code?q=" + urllib.parse.quote(q, safe="")
    headers = {
        "Accept": "application/vnd.github.text-match+json",
        "User-Agent": "gh-trending-audio-dashboard",
        "Authorization": f"Bearer {token}",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=GITHUB_CODE_SEARCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        # 401/403/422/429 → 鉴权失败或配额超限，回退本地搜索
        if e.code in (401, 403, 422, 429):
            raise _CodeSearchUnavailable(
                f"GitHub Code Search API 不可用 (HTTP {e.code})"
            )
        raise
    except urllib.error.URLError as e:
        raise _CodeSearchUnavailable(f"网络请求失败: {e}")
    except (OSError, requests.RequestException) as e:
        raise _CodeSearchUnavailable(f"请求异常: {e}")

    items = data.get("items") or []
    results = []
    for item in items[:20]:
        snippet = ""
        tms = item.get("text_matches") or []
        if tms:
            snippet = (tms[0].get("fragment") or "").strip()
        results.append({
            "path": item.get("path", ""),
            "name": item.get("name", ""),
            "score": round(float(item.get("score") or 0), 4),
            "snippet": snippet,
            "context": snippet,
            "line": None,
            "type": "",
            "url": item.get("html_url", ""),
        })
    return results, int(data.get("total_count") or len(results))


def ext_matches_language(path: str, language: str) -> bool:
    """按文件扩展名判断是否属于指定编程语言（用于本地搜索过滤）。"""
    from os.path import splitext

    lang = language.lower()
    ext_map = {
        "python": {".py"},
        "javascript": {".js", ".jsx", ".mjs", ".cjs"},
        "typescript": {".ts", ".tsx"},
        "go": {".go"},
        "rust": {".rs"},
        "java": {".java"},
        "kotlin": {".kt", ".kts"},
        "ruby": {".rb"},
        "php": {".php"},
        "c": {".c", ".h"},
        "c++": {".cpp", ".hpp", ".cc", ".cxx"},
        "c#": {".cs"},
        "swift": {".swift"},
        "scala": {".scala"},
        "shell": {".sh", ".bash"},
    }
    exts = ext_map.get(lang)
    if not exts:
        return True  # 未知语言不过滤，全部参与搜索
    return splitext(path)[1].lower() in exts


def classify_line(line: str) -> str:
    """识别命中行的代码结构类型：function / class / import / match。"""
    s = line.lstrip()
    if re.match(r"(def|function|func|fn|sub|fun)\s+\w", s):
        return "function"
    if re.match(r"(class|interface|struct|trait|enum|object|record)\s+\w", s):
        return "class"
    if re.match(r"(import|from|require|use|include|#include)\s", s):
        return "import"
    return "match"


def regex_search_in_xml(xml_text: str, query: str, language: str) -> tuple[list[dict], int]:
    """在 Repomix XML 输出中按正则搜索代码，返回匹配结果（含上下文片段）。"""
    import os as _os
    import re as _re

    # 解析 <file path="...">content</file>（兼容内嵌 <content> 包装）
    files = _re.findall(
        r'<file\s+path="([^"]+)"[^>]*>(.*?)</file>', xml_text, _re.DOTALL
    )

    # 编译查询：优先当作正则，编译失败则按字面量转义
    try:
        rx = _re.compile(query)
    except _re.error:
        rx = _re.compile(_re.escape(query))

    results = []
    for path, raw in files:
        # 去掉内嵌 <content> 包装，并剥离 XML 标签后引入的首尾换行，
        # 使命中行号尽量贴近源文件真实行号
        content = raw.replace("<content>", "").replace("</content>", "").strip("\n")
        # 按语言扩展名过滤（若指定且可识别）
        if language and not ext_matches_language(path, language):
            continue

        lines = content.split("\n")
        hits = [i for i, ln in enumerate(lines) if rx.search(ln)]
        if not hits:
            continue

        mtype = classify_line(lines[hits[0]])
        i = hits[0]
        # 折叠片段：命中行 ±1 行
        s = max(0, i - 1)
        e = min(len(lines), i + 2)
        snippet = "\n".join(lines[s:e])
        # 展开上下文：命中行 ±5 行
        cs = max(0, i - 5)
        ce = min(len(lines), i + 6)
        context = "\n".join(lines[cs:ce])

        results.append({
            "path": path,
            "name": _os.path.basename(path),
            "score": round(0.8 + 0.2 * min(len(hits), 5), 2),
            "snippet": snippet,
            "context": context,
            "line": i + 1,
            "type": mtype,
            "url": "",
            "matches": len(hits),
        })
        if len(results) >= 30:
            break

    # 按命中数倒序，命中多的文件排前面
    results.sort(key=lambda r: r.get("matches", 0), reverse=True)
    return results, len(results)


def local_code_search(repo: str, query: str, language: str) -> tuple[list[dict], int]:
    """回退方案：用 Repomix 拉取仓库代码，本地用正则搜索代码位置。

    返回匹配的文件与代码片段（含命中行号、上下文、匹配类型）。
    Repomix 未安装或仓库不可访问时返回空结果。
    """
    import shutil as _shutil
    import subprocess

    if not _shutil.which("repomix"):
        return [], 0

    # repomix --remote 需要 GitHub URL；repo 已是 owner/repo 形式
    owner_repo = repo
    cmd = [
        "repomix",
        "--remote", f"https://github.com/{owner_repo}",
        "--style", "xml",
        "--stdout",
        "--include",
        "*.py,*.js,*.ts,*.jsx,*.tsx,*.mjs,*.cjs,*.go,*.rs,*.java,*.kt,*.rb,"
        "*.php,*.c,*.h,*.cpp,*.hpp,*.cc,*.cxx,*.cs,*.swift,*.scala,*.sh,*.bash,"
        "*.yml,*.yaml,*.toml,*.json,*.xml,*.html,*.css,*.scss,*.sql,*.vue",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=CODE_SEARCH_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return [], 0
    except (OSError, subprocess.SubprocessError):
        logger.debug("repomix 执行失败", exc_info=True)
        return [], 0
    if result.returncode != 0:
        return [], 0

    return regex_search_in_xml(result.stdout or "", query, language)

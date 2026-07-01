"""Utility functions for the web dashboard.

Extracted from the original ``DashboardHandler`` as module-level, self-free
helpers (data scanning, markdown parsing, GitHub API access and code search).
Functions that previously relied on the module-level ``OUTPUT_DIR`` now receive
it explicitly as an argument, keeping them pure and testable.
"""

from __future__ import annotations

import json
import re
import urllib.parse


class _CodeSearchUnavailable(Exception):
    """GitHub Code Search API 不可用（无 Token / 超出配额 / 网络错误）时抛出，
    用于触发到 Repomix + 本地正则的回退搜索。"""
    pass


# ── Markdown / project metadata ─────────────────────────────────────

def parse_md_metadata(md: str) -> dict:
    """从 Markdown 内容中提取项目元数据"""
    import re as _re
    meta = {"description": "", "stars": 0, "language": "", "license": "", "topics": ""}

    # 提取描述（Markdown 表格中的描述行，或第一段文字）
    desc_match = _re.search(r"[|｜]\s*描述\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if desc_match:
        meta["description"] = desc_match.group(1)[:120]
    else:
        # 尝试提取第一段非标题文字
        lines = md.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("|") and not line.startswith("---"):
                meta["description"] = line[:120]
                break

    # 提取星标数
    stars_match = _re.search(r"[|｜]\s*星标[数]?\s*[|｜]\s*([\d,]+)", md)
    if stars_match:
        meta["stars"] = int(stars_match.group(1).replace(",", ""))

    # 提取编程语言
    lang_match = _re.search(r"[|｜]\s*编程语言\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if lang_match:
        meta["language"] = lang_match.group(1).strip()

    # 提取开源协议
    lic_match = _re.search(r"[|｜]\s*开源协议\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if lic_match:
        meta["license"] = lic_match.group(1).strip()

    # 提取标签
    topics_match = _re.search(r"[|｜]\s*标签\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if topics_match:
        meta["topics"] = topics_match.group(1).strip()[:80]

    return meta


def get_audio_duration(audio_path) -> float | None:
    """获取音频时长（秒），用 ffprobe 快速读取"""
    import subprocess
    import shutil as _shutil
    if not _shutil.which("ffprobe"):
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def scan_projects(output_dir) -> list[dict]:
    """扫描所有输出目录，返回项目列表（含元数据）"""
    projects = []
    for d in sorted(output_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith("output"):
            continue
        for f in sorted(d.iterdir()):
            if f.suffix == ".md" and not f.name.endswith("_script.txt"):
                name = f.stem
                script_path = d / f"{name}_script.txt"
                audio_path = d / f"{name}.mp3"
                md_size = f.stat().st_size
                script_size = script_path.stat().st_size if script_path.exists() else 0
                audio_size = audio_path.stat().st_size if audio_path.exists() else 0

                # 从 Markdown 提取元数据
                meta = {"description": "", "stars": 0, "language": "", "license": "", "topics": ""}
                try:
                    md_text = f.read_text(encoding="utf-8", errors="replace")[:2000]
                    meta = parse_md_metadata(md_text)
                except Exception:
                    pass

                # 获取创建时间（用文件修改时间）
                created_at = f.stat().st_mtime

                projects.append({
                    "name": name,
                    "dir": d.name,
                    "has_md": True,
                    "has_script": script_path.exists(),
                    "has_audio": audio_path.exists() and audio_size > 0,
                    "md_size": md_size,
                    "script_size": script_size,
                    "audio_size": audio_size,
                    "total_size": md_size + script_size + audio_size,
                    "md_path": f"{d.name}/{f.name}",
                    "script_path": f"{d.name}/{script_path.name}" if script_path.exists() else None,
                    "audio_path": f"{d.name}/{audio_path.name}" if audio_path.exists() and audio_size > 0 else None,
                    "description": meta["description"],
                    "stars": meta["stars"],
                    "language": meta["language"],
                    "license": meta["license"],
                    "topics": meta["topics"],
                    "created_at": created_at,
                    "audio_duration": get_audio_duration(audio_path) if audio_path.exists() else None,
                })
    # 按创建时间倒序排列（最新在前）
    projects.sort(key=lambda p: p.get("created_at", 0), reverse=True)
    return projects


def get_project_detail(output_dir, dir_name: str, proj_name: str) -> dict | None:
    """获取项目详情（含 Markdown 内容）"""
    projects = scan_projects(output_dir)
    for p in projects:
        if p["name"] == proj_name and (not dir_name or p["dir"] == dir_name):
            md_path = output_dir / p["md_path"]
            script_path = output_dir / p["script_path"] if p["script_path"] else None

            md_content = ""
            if md_path.exists():
                md_content = md_path.read_text(encoding="utf-8")

            script_content = ""
            if script_path and script_path.exists():
                script_content = script_path.read_text(encoding="utf-8")

            return {**p, "md_content": md_content, "script_content": script_content}
    return None


def markdown_to_html(md: str) -> str:
    """Markdown -> HTML 转换，并支持 Mermaid 图表渲染。

    将 ```mermaid ... ``` 代码块转换为 <div class="mermaid"> 节点，
    交由前端 Mermaid.js 渲染为架构图。其余 Markdown 正常转换。
    """
    # 先把 ```mermaid ... ``` 代码块替换为纯文本占位符，
    # 避免 markdown 库将其当作普通代码块转义/高亮，保证后续还原为可渲染节点。
    mermaid_blocks: list[str] = []

    def _stash(m):
        mermaid_blocks.append(m.group(1).strip())
        return f"@@MERMAID:{len(mermaid_blocks) - 1}@@"

    md_stashed = re.sub(r"```mermaid\s*\n(.*?)```", _stash, md, flags=re.DOTALL)

    try:
        import markdown as md_lib
        html = md_lib.markdown(md_stashed, extensions=["fenced_code", "tables", "codehilite"])
    except ImportError:
        # 退化方案：手工转换标题，其余包裹在 <pre> 中
        html = md_stashed.replace("<", "&lt;").replace(">", "&gt;")
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.M)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.M)
        html = f"<pre>{html}</pre>"

    # 将占位符还原为 Mermaid.js 可渲染的 <div class="mermaid"> 节点
    for i, code in enumerate(mermaid_blocks):
        placeholder = f"@@MERMAID:{i}@@"
        mermaid_div = f'<div class="mermaid">{code}</div>'
        # markdown 库可能把占位符包裹在 <p> 中，也可能作为独立文本节点
        html = html.replace(f"<p>{placeholder}</p>", mermaid_div)
        html = html.replace(placeholder, mermaid_div)

    return html


def build_repo_from_md(name: str, md_text: str):
    """从项目名和 Markdown 文档构建轻量 RepoInfo（用于对比分析）。

    Web 仪表盘没有原始 GitHub API 数据，只能从已生成的 Markdown
    元数据中解析出星标、语言、协议等信息，构造一个 RepoInfo 供
    LLMEnhancer.generate_comparison 使用。
    """
    from gh_trending_audio.github_fetcher import RepoInfo

    meta = parse_md_metadata(md_text)
    # 项目文件名形如 owner_repo，拆分出 owner 和 repo 名
    if "_" in name:
        owner, repo_name = name.split("_", 1)
    else:
        owner, repo_name = name, name

    # 标签字符串还原为列表
    topics_str = meta.get("topics", "")
    topics = [t.strip() for t in topics_str.replace("，", ",").split(",") if t.strip()]

    return RepoInfo(
        full_name=f"{owner}/{repo_name}",
        name=repo_name,
        owner=owner,
        description=meta.get("description", ""),
        url="",
        homepage="",
        language=meta.get("language", ""),
        stars=meta.get("stars", 0) or 0,
        forks=0,
        open_issues=0,
        watchers=0,
        topics=topics,
        license_name=meta.get("license", ""),
    )


# ── 代码搜索辅助 ───────────────────────────────────────────────────

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


def github_api_get(url: str):
    """发起 GitHub API GET 请求，返回 (status_code, data)。

    data 为解析后的 JSON 字典；出错时返回字符串形式的错误正文。
    使用 config.py 中的 GITHUB_TOKEN（若有）提高速率配额。
    """
    import urllib.request
    import urllib.error

    from gh_trending_audio.config import GITHUB_TOKEN

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "gh-trending-audio-dashboard",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, str(e)


def github_code_search(repo: str, query: str, language: str, token: str):
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

    url = "https://api.github.com/search/code?q=" + urllib.parse.quote(q, safe="")
    headers = {
        "Accept": "application/vnd.github.text-match+json",
        "User-Agent": "gh-trending-audio-dashboard",
        "Authorization": f"Bearer {token}",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
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
    except Exception as e:
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


def regex_search_in_xml(xml_text: str, query: str, language: str):
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


def local_code_search(repo: str, query: str, language: str):
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
            cmd, capture_output=True, text=True, timeout=90
        )
    except subprocess.TimeoutExpired:
        return [], 0
    except Exception:
        return [], 0
    if result.returncode != 0:
        return [], 0

    return regex_search_in_xml(result.stdout or "", query, language)

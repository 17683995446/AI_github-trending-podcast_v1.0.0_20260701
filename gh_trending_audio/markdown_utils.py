"""Markdown 解析与转换工具（核心层）。

负责 Markdown 元数据提取、Markdown→HTML 转换、以及从 Markdown
构建轻量 RepoInfo 对象。

此模块从 ``web/markdown_utils.py`` 上移到核心包，修复架构层级倒置。
``web/markdown_utils.py`` 保留为兼容垫片，re-export 本模块的所有公共函数。
"""

from __future__ import annotations

import html as html_mod
import re

from .logging_config import get_logger
from .models import RepoInfo

logger = get_logger(__name__)


def parse_md_metadata(md: str) -> dict:
    """从 Markdown 内容中提取项目元数据"""
    meta = {"description": "", "stars": 0, "forks": 0, "language": "", "license": "", "topics": ""}

    # 提取描述（Markdown 表格中的描述行，或第一段文字）
    desc_match = re.search(r"[|｜]\s*描述\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if desc_match:
        meta["description"] = desc_match.group(1)[:120]
    else:
        lines = md.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("|") and not line.startswith("---"):
                meta["description"] = line[:120]
                break

    # 提取星标数
    stars_match = re.search(r"[|｜]\s*(?:星标|Stars?)[^\n|]*[|｜]\s*[^|\n]*?([\d,]+)", md)
    if stars_match:
        meta["stars"] = int(stars_match.group(1).replace(",", ""))

    # 提取派生(Fork)数
    forks_match = re.search(r"[|｜]\s*(?:Forks?|派生)[^\n|]*[|｜]\s*[^|\n]*?([\d,]+)", md)
    if forks_match:
        meta["forks"] = int(forks_match.group(1).replace(",", ""))

    # 提取编程语言
    lang_match = re.search(r"[|｜]\s*编程语言\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if lang_match:
        meta["language"] = lang_match.group(1).strip()

    # 提取开源协议
    lic_match = re.search(r"[|｜]\s*开源协议\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if lic_match:
        meta["license"] = lic_match.group(1).strip()

    # 提取标签
    topics_match = re.search(r"[|｜]\s*标签\s*[|｜]\s*(.+?)\s*[|｜]", md)
    if topics_match:
        meta["topics"] = topics_match.group(1).strip()[:80]

    return meta


def markdown_to_html(md: str) -> str:
    """Markdown -> HTML 转换，并支持 Mermaid 图表渲染。"""
    mermaid_blocks: list[str] = []

    def _stash(m: re.Match[str]) -> str:
        """将 Mermaid 代码块暂存到列表，返回可替换的占位符。

        Args:
            m: 正则匹配对象，其 group(1) 为 Mermaid 代码块内容。

        Returns:
            形如 ``@@MERMAID:{index}@@`` 的占位符字符串。
        """
        mermaid_blocks.append(m.group(1).strip())
        return f"@@MERMAID:{len(mermaid_blocks) - 1}@@"

    md_stashed = re.sub(r"```mermaid\s*\n(.*?)```", _stash, md, flags=re.DOTALL)

    try:
        import markdown as md_lib
        extensions = ["fenced_code", "tables", "codehilite"]
        extension_configs = {}
        try:
            import pymdownx  # noqa: F401
            extensions.extend([
                "pymdownx.tilde",
                "pymdownx.tasklist",
                "pymdownx.emoji",
                "pymdownx.superfences",
                "pymdownx.magiclink",
            ])
        except ImportError:
            pass
        html = md_lib.markdown(md_stashed, extensions=extensions, extension_configs=extension_configs)
    except ImportError:
        html = html_mod.escape(md_stashed)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.M)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.M)
        html = f"<pre>{html}</pre>"

    for i, code in enumerate(mermaid_blocks):
        placeholder = f"@@MERMAID:{i}@@"
        mermaid_div = f'<div class="mermaid">{code}</div>'
        html = html.replace(f"<p>{placeholder}</p>", mermaid_div)
        html = html.replace(placeholder, mermaid_div)

    return html


def build_repo_from_md(name: str, md_text: str) -> RepoInfo:
    """从项目名和 Markdown 文档构建轻量 RepoInfo。

    Args:
        name: 项目名称，形如 ``owner_repo`` 或 ``repo``。
              含下划线时按第一个下划线拆分为 owner 与 repo_name。
        md_text: 项目的 Markdown 文档内容，用于提取元数据。

    Returns:
        填充了元数据字段的 RepoInfo 对象。
    """
    from gh_trending_audio.models import RepoInfo

    meta = parse_md_metadata(md_text)
    if "_" in name:
        owner, repo_name = name.split("_", 1)
    else:
        owner, repo_name = name, name

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
        forks=meta.get("forks", 0) or 0,
        open_issues=0,
        watchers=0,
        topics=topics,
        license_name=meta.get("license", ""),
    )

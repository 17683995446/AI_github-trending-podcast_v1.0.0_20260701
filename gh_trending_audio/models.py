"""共享数据模型（Phase 2: 规范化）。

将项目核心数据结构集中定义，消除跨模块重复定义和数据模型散落问题。
所有模块通过 ``from gh_trending_audio.models import ...`` 统一导入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

# ── 可选：Pydantic 结构化输出模型 ──────────────────────────────────────
try:
    from pydantic import BaseModel, Field

    class PodcastScript(BaseModel):
        """LLM 结构化输出：播客文档 + 对话脚本。"""

        markdown: str = Field(..., description="项目深度解读的 Markdown 文档")
        audio_script: str = Field(..., description="双人对话脚本，格式 A: / B: 交替")

    _HAS_PYDANTIC = True
except ImportError:
    PodcastScript = None  # type: ignore[assignment, misc]
    _HAS_PYDANTIC = False

__all__ = [
    # 结构化输出模型（无 pydantic 时为 None）
    "PodcastScript",
    # 仓库信息
    "RepoInfo",
    "AudioDocument",
    "FileInfo",
    "RepoSummary",
    "CommunityData",
    # Web 层类型
    "ProjectMeta",
    "PipelineResult",
]


# ═══════════════════════════════════════════════════════════════════
# 仓库信息
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RepoInfo:
    """一个 GitHub 仓库的结构化信息。

    从 GitHub API 获取后填充基本字段，enrich 系列方法填充增强字段。
    """

    full_name: str           # owner/repo
    name: str
    owner: str
    description: str
    url: str                 # html_url
    homepage: str            # 项目主页
    language: str
    stars: int
    forks: int
    open_issues: int
    watchers: int
    topics: list[str] = field(default_factory=list)
    created_at: str = ""
    pushed_at: str = ""
    license_name: str = ""
    readme_text: str = ""    # 抓取后填充
    # ── 增强数据（enrich_with_details 填充）──
    file_tree: str = ""
    key_files: str = ""
    recent_releases: str = ""
    recent_issues: str = ""
    languages_breakdown: str = ""
    contributors_count: int = 0
    commits_count: int = 0

    @property
    def short_name(self) -> str:
        """仓库名简称（不含 owner 前缀）。"""
        return self.name

    def to_dict(self) -> dict:
        """序列化为字典（用于 JSON 输出）。"""
        return {
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "topics": self.topics,
            "license": self.license_name,
            "readme_preview": self.readme_text[:500] if self.readme_text else "",
        }


# ═══════════════════════════════════════════════════════════════════
# 文档与音频
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AudioDocument:
    """一个项目的完整音频文档。

    包含 Markdown 文档和 TTS 朗读脚本两种格式。
    """

    repo: RepoInfo
    title: str               # 文档标题
    markdown: str            # Markdown 全文
    audio_script: str        # TTS 朗读脚本（纯文本，无 Markdown 符号）

    def save(self, md_path: str | Path, script_path: str | Path) -> None:
        """保存 Markdown 文档和音频脚本到文件。

        Args:
            md_path: Markdown 文件保存路径
            script_path: 音频脚本文件保存路径
        """
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.markdown)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(self.audio_script)


# ═══════════════════════════════════════════════════════════════════
# GitHub 客户端数据模型
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    """GitHub 仓库中的文件/目录信息。

    Attributes:
        path: 文件路径
        type: "blob"（文件）或 "tree"（目录）
        size: 文件大小（字节）
    """

    path: str
    type: Literal["blob", "tree"]
    size: int = 0


@dataclass
class RepoSummary:
    """仓库摘要信息（用于项目列表展示）。

    所有字段除 full_name 外均有默认值，方便部分构造。
    """

    full_name: str
    name: str = ""
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    license_name: str = ""
    topics: list[str] = field(default_factory=list)
    default_branch: str = "main"
    html_url: str = ""


@dataclass
class CommunityData:
    """仓库社区数据（issues、PR、贡献者、releases）。

    所有字段均有默认值，支持空构造。
    """

    repo_info: dict = field(default_factory=dict)
    open_issues: list[dict] = field(default_factory=list)
    open_pulls: list[dict] = field(default_factory=list)
    contributors: list[dict] = field(default_factory=list)
    releases: list[dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Web 层类型
# ═══════════════════════════════════════════════════════════════════

class ProjectMeta(TypedDict, total=False):
    """项目元数据（扫描 output_* 目录的结果）。"""

    name: str
    dir: str
    has_md: bool
    has_script: bool
    has_audio: bool
    total_size: int
    language: str
    description: str
    stars: int
    md_path: str
    script_path: str
    audio_path: str
    md_content: str
    script_content: str


class PipelineResult(TypedDict, total=False):
    """流水线执行结果。"""

    output_dir: str
    doc_count: int
    audio_count: int
    skipped: int
    timestamp: str
    type: str  # "comparison" 等
    name: str
    project_url: str

"""项目扫描器（核心层）。

负责扫描输出目录中的项目文件、获取项目详情、以及音频时长计算。

此模块从 ``web/project_scanner.py`` 上移到核心包，修复架构层级倒置
（5个核心业务模块不再反向依赖 web 子包）。
``web/project_scanner.py`` 保留为兼容垫片，re-export 本模块的所有公共函数。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .constants import FFPROBE_TIMEOUT, MD_META_PARSE_LIMIT
from .logging_config import get_logger
from .markdown_utils import parse_md_metadata

logger = get_logger(__name__)


def get_audio_duration(audio_path: str | Path) -> float | None:
    """获取音频时长（秒），优先用 mutagen（纯 Python），退化到 ffprobe。

    Args:
        audio_path: 音频文件路径。

    Returns:
        时长（秒），获取失败返回 ``None``。
    """
    # 优先使用 mutagen（纯 Python，无外部依赖）
    try:
        from mutagen import File as MutagenFile

        audio = MutagenFile(str(audio_path))
        if audio is not None and audio.info is not None:
            duration = getattr(audio.info, "length", None)
            if duration is not None:
                return float(duration)
    except ImportError:
        pass  # mutagen 未安装，退化到 ffprobe
    except (OSError, ValueError, Exception) as exc:  # noqa: BLE001
        logger.debug("音频时长获取失败（mutagen）: %s", exc, exc_info=True)

    # 退化到 ffprobe 命令行工具
    if not shutil.which("ffprobe"):
        return None
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=FFPROBE_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        logger.debug("ffprobe 失败", exc_info=True)
        pass
    return None


def scan_projects(output_dir: Path) -> list[dict[str, Any]]:
    """扫描所有输出目录，返回项目列表（含元数据）。

    Args:
        output_dir: 项目输出根目录。

    Returns:
        按创建时间降序排列的项目字典列表。
    """
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

                meta = {"description": "", "stars": 0, "language": "", "license": "", "topics": ""}
                try:
                    md_text = f.read_text(encoding="utf-8", errors="replace")[:MD_META_PARSE_LIMIT]
                    meta = parse_md_metadata(md_text)
                except (KeyError, ValueError, IndexError):
                    logger.debug("MD 元数据解析失败", exc_info=True)
                    pass

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
                    "forks": meta["forks"],
                    "language": meta["language"],
                    "license": meta["license"],
                    "topics": meta["topics"],
                    "created_at": created_at,
                    "audio_duration": get_audio_duration(audio_path) if audio_path.exists() else None,
                })
    projects.sort(key=lambda p: p.get("created_at", 0), reverse=True)
    return projects


def get_project_detail(output_dir: Path, dir_name: str, proj_name: str) -> dict[str, Any] | None:
    """获取项目详情（含 Markdown 内容）。

    Args:
        output_dir: 项目输出根目录。
        dir_name: 项目所在子目录名。
        proj_name: 项目名（owner_repo 格式）。

    Returns:
        项目详情字典，未找到返回 ``None``。
    """
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

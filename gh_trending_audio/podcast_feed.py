"""播客 RSS 订阅源生成器（阶段6: 开源工具集成）。

使用 ``feedgen`` 库生成标准的 RSS 2.0 播客订阅源（含 iTunes 扩展），
以及 OPML 格式导出，让用户可以在 Apple Podcasts、Pocket Casts、
Spotify 等播客应用中订阅本工具生成的音频内容。

核心功能：
    - ``generate_podcast_feed()``  → RSS 2.0 XML 字符串（含 iTunes 标签）
    - ``generate_opml()``          → OPML XML 字符串（批量订阅导入）

依赖：
    - feedgen（可选，缺失时退化到 xml.etree 手动构建）

设计原则：
    - 第一性原理：播客 = 音频 + RSS 订阅源，缺一不可
    - 零侵入：独立模块，不修改现有流水线
    - 优雅降级：feedgen 不可用时用标准库 xml.etree
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .project_scanner import get_audio_duration, scan_projects

logger = get_logger(__name__)

# ── 播客频道元数据 ──
_PODCAST_TITLE = "GitHub Trending Audio"
_PODCAST_SUBTITLE = "将 GitHub 热门项目转化为音频播客"
_PODCAST_AUTHOR = "GH Trending Audio"
_PODCAST_CATEGORY = "Technology"
_PODCAST_LANGUAGE = "zh-cn"


def _format_duration(seconds: float | None) -> str:
    """将秒数格式化为 HH:MM:SS 或 MM:SS。"""
    if not seconds or seconds <= 0:
        return "00:00"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _rfc822_date(timestamp: float) -> str:
    """将 Unix 时间戳转为 RFC 822 日期格式（RSS 标准）。"""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def generate_podcast_feed(
    output_dir: Path,
    base_url: str = "",
    max_episodes: int = 100,
) -> str:
    """生成 RSS 2.0 播客订阅源 XML。

    Args:
        output_dir: 输出根目录（包含 output_* 子目录）
        base_url: 服务器基础 URL（如 ``http://localhost:8000``），
                  用于构建音频文件绝对 URL
        max_episodes: 最大剧集数（防止超大输出导致 XML 过大）

    Returns:
        RSS 2.0 XML 字符串（含 iTunes podcast 扩展标签）
    """
    base_url = base_url.rstrip("/")
    projects = scan_projects(output_dir)
    # 仅保留有音频的项目
    audio_projects = [p for p in projects if p.get("has_audio")]
    audio_projects = audio_projects[:max_episodes]

    try:
        return _generate_with_feedgen(audio_projects, base_url)
    except ImportError:
        logger.info("feedgen 不可用，退化到 xml.etree 手动构建 RSS")
        return _generate_with_stdlib(audio_projects, base_url)


def _generate_with_feedgen(projects: list[dict], base_url: str) -> str:
    """使用 feedgen 库生成 RSS（首选路径）。"""
    from feedgen.feed import FeedGenerator

    fg = FeedGenerator()
    fg.load_extension("podcast")

    # 频道元数据
    fg.title(_PODCAST_TITLE)
    fg.subtitle(_PODCAST_SUBTITLE)
    fg.link(href=f"{base_url}/" if base_url else "/", rel="alternate")
    fg.link(href=f"{base_url}/feed.xml" if base_url else "/feed.xml", rel="self")
    fg.description(_PODCAST_SUBTITLE)
    fg.language(_PODCAST_LANGUAGE)
    fg.podcast.itunes_category(_PODCAST_CATEGORY)
    fg.podcast.itunes_author(_PODCAST_AUTHOR)
    fg.podcast.itunes_owner(name=_PODCAST_AUTHOR, email="noreply@example.com")
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_type("episodic")

    for p in projects:
        audio_path = p.get("audio_path", "")
        if not audio_path:
            continue

        enclosure_url = f"{base_url}/file/{audio_path}" if base_url else f"/file/{audio_path}"
        audio_size = p.get("audio_size", 0)
        duration = p.get("audio_duration")
        duration_str = _format_duration(duration)

        fe = fg.add_entry()
        fe.id(enclosure_url)
        fe.title(p.get("name", "Unknown"))
        fe.description(p.get("description") or p.get("name", ""))
        fe.enclosure(enclosure_url, str(audio_size), "audio/mpeg")
        fe.pubDate(_rfc822_date(p.get("created_at", 0)))

        # iTunes 剧集标签
        fe.podcast.itunes_duration(duration_str)
        fe.podcast.itunes_episode_type("full")

        # 链接到项目详情页
        detail_url = f"{base_url}/project/{p.get('dir', '')}/{p.get('name', '')}"
        fe.link(href=detail_url)

    return fg.rss_str(pretty=True).decode("utf-8")


def _generate_with_stdlib(projects: list[dict], base_url: str) -> str:
    """使用标准库 xml.etree 手动构建 RSS（退化路径）。"""
    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")

    rss = ET.Element("rss", attrib={
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    })

    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = _PODCAST_TITLE
    ET.SubElement(channel, "link").text = f"{base_url}/" if base_url else "/"
    ET.SubElement(channel, "description").text = _PODCAST_SUBTITLE
    ET.SubElement(channel, "language").text = _PODCAST_LANGUAGE
    ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}subtitle").text = _PODCAST_SUBTITLE
    ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author").text = _PODCAST_AUTHOR
    ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit").text = "no"
    cat = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}category")
    cat.text = _PODCAST_CATEGORY

    for p in projects:
        audio_path = p.get("audio_path", "")
        if not audio_path:
            continue

        enclosure_url = f"{base_url}/file/{audio_path}" if base_url else f"/file/{audio_path}"
        audio_size = p.get("audio_size", 0)
        duration_str = _format_duration(p.get("audio_duration"))

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = p.get("name", "Unknown")
        ET.SubElement(item, "description").text = p.get("description") or p.get("name", "")
        ET.SubElement(item, "guid", attrib={"isPermaLink": "true"}).text = enclosure_url
        ET.SubElement(item, "pubDate").text = _rfc822_date(p.get("created_at", 0))
        ET.SubElement(item, "enclosure", attrib={
            "url": enclosure_url,
            "length": str(audio_size),
            "type": "audio/mpeg",
        })
        ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration").text = duration_str

    return ET.tostring(rss, encoding="unicode")


def generate_opml(output_dir: Path, base_url: str = "") -> str:
    """生成 OPML 格式导出（用于播客应用批量订阅导入）。

    OPML (Outline Processor Markup Language) 是播客应用通用的
    订阅列表导入/导出格式。用户可以将生成的 OPML 文件导入到
    Pocket Casts、Apple Podcasts 等应用中。

    Args:
        output_dir: 输出根目录
        base_url: 服务器基础 URL

    Returns:
        OPML XML 字符串
    """
    base_url = base_url.rstrip("/")
    projects = scan_projects(output_dir)
    audio_projects = [p for p in projects if p.get("has_audio")]

    rss_url = f"{base_url}/feed.xml" if base_url else "/feed.xml"

    ET.register_namespace("", "http://www.opml.org/spec2")
    opml = ET.Element("opml", attrib={"version": "2.0"})
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "GitHub Trending Audio - 播客订阅"
    ET.SubElement(head, "dateCreated").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    body = ET.SubElement(opml, "body")
    # 主订阅源
    ET.SubElement(body, "outline", attrib={
        "type": "rss",
        "text": _PODCAST_TITLE,
        "title": _PODCAST_TITLE,
        "xmlUrl": rss_url,
        "htmlUrl": f"{base_url}/" if base_url else "/",
    })

    # 每个剧集作为单独 outline（方便按项目筛选）
    if audio_projects:
        episodes_el = ET.SubElement(body, "outline", attrib={
            "text": "所有剧集",
            "title": "所有剧集",
        })
        for p in audio_projects:
            audio_path = p.get("audio_path", "")
            if not audio_path:
                continue
            enclosure_url = f"{base_url}/file/{audio_path}" if base_url else f"/file/{audio_path}"
            ET.SubElement(episodes_el, "outline", attrib={
                "type": "link",
                "text": p.get("name", "Unknown"),
                "title": p.get("name", "Unknown"),
                "url": enclosure_url,
                "htmlUrl": f"{base_url}/project/{p.get('dir', '')}/{p.get('name', '')}" if base_url else "",
            })

    return ET.tostring(opml, encoding="unicode")


def get_feed_stats(output_dir: Path) -> dict[str, Any]:
    """获取播客订阅源统计信息。

    Returns:
        包含剧集数、总时长、总大小等统计数据的字典
    """
    projects = scan_projects(output_dir)
    audio_projects = [p for p in projects if p.get("has_audio")]

    total_duration = sum(p.get("audio_duration") or 0 for p in audio_projects)
    total_size = sum(p.get("audio_size", 0) for p in audio_projects)

    return {
        "episode_count": len(audio_projects),
        "total_duration_seconds": total_duration,
        "total_duration_formatted": _format_duration(total_duration),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
        "feed_title": _PODCAST_TITLE,
        "feed_subtitle": _PODCAST_SUBTITLE,
    }

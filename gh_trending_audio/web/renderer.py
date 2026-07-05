"""HTML 页面渲染器（Phase 1: 从 handler.py 拆分）。

将仪表盘、项目详情页的 HTML 模板渲染逻辑从 DashboardHandler 中分离，
handler 只需调用 ``render_dashboard`` / ``render_project`` 即可。
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .templates import DASHBOARD_HTML, PROJECT_HTML, PLAYER_HTML, _AUDIO_SESSION_JS, _SHARED_JS_UTILS
from .markdown_utils import markdown_to_html
from .project_scanner import get_project_detail, scan_projects


def render_dashboard(output_dir: Path) -> str:
    """渲染仪表盘页面 HTML。

    Args:
        output_dir: 项目输出根目录
    """
    projects = scan_projects(output_dir)
    stats = {
        "total_projects": len(projects),
        "total_audio": sum(1 for p in projects if p["has_audio"]),
        "total_md": len(projects),
    }
    projects_json = json.dumps(projects, ensure_ascii=False, default=str)

    return DASHBOARD_HTML.format(
        total_projects=stats["total_projects"],
        total_audio=stats["total_audio"],
        total_md=stats["total_md"],
        projects_json=projects_json,
        _AUDIO_SESSION_JS=_AUDIO_SESSION_JS,
        _SHARED_JS_UTILS=_SHARED_JS_UTILS,
    )


def render_player() -> str:
    """渲染播放器页面 HTML。"""
    return PLAYER_HTML.format(
        _AUDIO_SESSION_JS=_AUDIO_SESSION_JS,
        _SHARED_JS_UTILS=_SHARED_JS_UTILS,
    )


def render_project(output_dir: Path, dir_name: str, name: str) -> str:
    """渲染项目详情页 HTML。

    Args:
        output_dir: 项目输出根目录
        dir_name: 项目所在子目录名
        name: 项目名（owner_repo 格式）
    """
    detail = get_project_detail(output_dir, dir_name, name)
    if not detail:
        return "<h1>项目未找到</h1>"

    md_html = markdown_to_html(detail["md_content"])
    md_raw = detail["md_content"].replace("</script", "<\\/script") if detail.get("md_content") else ""

    audio_player = ""
    download_audio_btn = ""
    if detail["has_audio"]:
        audio_path = detail["audio_path"]
        audio_player = f"""
                <div class="audio-player">
                    <h3><i data-lucide="volume-2"></i> 音频播放
                        <span class="section-actions">
                            <select class="speed-select" onchange="changeDetailSpeed(this)">
                                <option value="0.75">0.75x</option>
                                <option value="1.0" selected>1.0x</option>
                                <option value="1.25">1.25x</option>
                                <option value="1.5">1.5x</option>
                                <option value="2.0">2.0x</option>
                            </select>
                        </span>
                    </h3>
                    <audio id="detailAudio" controls style="width:100%; max-width:600px;">
                        <source src="/file/{audio_path}" type="audio/mpeg">
                        <track label="字幕" kind="subtitles" srclang="zh" src="/api/subtitle/{dir_name}/{name}?format=vtt" default>
                    </audio>
                </div>
            """
        download_audio_btn = f'<a class="btn btn-secondary" href="/file/{audio_path}" download><i data-lucide="download"></i> 下载音频</a>'
    else:
        audio_player = '<div class="audio-player"><p><i data-lucide="alert-triangle"></i> 此项目暂无音频文件</p></div>'

    download_md_btn = f'<a class="btn btn-secondary" href="/file/{detail["md_path"]}" download><i data-lucide="download"></i> 下载文档</a>'

    script_content = detail.get("script_content", "")
    script_raw = script_content.replace("</script", "<\\/script") if script_content else ""
    script_display = ""
    download_script_btn = ""
    if script_content:
        escaped = html.escape(script_content)
        script_path = detail.get("script_path", "")
        script_display = f"""
                <div class="script-section">
                    <h3><i data-lucide="clipboard-list"></i> 双人对话脚本
                        <span class="section-actions">
                            <button class="mini-btn" onclick="copyText('script')"><i data-lucide="clipboard"></i> 复制脚本</button>
                        </span>
                    </h3>
                    <pre class="script-text">{escaped}</pre>
                </div>
            """
        if script_path:
            download_script_btn = f'<a class="btn btn-secondary" href="/file/{script_path}" download><i data-lucide="download"></i> 下载脚本</a>'

    # 字幕下载按钮（阶段7: SRT/VTT 无障碍访问）
    download_subtitle_btn = ""
    if detail.get("has_audio") and script_content:
        subtitle_base = f"/api/subtitle/{dir_name}/{name}"
        download_subtitle_btn = (
            f'<a class="btn btn-secondary" href="{subtitle_base}?format=srt" download>'
            f'<i data-lucide="captions"></i> SRT</a>'
            f'<a class="btn btn-secondary" href="{subtitle_base}?format=vtt" download>'
            f'<i data-lucide="captions"></i> VTT</a>'
        )

    # 多格式导出按钮（阶段9: PDF/EPUB/JSON/ZIP）
    export_base = f"/api/export/{dir_name}/{name}"
    download_export_btn = (
        f'<a class="btn btn-secondary" href="{export_base}?format=pdf" download>'
        f'<i data-lucide="file-text"></i> PDF</a>'
        f'<a class="btn btn-secondary" href="{export_base}?format=epub" download>'
        f'<i data-lucide="book-open"></i> EPUB</a>'
        f'<a class="btn btn-secondary" href="{export_base}?format=json" download>'
        f'<i data-lucide="braces"></i> JSON</a>'
        f'<a class="btn btn-secondary" href="{export_base}?format=zip" download>'
        f'<i data-lucide="archive"></i> ZIP</a>'
    )

    if name.startswith("compare_"):
        repo_full = ""
    else:
        repo_full = name.replace("_", "/", 1) if "_" in name else name

    return PROJECT_HTML.format(
        name=detail["name"],
        audio_player=audio_player,
        md_html=md_html,
        script_display=script_display,
        download_md_btn=download_md_btn,
        download_audio_btn=download_audio_btn,
        download_script_btn=download_script_btn,
        download_subtitle_btn=download_subtitle_btn,
        download_export_btn=download_export_btn,
        script_raw=script_raw,
        md_raw=md_raw,
        qa_dir=dir_name,
        qa_project=name,
        repo_full=repo_full,
        proj_language=detail.get("language", "") or "",
        overview_stars=detail.get("stars", 0) or 0,
        overview_forks=detail.get("forks", 0) or 0,
        _AUDIO_SESSION_JS=_AUDIO_SESSION_JS,
        _SHARED_JS_UTILS=_SHARED_JS_UTILS,
    )

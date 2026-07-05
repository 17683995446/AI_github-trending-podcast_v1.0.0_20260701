"""多格式导出器（阶段9: 开源工具集成 - 数据可携带性）。

将项目内容导出为多种格式，让用户可以灵活使用生成的内容：

    - ``export_json()``  → JSON 格式（元数据 + 全部内容）
    - ``export_zip()``   → ZIP 打包（md + script + mp3 + srt + vtt）
    - ``export_pdf()``   → PDF 文档（fpdf2 + CJK 字体）
    - ``export_epub()``  → EPUB 电子书（ebooklib）

依赖：
    - fpdf2（可选，PDF 生成）
    - ebooklib（可选，EPUB 生成）
    - 标准库 zipfile、json（ZIP/JSON）

设计原则：
    - 第一性原理：数据属于用户，应支持多格式导出
    - 优雅降级：fpdf2/ebooklib 不可用时返回友好错误
    - CJK 支持：PDF 使用 Noto Sans CJK 字体
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .constants import PDF_EXPORT_TIMEOUT
from .logging_config import get_logger
from .project_scanner import get_project_detail

logger = get_logger(__name__)

# CJK 字体路径（系统安装的 Noto Sans CJK）
_CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto-cjk-otf/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def _find_cjk_font() -> str | None:
    """查找系统上可用的 CJK 字体。"""
    for path in _CJK_FONT_CANDIDATES:
        if Path(path).exists():
            return path
    # 尝试 fc-list 查找
    try:
        import subprocess
        result = subprocess.run(
            ["fc-list", ":lang=zh", "file"],
            capture_output=True, text=True, timeout=PDF_EXPORT_TIMEOUT,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                line = line.strip().rstrip(":")
                if line and (line.endswith(".otf") or line.endswith(".ttf") or line.endswith(".ttc")):
                    return line
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def export_json(output_dir: Path, dir_name: str, proj_name: str) -> bytes | None:
    """导出项目数据为 JSON 格式。

    Returns:
        JSON bytes，项目不存在返回 None
    """
    project = get_project_detail(output_dir, dir_name, proj_name)
    if not project:
        return None

    # 移除不可序列化的字段
    export_data = {
        "name": project.get("name"),
        "dir": project.get("dir"),
        "description": project.get("description"),
        "stars": project.get("stars"),
        "forks": project.get("forks"),
        "language": project.get("language"),
        "license": project.get("license"),
        "topics": project.get("topics"),
        "has_audio": project.get("has_audio"),
        "audio_duration": project.get("audio_duration"),
        "audio_size": project.get("audio_size"),
        "md_size": project.get("md_size"),
        "created_at": project.get("created_at"),
        "md_content": project.get("md_content", ""),
        "script_content": project.get("script_content", ""),
    }
    return json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")


def export_zip(output_dir: Path, dir_name: str, proj_name: str) -> bytes | None:
    """导出项目所有文件为 ZIP 打包。

    包含：md、script.txt、mp3（如有）、srt、vtt
    """
    project = get_project_detail(output_dir, dir_name, proj_name)
    if not project:
        return None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Markdown 文档
        md_content = project.get("md_content", "")
        if md_content:
            zf.writestr(f"{proj_name}.md", md_content)

        # 脚本
        script_content = project.get("script_content", "")
        if script_content:
            zf.writestr(f"{proj_name}_script.txt", script_content)

        # 音频文件
        audio_path = project.get("audio_path")
        if audio_path:
            full_audio = output_dir / audio_path
            if full_audio.exists():
                zf.write(full_audio, f"{proj_name}.mp3")

        # SRT 字幕
        try:
            from .subtitle_gen import generate_subtitle_for_project
            srt = generate_subtitle_for_project(output_dir, dir_name, proj_name, "srt")
            if srt:
                zf.writestr(f"{proj_name}.srt", srt)
        except (OSError, ValueError):
            logger.debug("SRT 生成失败", exc_info=True)

        # VTT 字幕
        try:
            from .subtitle_gen import generate_subtitle_for_project
            vtt = generate_subtitle_for_project(output_dir, dir_name, proj_name, "vtt")
            if vtt:
                zf.writestr(f"{proj_name}.vtt", vtt)
        except (OSError, ValueError):
            logger.debug("VTT 生成失败", exc_info=True)

        # 元数据 JSON
        meta = {
            "name": project.get("name"),
            "description": project.get("description"),
            "stars": project.get("stars"),
            "language": project.get("language"),
            "license": project.get("license"),
        }
        zf.writestr("metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))

    return buf.getvalue()


def _markdown_to_plain_text(md: str) -> str:
    """将 Markdown 转换为纯文本（去除格式标记）。"""
    # 移除代码块
    text = re.sub(r"```[\s\S]*?```", "", md)
    # 移除行内代码
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 移除图片
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    # 移除链接，保留文本
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 移除粗体/斜体
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # 移除标题标记
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # 移除引用
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    # 移除水平线
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # 移除列表标记
    text = re.sub(r"^[\-\*\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # 移除表格分隔行
    text = re.sub(r"^\|[\s\-\|:]+\|$", "", text, flags=re.MULTILINE)
    # 清理多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def export_pdf(output_dir: Path, dir_name: str, proj_name: str) -> bytes | None:
    """导出项目文档为 PDF。

    使用 fpdf2 + Noto Sans CJK 字体生成 PDF。
    """
    project = get_project_detail(output_dir, dir_name, proj_name)
    if not project:
        return None

    md_content = project.get("md_content", "")
    if not md_content:
        return None

    try:
        from fpdf import FPDF
    except ImportError:
        logger.warning("fpdf2 不可用，无法生成 PDF")
        return None

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)

    # 添加 CJK 字体
    font_path = _find_cjk_font()
    if font_path:
        try:
            pdf.add_font("CJK", "", font_path)
            pdf.add_font("CJK", "B", font_path)
            font_family = "CJK"
        except OSError:
            logger.warning(f"字体加载失败: {font_path}", exc_info=True)
            font_family = "Helvetica"
    else:
        font_family = "Helvetica"

    pdf.add_page()
    pdf.set_font(font_family, "B", 16)

    # 标题
    title = proj_name.replace("_", "/")
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(5)

    # 元数据
    pdf.set_font(font_family, "", 10)
    meta_parts = []
    if project.get("language"):
        meta_parts.append(f"语言: {project['language']}")
    if project.get("stars"):
        meta_parts.append(f"星标: {project['stars']:,}")
    if project.get("license"):
        meta_parts.append(f"协议: {project['license']}")
    if meta_parts:
        pdf.cell(0, 6, " | ".join(meta_parts), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # 正文
    pdf.set_font(font_family, "", 10)
    plain_text = _markdown_to_plain_text(md_content)
    # 分行写入
    page_width = pdf.w - 2 * pdf.l_margin
    for line in plain_text.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        # 限制单行字符数，防止超宽内容
        if len(line) > 200:
            line = line[:200] + "..."
        try:
            pdf.multi_cell(page_width, 5, line)
        except (ValueError, RuntimeError):
            # 跳过无法渲染的行（如特殊字符或过宽内容）
            try:
                safe = line.encode("ascii", "replace").decode()
                pdf.multi_cell(page_width, 5, safe)
            except (ValueError, RuntimeError):
                continue

    return pdf.output()


def export_epub(output_dir: Path, dir_name: str, proj_name: str) -> bytes | None:
    """导出项目文档为 EPUB 电子书。

    使用 ebooklib 生成标准 EPUB 格式。
    """
    project = get_project_detail(output_dir, dir_name, proj_name)
    if not project:
        return None

    md_content = project.get("md_content", "")
    if not md_content:
        return None

    try:
        from ebooklib import epub
    except ImportError:
        logger.warning("ebooklib 不可用，无法生成 EPUB")
        return None

    try:
        import markdown as md_lib
        html_content = md_lib.markdown(md_content, extensions=["tables", "fenced_code"])
    except ImportError:
        html_content = f"<pre>{md_content}</pre>"

    title = proj_name.replace("_", "/")
    book = epub.EpubBook()
    book.set_identifier(f"gh-trending-{proj_name}")
    book.set_title(title)
    book.set_language("zh")
    book.add_author("GH Trending Audio")

    # 章节
    chapter = epub.EpubHtml(
        title=title,
        file_name="content.xhtml",
        lang="zh",
    )
    chapter.content = f"<html><body><h1>{title}</h1>{html_content}</body></html>"
    book.add_item(chapter)

    # 目录
    book.toc = [chapter]

    # 添加导航文件
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 书脊
    book.spine = ["nav", chapter]

    # 写入 BytesIO
    buf = io.BytesIO()
    epub.write_epub(buf, book, {})
    return buf.getvalue()


def export_project(
    output_dir: Path,
    dir_name: str,
    proj_name: str,
    fmt: str = "json",
) -> tuple[bytes | None, str, str]:
    """统一导出入口。

    Args:
        fmt: "json" / "zip" / "pdf" / "epub"

    Returns:
        (data, filename, content_type) 元组，项目不存在返回 (None, "", "")
    """
    fmt = fmt.lower()
    exporters = {
        "json": (export_json, "application/json", ".json"),
        "zip": (export_zip, "application/zip", ".zip"),
        "pdf": (export_pdf, "application/pdf", ".pdf"),
        "epub": (export_epub, "application/epub+zip", ".epub"),
    }

    if fmt not in exporters:
        return None, "", ""

    export_fn, content_type, ext = exporters[fmt]
    data = export_fn(output_dir, dir_name, proj_name)
    if data is None:
        return None, "", ""

    filename = f"{proj_name}{ext}"
    return data, filename, content_type

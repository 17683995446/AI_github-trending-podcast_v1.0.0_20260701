"""字幕生成器（阶段7: 开源工具集成 - 音频无障碍访问）。

将音频脚本（A:/B: 对话格式）转换为 SRT 和 WebVTT 字幕格式，
基于音频时长和文本长度智能估算时间戳，让音频内容可被搜索、
无障碍访问、并支持静音观看。

核心功能：
    - ``generate_srt()``    → SRT 字幕字符串
    - ``generate_vtt()``    → WebVTT 字幕字符串
    - ``parse_dialogue()``  → 解析 A:/B: 对话脚本为分段列表

设计原则：
    - 第一性原理：字幕 = 文本 + 时间戳；时间戳基于音频时长按字数比例分配
    - 零依赖：纯 Python 标准库实现，不依赖外部字幕库
    - 优雅降级：无音频时长时按固定速率估算
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .project_scanner import get_audio_duration

logger = get_logger(__name__)

# 默认语速（中文字/秒），用于无音频时长时的估算
_DEFAULT_CHARS_PER_SECOND = 4.0
# 单条字幕最大字符数（超出则拆分）
_MAX_SUBTITLE_CHARS = 80
# 单条字幕最小显示时间（毫秒）
_MIN_DURATION_MS = 1500


@dataclass
class SubtitleSegment:
    """字幕分段：一段文本 + 开始/结束时间戳。"""
    text: str
    start_ms: int
    end_ms: int
    speaker: str = ""  # "A" / "B" / "" (无说话人标记)


def parse_dialogue(script: str) -> list[dict[str, str]]:
    """解析音频脚本为对话分段列表。

    支持格式：
        A: 这是说话人A的台词
        B: 这是说话人B的台词
        无标记的行作为旁白

    Args:
        script: 音频脚本文本

    Returns:
        分段列表，每项含 ``speaker`` 和 ``text`` 键
    """
    segments: list[dict[str, str]] = []
    current_speaker = ""
    current_text: list[str] = []

    for line in script.strip().split("\n"):
        line = line.strip()
        if not line:
            if current_text:
                segments.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text),
                })
                current_text = []
                current_speaker = ""
            continue

        # 检测 A: / B: 等说话人标记
        match = re.match(r"^([A-Za-z])\s*[:：]\s*(.*)", line)
        if match:
            # 保存前一段
            if current_text:
                segments.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_text),
                })
                current_text = []
            current_speaker = match.group(1).upper()
            text = match.group(2).strip()
            if text:
                current_text.append(text)
        else:
            current_text.append(line)

    # 保存最后一段
    if current_text:
        segments.append({
            "speaker": current_speaker,
            "text": " ".join(current_text),
        })

    return segments


def _split_long_text(text: str, max_chars: int = _MAX_SUBTITLE_CHARS) -> list[str]:
    """将过长的文本拆分为多条字幕（按句子/标点断句）。"""
    if len(text) <= max_chars:
        return [text]

    # 按句号、问号、感叹号、分号拆分
    sentences = re.split(r"(?<=[。！？；!?;])", text)
    chunks: list[str] = []
    current = ""

    for sent in sentences:
        if not sent:
            continue
        if len(current) + len(sent) <= max_chars:
            current += sent
        else:
            if current:
                chunks.append(current.strip())
            # 如果单个句子超长，硬切
            while len(sent) > max_chars:
                chunks.append(sent[:max_chars])
                sent = sent[max_chars:]
            current = sent

    if current:
        chunks.append(current.strip())

    return chunks


def estimate_timestamps(
    segments: list[dict[str, str]],
    total_duration_seconds: float | None = None,
) -> list[SubtitleSegment]:
    """为对话分段估算时间戳。

    时间分配策略：
        - 有音频时长：按字符数比例分配总时长
        - 无音频时长：按默认语速（4字/秒）估算

    Args:
        segments: parse_dialogue() 返回的分段列表
        total_duration_seconds: 音频总时长（秒），None 则按默认语速估算

    Returns:
        SubtitleSegment 列表，含 start_ms / end_ms 时间戳
    """
    # 先拆分过长的段落
    all_chunks: list[tuple[str, str]] = []  # (speaker, text)
    for seg in segments:
        speaker = seg.get("speaker", "")
        text = seg.get("text", "")
        if not text:
            continue
        for chunk in _split_long_text(text):
            all_chunks.append((speaker, chunk))

    if not all_chunks:
        return []

    # 计算每段的字符权重
    weights = [max(len(text), 1) for _, text in all_chunks]
    total_weight = sum(weights)

    # 计算总时长（毫秒）
    if total_duration_seconds and total_duration_seconds > 0:
        total_ms = int(total_duration_seconds * 1000)
    else:
        # 按默认语速估算
        total_ms = int((total_weight / _DEFAULT_CHARS_PER_SECOND) * 1000)

    # 按权重分配时间
    result: list[SubtitleSegment] = []
    current_ms = 0

    for i, (speaker, text) in enumerate(all_chunks):
        weight = weights[i]
        # 该段时长 = 总时长 * (该段字数 / 总字数)
        if i == len(all_chunks) - 1:
            # 最后一段用剩余时间
            segment_ms = total_ms - current_ms
        else:
            segment_ms = int(total_ms * weight / total_weight)

        segment_ms = max(segment_ms, _MIN_DURATION_MS)
        end_ms = current_ms + segment_ms
        # 仅在非最后段时限制不超过总时长（最后段允许超出以保证最小显示时间）
        if i < len(all_chunks) - 1:
            end_ms = min(end_ms, total_ms)

        result.append(SubtitleSegment(
            text=text,
            start_ms=current_ms,
            end_ms=end_ms,
            speaker=speaker,
        ))
        current_ms = end_ms

    return result


def _format_srt_time(ms: int) -> str:
    """格式化毫秒为 SRT 时间戳: HH:MM:SS,mmm"""
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _format_vtt_time(ms: int) -> str:
    """格式化毫秒为 WebVTT 时间戳: HH:MM:SS.mmm"""
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def generate_srt(segments: list[SubtitleSegment]) -> str:
    """生成 SRT 格式字幕。

    Args:
        segments: SubtitleSegment 列表

    Returns:
        SRT 格式字幕字符串
    """
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        text = f"{seg.speaker}: {seg.text}" if seg.speaker else seg.text
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg.start_ms)} --> {_format_srt_time(seg.end_ms)}")
        lines.append(text)
        lines.append("")  # 空行分隔
    return "\n".join(lines)


def generate_vtt(segments: list[SubtitleSegment]) -> str:
    """生成 WebVTT 格式字幕。

    Args:
        segments: SubtitleSegment 列表

    Returns:
        WebVTT 格式字幕字符串
    """
    lines: list[str] = ["WEBVTT", ""]
    for seg in segments:
        text = f"{seg.speaker}: {seg.text}" if seg.speaker else seg.text
        lines.append(f"{_format_vtt_time(seg.start_ms)} --> {_format_vtt_time(seg.end_ms)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def generate_subtitle_for_project(
    output_dir: Path,
    dir_name: str,
    proj_name: str,
    fmt: str = "srt",
) -> str | None:
    """为指定项目生成字幕文件内容。

    Args:
        output_dir: 输出根目录
        dir_name: 项目所在目录名（如 output_demo）
        proj_name: 项目名（如 owner_repo）
        fmt: "srt" 或 "vtt"

    Returns:
        字幕字符串，项目不存在返回 None
    """
    from .project_scanner import get_project_detail

    project = get_project_detail(output_dir, dir_name, proj_name)
    if not project:
        return None

    script = project.get("script_content", "")
    if not script:
        return None

    # 解析对话
    segments = parse_dialogue(script)
    if not segments:
        return None

    # 获取音频时长
    duration = project.get("audio_duration")

    # 估算时间戳
    sub_segments = estimate_timestamps(segments, duration)

    if fmt.lower() == "vtt":
        return generate_vtt(sub_segments)
    return generate_srt(sub_segments)

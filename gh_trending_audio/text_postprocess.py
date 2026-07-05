"""text_postprocess.py —— LLM 输出音频脚本的后处理

本模块负责对 LLM 生成的音频脚本进行基于正则的后处理，使其更适合 TTS 朗读：

  - 移除 Markdown 标题 / 表格 / 链接 / URL 等格式符号
  - 保留 ``A:`` / ``B:`` 说话人标记，仅清理说话内容
  - 中文模式：将英文连词（and / to / the / of / for / with / in）转为中文
  - 英文标点转中文标点（同时保护版本号中的点，如 ``2.9.1``）
  - 修复重复字符 / 重复词 / 重复双字词 / 连续重复行
  - 跳过开头标题行与乱码行

该逻辑原先位于 ``LLMEnhancer._clean_audio_script`` 静态方法，为便于复用与
单元测试而拆分至独立模块。``llm_enhancer`` 仍保留同名静态方法以维持向后兼容。
"""

from __future__ import annotations

import re

from .logging_config import get_logger

logger = get_logger(__name__)


def clean_audio_script(text: str) -> str:
    """清理 LLM 输出的音频脚本，保留 A:/B: 说话人标记，确保适合 TTS 朗读。

    Args:
        text: LLM 生成的原始音频脚本文本。

    Returns:
        经过清理后的纯文本音频脚本，行与行之间以 ``\\n`` 分隔。
    """
    logger.debug("开始清理音频脚本，原始长度=%d 字符", len(text))

    lines = text.split("\n")
    cleaned_lines = []
    skip_header = True  # 跳过开头的标题行

    for line in lines:
        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 检测说话人标记（A: 或 B: 开头，保留不清理）
        is_dialogue = bool(re.match(r"^[AB][:：]", line))

        if not is_dialogue:
            # 移除 Markdown 标题符号
            line = re.sub(r"^#+\s*", "", line)

            # 移除表格相关内容
            if line.startswith("|") or line.startswith("---"):
                continue

            # 移除 Markdown 链接，保留文字
            line = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", line)

            # 移除 URL
            line = re.sub(r"https?://\S+", "", line)

            # 移除 Markdown 格式符号
            line = re.sub(r"[*_>`#|-]", "", line)

            # 跳过开头的标题行
            if skip_header:
                if re.match(r"^(音频脚本|第二部分|第三部分|纯文本|脚本|双人对话)[:：]?", line):
                    continue
                if len(line) < 15 and ("脚本" in line or "部分" in line or "音频" in line or "对话" in line):
                    continue
                skip_header = False
        else:
            # 对话行：只清理说话内容部分，保留 A:/B: 前缀
            speaker = line[0]
            content = line[2:].strip()

            # 清理格式符号
            content = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", content)
            content = re.sub(r"https?://\S+", "", content)
            content = re.sub(r"[*_>`#]", "", content)

            # 中文模式：清理英文连词和英文标点
            # 替换英文连词为中文
            content = re.sub(r"\s+and\s+", "和", content)
            content = re.sub(r"\s+to\s+", "到", content)
            content = re.sub(r"\s+the\s+", "", content)
            content = re.sub(r"\s+of\s+", "的", content)
            content = re.sub(r"\s+for\s+", "用于", content)
            content = re.sub(r"\s+with\s+", "使用", content)
            content = re.sub(r"\s+in\s+", "在", content)

            # 英文标点转中文标点（但保留版本号中的点，如 2.9.1）
            # 先保护版本号格式（数字.数字）
            content = re.sub(r"(\d)\.(\d)", r"\1§DOT§\2", content)
            content = content.replace(". ", "。")
            content = content.replace(".", "。")
            content = content.replace(", ", "，")
            content = content.replace(",", "，")
            content = content.replace("? ", "？")
            content = content.replace("?", "？")
            content = content.replace("! ", "！")
            content = content.replace("!", "！")
            content = content.replace(": ", "：")
            # 恢复版本号中的点
            content = content.replace("§DOT§", ".")

            # 修复重复字符（如 "解解算法" -> "解算法"，"configconfig" -> "config"）
            content = re.sub(r"(.)\1{2,}", r"\1", content)
            # 修复重复词（英文，如 "configconfig" -> "config"）
            content = re.sub(r"([a-zA-Z]{3,})\1", r"\1", content)

            # 跳过乱码行（中文字符太少且整体太短）
            chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
            if chinese_chars < 3 and len(content) < 10:
                logger.debug("跳过乱码对话行：%r", content)
                continue

            line = f"{speaker}: {content}"

        # 修复重复双字词（如 "可以可以" -> "可以"）
        for length in [2, 3, 4]:
            pattern = r"(.{" + str(length) + r"})\1{1,}"
            line = re.sub(pattern, r"\1", line)

        # 去除连续重复行
        if cleaned_lines and line.strip() == cleaned_lines[-1].strip():
            continue

        # 清理多余的句号
        line = re.sub(r"。{2,}", "。", line)
        line = re.sub(r"^[。.,，]+", "", line.strip())

        if line.strip():
            cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    logger.debug("音频脚本清理完成，结果长度=%d 字符，共 %d 行", len(result), len(cleaned_lines))
    return result

"""Piper TTS 引擎（阶段10: 本地神经语音合成）。

Piper 是一个快速、高质量的本地神经 TTS 引擎，
支持多种语言和音色，完全离线运行，无需 API Key。

通过 ``@register_tts_engine("piper")`` 注册到 TTS 引擎注册表，
当系统安装了 piper 二进制时自动可用。

依赖：
    - piper 二进制（系统安装）
    - Piper 模型文件（.onnx + .json）
    - ffmpeg（可选，WAV→MP3 转码）

设计原则：
    - 第一性原理：本地 TTS = 无网络依赖 + 无 API 费用
    - 注册机制：通过 registry 自动发现，无需修改 if-elif
    - 优雅降级：piper 未安装时 is_available() 返回 False
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .constants import PIPER_TTS_TIMEOUT, PIPER_DOWNLOAD_TIMEOUT
from .exceptions import TTSError
from .logging_config import get_logger
from .registry import TTSBackend, register_tts_engine

logger = get_logger(__name__)


def _find_piper_binary() -> str | None:
    """查找 piper 二进制路径。"""
    for name in ["piper", "piper-tts"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def _find_piper_models() -> list[tuple[str, str]]:
    """查找可用的 Piper 模型。

    Returns:
        [(onnx_path, config_path), ...] 列表
    """
    # 常见模型目录
    search_dirs = [
        os.environ.get("PIPER_MODELS", ""),
        os.path.expanduser("~/.local/share/piper"),
        "/usr/share/piper/models",
        os.path.expanduser("~/piper_models"),
    ]

    models: list[tuple[str, str]] = []
    for dir_path in search_dirs:
        if not dir_path or not os.path.isdir(dir_path):
            continue
        for root, _dirs, files in os.walk(dir_path):
            onnx_files = [f for f in files if f.endswith(".onnx")]
            for onnx in onnx_files:
                onnx_path = os.path.join(root, onnx)
                # 配置文件: model.onnx → model.onnx.json
                config_path = onnx_path + ".json"
                if os.path.exists(config_path):
                    models.append((onnx_path, config_path))
    return models


def _select_piper_model(language: str = "zh") -> tuple[str, str] | None:
    """根据语言选择合适的 Piper 模型。

    Args:
        language: "zh" 或 "en"

    Returns:
        (onnx_path, config_path) 或 None
    """
    models = _find_piper_models()
    if not models:
        return None

    if language == "zh":
        # 优先选择中文模型
        for onnx, config in models:
            name = os.path.basename(onnx).lower()
            if "zh" in name or "chinese" in name:
                return (onnx, config)
    else:
        # 英文模型
        for onnx, config in models:
            name = os.path.basename(onnx).lower()
            if "en" in name or "english" in name:
                return (onnx, config)

    # 回退到第一个可用模型
    return models[0]


@register_tts_engine("piper")
class _PiperBackend(TTSBackend):
    """Piper 本地 TTS 引擎后端。"""

    @property
    def name(self) -> str:
        return "piper"

    @property
    def requires_network(self) -> bool:
        return False  # 完全离线

    @staticmethod
    def is_available() -> bool:
        """检查 piper 二进制和模型是否可用。"""
        return _find_piper_binary() is not None and len(_find_piper_models()) > 0

    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: str = "",
        rate: str = "+0%",
        volume: str = "+0%",
        language: str = "zh",
    ) -> str:
        """使用 Piper 合成语音。

        Args:
            text: 待合成文本
            output_path: 输出文件路径（.wav 或 .mp3）
            voice: 音色（忽略，Piper 按模型区分音色）
            rate: 语速（Piper 不直接支持，忽略）
            volume: 音量（忽略）
            language: 语言 zh/en

        Returns:
            实际输出文件路径
        """
        piper_bin = _find_piper_binary()
        if not piper_bin:
            raise TTSError("Piper 二进制未安装")

        model = _select_piper_model(language)
        if not model:
            raise TTSError(f"未找到 {language} 语言的 Piper 模型")

        onnx_path, config_path = model
        output_path = str(output_path)
        want_mp3 = output_path.endswith(".mp3")

        # Piper 输出 WAV
        if want_mp3:
            wav_path = output_path.replace(".mp3", ".wav")
        else:
            wav_path = output_path

        # 调用 piper 合成
        cmd = [
            piper_bin,
            "--model", onnx_path,
            "--config", config_path,
            "--output_file", wav_path,
        ]

        logger.info(f"Piper TTS: 模型={os.path.basename(onnx_path)}, 文本长度={len(text)}")
        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=PIPER_TTS_TIMEOUT,
        )

        if result.returncode != 0:
            raise TTSError(f"Piper 合成失败: {result.stderr}")

        # WAV → MP3 转码
        if want_mp3:
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                subprocess.run(
                    [ffmpeg, "-y", "-i", wav_path, "-codec:a", "libmp3lame",
                     "-qscale:a", "2", output_path],
                    capture_output=True,
                    timeout=PIPER_DOWNLOAD_TIMEOUT,
                )
                # 删除临时 WAV
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass
            else:
                # 无 ffmpeg，直接重命名为 .wav
                shutil.move(wav_path, output_path.replace(".mp3", ".wav"))
                return output_path.replace(".mp3", ".wav")

        return output_path

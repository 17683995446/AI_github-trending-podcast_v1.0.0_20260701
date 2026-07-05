"""
tts_engine.py —— 多引擎文本转语音（TTS）

引擎优先级（自动回退）：
  1. siliconflow —— 硅基流动 CosyVoice2，高质量神经网络语音（需 API Key）
  2. edge-tts   —— 微软 Edge 在线 TTS，高质量神经网络语音（需联网 WebSocket）
  3. espeak-ng  —— 离线 TTS 引擎，系统级安装，无需联网（质量较低但稳定）

双人对话模式支持所有三个引擎：
  - siliconflow：CosyVoice2 多音色（david/claire/alex/benjamin 等）
  - edge-tts：交替使用不同 Neural 语音（云希/晓晓/云扬 等）
  - espeak-ng：单人模式回退（不区分音色）

成本对比：
  - siliconflow：免费额度（9B 以下模型永久免费）
  - edge-tts：免费（云服务，高质量，需联网）
  - espeak-ng：免费（本地，离线，质量较低）
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import Callable, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .constants import TTS_SYNTHESIS_TIMEOUT, TTS_FALLBACK_TIMEOUT
from .exceptions import TTSError
from .logging_config import get_logger
from .registry import (
    TTSBackend,
    get_tts_engine,
    get_tts_engines_sorted_by_priority,
    list_tts_engines,
    register_tts_engine,
)

# 注册 Piper 本地 TTS 引擎（阶段10: 零成本本地部署）
try:
    from .piper_tts import _PiperBackend  # noqa: F401 — 注册触发
except ImportError:
    pass

console = Console()
logger = get_logger(__name__)

# 预设语音：按引擎和语言分组
VOICES = {
    "siliconflow": {
        "zh": {
            "male_calm": "FunAudioLLM/CosyVoice2-0.5B:alex",       # 沉稳男声
            "male_deep": "FunAudioLLM/CosyVoice2-0.5B:benjamin",    # 低沉男声
            "male_magnetic": "FunAudioLLM/CosyVoice2-0.5B:charles", # 磁性男声
            "male_cheerful": "FunAudioLLM/CosyVoice2-0.5B:david",   # 欢快男声
            "female_calm": "FunAudioLLM/CosyVoice2-0.5B:anna",     # 沉稳女声
            "female_passionate": "FunAudioLLM/CosyVoice2-0.5B:bella", # 激情女声
            "female_gentle": "FunAudioLLM/CosyVoice2-0.5B:claire",  # 温柔女声
            "female_cheerful": "FunAudioLLM/CosyVoice2-0.5B:diana", # 欢快女声
        },
        "en": {
            "male_calm": "FunAudioLLM/CosyVoice2-0.5B:alex",
            "female_gentle": "FunAudioLLM/CosyVoice2-0.5B:claire",
        },
    },
    "edge-tts": {
        "zh": {
            "female_warm": "zh-CN-XiaoxiaoNeural",
            "male_warm": "zh-CN-YunxiNeural",
            "female_lively": "zh-CN-XiaoyiNeural",
            "male_calm": "zh-CN-YunyangNeural",
        },
        "en": {
            "female_warm": "en-US-JennyNeural",
            "male_warm": "en-US-GuyNeural",
            "female_calm": "en-US-AriaNeural",
            "male_calm": "en-US-DavisNeural",
        },
    },
    "espeak-ng": {
        "zh": {
            "default": "cmn",
        },
        "en": {
            "default": "en",
        },
    },
}

DEFAULT_VOICE = {
    "siliconflow": {"zh": "FunAudioLLM/CosyVoice2-0.5B:alex", "en": "FunAudioLLM/CosyVoice2-0.5B:alex"},
    "edge-tts": {"zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-JennyNeural"},
    "espeak-ng": {"zh": "cmn", "en": "en"},
}

# [Deprecated] 引擎优先级（auto 模式按此顺序尝试）
# 已被引擎自注册的 ``priority`` 参数取代（见 register_tts_engine），
# 保留此列表仅为向后兼容，新引擎应通过 ``priority`` 参数声明优先级。
_ENGINE_PRIORITY: list[str] = ["siliconflow", "edge-tts", "espeak-ng"]


class TTSEngine:
    """多引擎 TTS 封装：文本 -> 音频文件"""

    def __init__(
        self,
        voice: Optional[str] = None,
        language: str = "zh",
        rate: str = "+0%",
        volume: str = "+0%",
        engine: str = "auto",
        style: str = "dialogue",
    ):
        """
        Args:
            voice:    指定语音名称（覆盖默认）
            language: "zh" 或 "en"
            rate:    语速，例如 "+10%"
            volume:  音量
            engine:  引擎选择 "auto"（自动回退）、"edge-tts"、"espeak-ng"
            style:   播客风格，影响双人对话音色分配
        """
        self.language = language
        self.rate = rate
        self.volume = volume
        self.engine = engine
        self.style = style
        self.voice = voice
        self._active_engine: str = ""  # 实际使用的引擎
        self._failed_engines: set[str] = set()  # 已知不可用的引擎（批量场景下避免重复尝试）

    def text_to_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
    ) -> str:
        """
        将文本转为语音并保存为 MP3。

        支持双人对话格式：脚本中用 "A: ..." 和 "B: ..." 标记说话人，
        会自动为 A 和 B 分配不同音色分别合成再拼接。

        自动引擎选择：
            - engine="auto"：优先 siliconflow -> edge-tts -> espeak-ng
            - engine="siliconflow"：仅用硅基流动 CosyVoice2
            - engine="edge-tts"：仅用 edge-tts
            - engine="espeak-ng"：仅用 espeak-ng

        Returns:
            输出文件路径
        """
        if voice:
            self.voice = voice

        # 检测双人对话格式
        dialogue_segments = self._parse_dialogue(text)
        if dialogue_segments:
            return self._synthesize_dialogue(dialogue_segments, output_path)

        # 单人模式：通过注册表发现引擎
        if self.engine == "auto":
            for eng_name, backend_cls in get_tts_engines_sorted_by_priority():
                if eng_name in self._failed_engines:
                    continue
                if backend_cls is None:
                    continue
                try:
                    logger.debug("尝试 %s 引擎...", eng_name)
                    backend = backend_cls(self)
                    result = backend.synthesize(text, output_path)
                    self._active_engine = eng_name
                    return result
                except (TTSError, OSError, RuntimeError, ImportError) as e:
                    logger.warning("%s 引擎不可用: %s", eng_name, e, exc_info=True)
                    self._failed_engines.add(eng_name)
            raise TTSError("所有 TTS 引擎均不可用")
        else:
            backend_cls = get_tts_engine(self.engine)
            if backend_cls is None:
                raise TTSError(f"未知 TTS 引擎: {self.engine}")
            backend = backend_cls(self)
            result = backend.synthesize(text, output_path)
            self._active_engine = self.engine
            return result

    # ------------------------------------------------------------------
    # 双人对话合成
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_dialogue(text: str) -> list[tuple[str, str]] | None:
        """
        解析双人对话脚本。

        格式：每行以 "A: " 或 "B: " 开头。
        返回 [("A", "说话内容"), ("B", "说话内容"), ...] 或 None（非对话格式）。
        """
        import re

        lines = text.strip().split("\n")
        segments: list[tuple[str, str]] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^([AB])[:：]\s*(.+)", line)
            if match:
                speaker = match.group(1)
                content = match.group(2).strip()
                if content:
                    segments.append((speaker, content))
            else:
                # 非对话行：如果有已收集的对话段，当作延续内容
                if segments and segments[-1][0]:
                    segments[-1] = (segments[-1][0], segments[-1][1] + " " + line)

        # 至少 2 段且包含 A 和 B 才算对话格式
        if len(segments) >= 2:
            speakers = set(s for s, _ in segments)
            if len(speakers) >= 2:
                return segments
        return None

    # 双人对话音色映射：硅基流动 + edge-tts 双引擎
    _DIALOGUE_VOICES = {
        "siliconflow": {
            "dialogue": {"A": "FunAudioLLM/CosyVoice2-0.5B:david", "B": "FunAudioLLM/CosyVoice2-0.5B:claire"},
            "debate": {"A": "FunAudioLLM/CosyVoice2-0.5B:david", "B": "FunAudioLLM/CosyVoice2-0.5B:alex"},
            "interview": {"A": "FunAudioLLM/CosyVoice2-0.5B:david", "B": "FunAudioLLM/CosyVoice2-0.5B:claire"},
            "news": {"A": "FunAudioLLM/CosyVoice2-0.5B:benjamin", "B": "FunAudioLLM/CosyVoice2-0.5B:claire"},
            "story": {"A": "FunAudioLLM/CosyVoice2-0.5B:benjamin", "B": "FunAudioLLM/CosyVoice2-0.5B:david"},
        },
        "edge-tts": {
            "dialogue": {"A": "zh-CN-YunxiNeural", "B": "zh-CN-XiaoxiaoNeural"},
            "debate": {"A": "zh-CN-YunxiNeural", "B": "zh-CN-YunyangNeural"},
            "interview": {"A": "zh-CN-YunxiNeural", "B": "zh-CN-XiaoxiaoNeural"},
            "news": {"A": "zh-CN-YunyangNeural", "B": "zh-CN-XiaoxiaoNeural"},
            "story": {"A": "zh-CN-YunyangNeural", "B": "zh-CN-YunxiNeural"},
        },
    }

    def _synthesize_dialogue(
        self, segments: list[tuple[str, str]], output_path: str
    ) -> str:
        """
        合成双人对话音频：A 和 B 分别用不同音色合成，最后拼接。

        引擎降级链：siliconflow（CosyVoice2 多音色）→ edge-tts（交替音色）→ espeak-ng。
        不再因 siliconflow 不可用而直接跳到 espeak-ng，edge-tts 同样支持双人对话。
        """
        # 确定可用引擎：siliconflow → edge-tts → espeak-ng
        dialogue_engine = "espeak-ng"
        try:
            from .config import TTS_API_KEY
            if TTS_API_KEY:
                dialogue_engine = "siliconflow"
        except ImportError:
            pass

        # 尝试 edge-tts 是否可用
        if dialogue_engine == "espeak-ng":
            try:
                import importlib
                importlib.util.find_spec("edge_tts")
                dialogue_engine = "edge-tts"
            except ImportError:
                pass

        # 获取当前风格对应的音色映射
        voice_map = self._DIALOGUE_VOICES.get(dialogue_engine, {}).get(
            self.style, self._DIALOGUE_VOICES.get(dialogue_engine, {}).get("dialogue", {})
        )
        if not voice_map:
            # espeak-ng 回退：单人模式，不区分音色
            voice_map = {"A": DEFAULT_VOICE.get(dialogue_engine, {}).get(self.language, "cmn"),
                         "B": DEFAULT_VOICE.get(dialogue_engine, {}).get(self.language, "cmn")}

        logger.debug(
            "检测到双人对话（%s 段），引擎=%s，A=%s, B=%s",
            len(segments), dialogue_engine,
            voice_map.get('A', '?'), voice_map.get('B', '?'),
        )

        # 逐段合成
        temp_files: list[str] = []
        original_voice = self.voice
        original_engine = self.engine

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(description="双人对话合成中...", total=len(segments))
            for i, (speaker, content) in enumerate(segments):
                temp_path = output_path.replace(".mp3", f"_seg{i}_{speaker}.mp3")
                self.voice = voice_map.get(speaker, voice_map.get("A"))
                progress.update(
                    task, advance=1,
                    description=f"[{i+1}/{len(segments)}] {speaker}: {content[:30]}..."
                )
                # 按注册表优先级尝试引擎，失败时逐级回退
                synthesized = False
                for eng_name, backend_cls in get_tts_engines_sorted_by_priority():
                    if eng_name == "siliconflow" and dialogue_engine != "siliconflow":
                        continue
                    if backend_cls is None:
                        continue
                    try:
                        backend = backend_cls(self)
                        backend.synthesize(content, temp_path)
                        synthesized = True
                        break
                    except (TTSError, OSError, RuntimeError, ImportError) as e:
                        logger.warning("%s 引擎不可用: %s", eng_name, e, exc_info=True)
                if not synthesized:
                    raise TTSError(f"第 {i+1} 段音频合成失败：所有引擎均不可用")
                temp_files.append(temp_path)

        self.voice = original_voice
        self.engine = original_engine

        # 拼接所有片段
        self._concat_audio(temp_files, output_path)
        for f in temp_files:
            try:
                os.remove(f)
            except OSError:
                pass

        file_size = os.path.getsize(output_path)
        logger.info(
            "✓ 双人对话合成完成: %s (%.1f KB, %s 段, 引擎=%s)",
            output_path, file_size / 1024, len(segments), dialogue_engine,
        )
        self._active_engine = f"{dialogue_engine}-dialogue"
        return output_path

    # ------------------------------------------------------------------
    # 硅基流动 TTS 引擎（最高优先级，高质量神经网络语音）
    # ------------------------------------------------------------------

    def _synthesize_siliconflow(self, text: str, output_path: str) -> str:
        """使用硅基流动 CosyVoice2 合成语音（HTTP 协议，高质量）"""
        from .config import TTS_API_KEY, TTS_BASE_URL, TTS_MODEL
        from openai import OpenAI

        if not TTS_API_KEY:
            raise TTSError("硅基流动 TTS 需要配置 TTS_API_KEY")

        voice = self.voice or DEFAULT_VOICE["siliconflow"].get(
            self.language, DEFAULT_VOICE["siliconflow"]["zh"]
        )
        speed = self._parse_rate_to_float()
        client = OpenAI(api_key=TTS_API_KEY, base_url=TTS_BASE_URL)

        def _synth_chunk(chunk: str, out_path: str) -> None:
            with client.audio.speech.with_streaming_response.create(
                model=TTS_MODEL,
                voice=voice,
                input=chunk,
                response_format="mp3",
                speed=speed,
            ) as response:
                response.stream_to_file(out_path)

        voice_label = voice.split(":")[-1] if ":" in voice else voice
        return self._run_chunked_synthesis(
            text, output_path, 500, _synth_chunk, f"硅基流动 TTS（{voice_label}）"
        )

    # ------------------------------------------------------------------
    # edge-tts 引擎
    # ------------------------------------------------------------------

    def _synthesize_edge(self, text: str, output_path: str) -> str:
        """使用 edge-tts 合成语音"""
        import edge_tts

        voice = self.voice or DEFAULT_VOICE["edge-tts"].get(
            self.language, DEFAULT_VOICE["edge-tts"]["zh"]
        )
        rate = self.rate if self.rate != "+0%" else "+0%"

        def _synth_chunk(chunk: str, out_path: str) -> None:
            communicate = edge_tts.Communicate(
                text=chunk, voice=voice, rate=rate, volume=self.volume
            )
            asyncio.run(communicate.save(out_path))

        return self._run_chunked_synthesis(text, output_path, 3000, _synth_chunk, "edge-tts")

    # ------------------------------------------------------------------
    # espeak-ng 引擎（离线回退）
    # ------------------------------------------------------------------

    def _synthesize_espeak(self, text: str, output_path: str) -> str:
        """使用 espeak-ng 合成语音（离线，无需联网）"""
        # 检查 espeak-ng 是否可用
        if not shutil.which("espeak-ng"):
            raise TTSError(
                "espeak-ng 未安装。请运行: apt-get install espeak-ng"
            )

        voice = self.voice or DEFAULT_VOICE["espeak-ng"].get(
            self.language, DEFAULT_VOICE["espeak-ng"]["zh"]
        )

        # 解析语速
        # 中文语音需要更慢的默认语速才能听清
        if self.language == "zh":
            default_speed = 140  # 中文默认更慢
        else:
            default_speed = 175  # 英文默认语速

        if self.rate.startswith("+"):
            pct = int(self.rate.strip("+%"))
            speed = int(default_speed * (1 + pct / 100))
        elif self.rate.startswith("-"):
            pct = int(self.rate.strip("-%"))
            speed = int(default_speed * (1 - pct / 100))
        else:
            speed = default_speed

        # 中文语音不要超过 180，否则听不清
        if self.language == "zh":
            speed = min(speed, 180)

        # espeak-ng 输出 WAV，需要用 ffmpeg 转 MP3
        has_ffmpeg = shutil.which("ffmpeg") is not None

        chunks = self._split_text(text, max_chars=2000)

        logger.debug(
            "espeak-ng 合成中（语音: %s, 语速: %s）...",
            voice, speed,
        )

        if len(chunks) == 1:
            temp_wav = output_path.replace(".mp3", "_tmp.wav")
            self._espeak_to_file(chunks[0], voice, speed, temp_wav)

            if has_ffmpeg:
                self._wav_to_mp3(temp_wav, output_path)
                os.remove(temp_wav)
            else:
                os.rename(temp_wav, output_path.replace(".mp3", ".wav"))
                output_path = output_path.replace(".mp3", ".wav")
        else:
            # 分段合成
            logger.debug("文本较长（%s 字），分 %s 段合成", len(text), len(chunks))
            temp_wavs: list[str] = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(description="espeak-ng 分段合成...", total=len(chunks))
                for i, chunk in enumerate(chunks):
                    temp_wav = output_path.replace(".mp3", f"_part{i}.wav")
                    self._espeak_to_file(chunk, voice, speed, temp_wav)
                    temp_wavs.append(temp_wav)
                    progress.update(task, advance=1, description=f"已合成 {i+1}/{len(chunks)} 段")

            # 用 ffmpeg concat demuxer 合并所有 WAV 为最终 MP3
            if has_ffmpeg:
                # 创建 concat 列表文件
                list_file = output_path.replace(".mp3", "_concat_list.txt")
                with open(list_file, "w") as f:
                    for wav in temp_wavs:
                        f.write(f"file '{os.path.abspath(wav)}'\n")

                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-codec:a", "libmp3lame",
                    "-b:a", "128k",
                    output_path,
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=TTS_SYNTHESIS_TIMEOUT)

                # 清理
                os.remove(list_file)
                for f in temp_wavs:
                    try:
                        os.remove(f)
                    except OSError:
                        pass

                if result.returncode != 0:
                    # ffmpeg concat 失败，退化到二进制拼接 WAV
                    combined_wav = output_path.replace(".mp3", "_combined.wav")
                    with open(combined_wav, "wb") as out_f:
                        for wav in temp_wavs:
                            with open(wav, "rb") as in_f:
                                out_f.write(in_f.read())
                    self._wav_to_mp3(combined_wav, output_path)
                    os.remove(combined_wav)
            else:
                # 无 ffmpeg，直接二进制拼接 WAV
                combined_wav = output_path.replace(".mp3", ".wav")
                with open(combined_wav, "wb") as out_f:
                    for wav in temp_wavs:
                        with open(wav, "rb") as in_f:
                            out_f.write(in_f.read())
                for f in temp_wavs:
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                output_path = combined_wav

        file_size = os.path.getsize(output_path)
        logger.info(
            "✓ espeak-ng 合成完成: %s (%.1f KB)",
            output_path, file_size / 1024,
        )
        return output_path

    def _espeak_to_file(self, text: str, voice: str, speed: int, output_wav: str):
        """用 espeak-ng 将文本转为 WAV 文件"""
        # 将文本写入临时文件（避免命令行长度限制和特殊字符问题）
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        try:
            cmd = [
                "espeak-ng",
                "-v", voice,
                "-s", str(speed),
                "-f", tmp_path,
                "-w", output_wav,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=TTS_FALLBACK_TIMEOUT)
            if result.returncode != 0:
                raise TTSError(
                    f"espeak-ng 失败: {result.stderr.decode('utf-8', errors='replace')}"
                )
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _wav_to_mp3(wav_path: str, mp3_path: str):
        """用 ffmpeg 将 WAV 转为 MP3"""
        cmd = [
            "ffmpeg", "-y",
            "-i", wav_path,
            "-codec:a", "libmp3lame",
            "-b:a", "128k",
            mp3_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=TTS_SYNTHESIS_TIMEOUT)
        if result.returncode != 0:
            # 如果 ffmpeg 转码失败，直接复制 WAV
            shutil.copy(wav_path, mp3_path)

    @staticmethod
    def _concat_wav(wav_files: list[str], output: str):
        """拼接多个 WAV 文件"""
        # 使用 ffmpeg 拼接
        if shutil.which("ffmpeg"):
            concat_input = "|".join(wav_files)
            cmd = [
                "ffmpeg", "-y",
                "-i", f"concat:{concat_input}",
                "-codec:a", "libmp3lame",
                "-b:a", "128k",
                output.replace(".wav", ".mp3"),
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=TTS_SYNTHESIS_TIMEOUT)
            if result.returncode == 0:
                return

        # 退化：二进制拼接
        with open(output, "wb") as out_f:
            for f in wav_files:
                with open(f, "rb") as in_f:
                    out_f.write(in_f.read())

    # ------------------------------------------------------------------
    # 通用工具方法
    # ------------------------------------------------------------------

    def _parse_rate_to_float(self) -> float:
        """将语速字符串（如 ``+10%``）解析为浮点倍率（如 ``1.1``）。

        适用于 siliconflow 等需要浮点倍率的引擎。
        """
        if self.rate.startswith("+"):
            pct = int(self.rate.strip("+%"))
            return 1.0 + pct / 100
        elif self.rate.startswith("-"):
            pct = int(self.rate.strip("-%"))
            return 1.0 - pct / 100
        return 1.0

    def _run_chunked_synthesis(
        self,
        text: str,
        output_path: str,
        max_chars: int,
        synth_func: Callable[[str, str], None],
        engine_label: str,
    ) -> str:
        """通用分段合成 + 拼接 + 清理模板（模板方法模式）。

        适用于输出 MP3 的引擎（siliconflow、edge-tts）。
        espeak-ng 因输出 WAV 且转码逻辑不同，不使用此模板。

        Args:
            text:         要合成的完整文本
            output_path:  最终输出 MP3 路径
            max_chars:    单段最大字数
            synth_func:   单段合成回调 ``(chunk_text, output_file) -> None``
            engine_label: 引擎标签（用于进度条和成功日志）

        Returns:
            输出文件路径
        """
        chunks = self._split_text(text, max_chars=max_chars)

        if len(chunks) == 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description=f"{engine_label} 合成中...", total=None)
                synth_func(chunks[0], output_path)
        else:
            logger.debug("文本较长（%s 字），分 %s 段合成", len(text), len(chunks))
            temp_files: list[str] = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    description=f"{engine_label} 分段合成...", total=len(chunks)
                )
                for i, chunk in enumerate(chunks):
                    temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
                    synth_func(chunk, temp_path)
                    temp_files.append(temp_path)
                    progress.update(
                        task, advance=1,
                        description=f"已合成 {i+1}/{len(chunks)} 段",
                    )

            self._concat_audio(temp_files, output_path)
            for f in temp_files:
                try:
                    os.remove(f)
                except OSError:
                    pass

        file_size = os.path.getsize(output_path)
        logger.info(
            "✓ %s 合成完成: %s (%.1f KB)",
            engine_label, output_path, file_size / 1024,
        )
        return output_path

    @staticmethod
    def _split_text(text: str, max_chars: int = 3000) -> list[str]:
        """将长文本按句子边界分段"""
        if len(text) <= max_chars:
            return [text]

        import re

        sentences = re.split(r"(?<=[。．！？\n.!?])\s*", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) > max_chars and current:
                chunks.append(current)
                current = sentence
            else:
                current += " " + sentence if current else sentence

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def _concat_audio(files: list[str], output: str):
        """拼接多个 MP3 文件，使用 pydub 实现交叉淡入淡出。

        退化策略：pydub 不可用时回退到二进制拼接。
        """
        if not files:
            return
        try:
            from pydub import AudioSegment

            # 加载第一段
            combined = AudioSegment.from_mp3(files[0])
            # 逐段拼接，100ms 交叉淡入淡出避免爆音
            for f in files[1:]:
                segment = AudioSegment.from_mp3(f)
                # 确保两段有足够的重叠用于 crossfade
                overlap = min(100, len(combined), len(segment))
                if overlap > 0:
                    combined = combined.append(segment, crossfade=overlap)
                else:
                    combined += segment
            # 段间插入 300ms 静音（自然停顿）
            combined.export(output, format="mp3")
        except ImportError:
            # pydub 未安装，退化到二进制拼接
            with open(output, "wb") as out_f:
                for f in files:
                    with open(f, "rb") as in_f:
                        out_f.write(in_f.read())
        except Exception:
            # pydub/ffmpeg 异常时退化到二进制拼接
            logger.debug("pydub/ffmpeg 拼接失败，退化到二进制拼接", exc_info=True)
            with open(output, "wb") as out_f:
                for f in files:
                    with open(f, "rb") as in_f:
                        out_f.write(in_f.read())

    # ------------------------------------------------------------------
    # 信息方法
    # ------------------------------------------------------------------

    @property
    def active_engine(self) -> str:
        """返回实际使用的引擎名称"""
        return self._active_engine or "unknown"

    def list_available_voices(self) -> dict:
        """返回预设语音列表"""
        return VOICES

    @staticmethod
    def check_engines() -> dict:
        """检查各引擎的可用性（通过注册表发现 + 补充详细信息）"""
        status: dict[str, dict] = {}

        # 通过注册表发现所有已注册引擎
        for eng_name in list_tts_engines():
            backend_cls = get_tts_engine(eng_name)
            if backend_cls is None:
                continue

            if eng_name == "siliconflow":
                try:
                    from .config import TTS_API_KEY, TTS_MODEL
                    status["siliconflow"] = {
                        "available": bool(TTS_API_KEY),
                        "note": f"CosyVoice2 神经网络语音（{TTS_MODEL}）",
                    }
                except ImportError:
                    status["siliconflow"] = {"available": False, "note": "config.py 未配置"}
            elif eng_name == "edge-tts":
                try:
                    import importlib
                    importlib.util.find_spec("edge_tts")
                    status["edge-tts"] = {"available": True, "note": "需联网（WebSocket）"}
                except ImportError:
                    status["edge-tts"] = {"available": False, "note": "未安装: pip install edge-tts"}
            elif eng_name == "espeak-ng":
                if shutil.which("espeak-ng"):
                    status["espeak-ng"] = {"available": True, "note": "离线可用（质量较低）"}
                else:
                    status["espeak-ng"] = {
                        "available": False,
                        "note": "未安装: apt-get install espeak-ng",
                    }
            else:
                # 第三方注册的引擎：使用 is_available() + 引擎名
                status[eng_name] = {
                    "available": backend_cls.is_available(),
                    "note": eng_name,
                }

        # ffmpeg（辅助工具，非 TTS 引擎）
        status["ffmpeg"] = {
            "available": shutil.which("ffmpeg") is not None,
            "note": "音频处理" if shutil.which("ffmpeg") else "未安装",
        }

        return status


# ═══════════════════════════════════════════════════════════════════
# TTSBackend 适配器（阶段4: 激活注册机制）
#
# 三个内置引擎通过 TTSBackend 接口注册到 registry，
# TTSEngine.text_to_speech 通过注册表发现引擎，不再依赖 if/elif 链。
# 新增引擎只需实现 TTSBackend + @register_tts_engine 注册。
# ═══════════════════════════════════════════════════════════════════


@register_tts_engine("siliconflow", priority=100)
class _SiliconFlowBackend(TTSBackend):
    """硅基流动 CosyVoice2 引擎适配器。"""

    def __init__(self, engine: TTSEngine):
        self._engine = engine

    @property
    def name(self) -> str:
        return "siliconflow"

    @property
    def requires_network(self) -> bool:
        return True

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
        if voice:
            self._engine.voice = voice
        return self._engine._synthesize_siliconflow(text, output_path)

    @staticmethod
    def is_available() -> bool:
        try:
            from .config import TTS_API_KEY
            return bool(TTS_API_KEY)
        except ImportError:
            return False


@register_tts_engine("edge-tts", priority=50)
class _EdgeTTSBackend(TTSBackend):
    """edge-tts 引擎适配器。"""

    def __init__(self, engine: TTSEngine):
        self._engine = engine

    @property
    def name(self) -> str:
        return "edge-tts"

    @property
    def requires_network(self) -> bool:
        return True

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
        if voice:
            self._engine.voice = voice
        return self._engine._synthesize_edge(text, output_path)

    @staticmethod
    def is_available() -> bool:
        try:
            import importlib
            importlib.util.find_spec("edge_tts")
            return True
        except ImportError:
            return False


@register_tts_engine("espeak-ng", priority=10)
class _EspeakBackend(TTSBackend):
    """espeak-ng 离线引擎适配器。"""

    def __init__(self, engine: TTSEngine):
        self._engine = engine

    @property
    def name(self) -> str:
        return "espeak-ng"

    @property
    def requires_network(self) -> bool:
        return False

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
        if voice:
            self._engine.voice = voice
        return self._engine._synthesize_espeak(text, output_path)

    @staticmethod
    def is_available() -> bool:
        return shutil.which("espeak-ng") is not None

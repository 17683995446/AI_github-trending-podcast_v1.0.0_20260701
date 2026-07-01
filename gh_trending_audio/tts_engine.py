"""
tts_engine.py —— 多引擎文本转语音（TTS）

引擎优先级（自动回退）：
  1. edge-tts   —— 微软 Edge 在线 TTS，高质量神经网络语音（需联网 WebSocket）
  2. espeak-ng  —— 离线 TTS 引擎，系统级安装，无需联网（质量较低但稳定）

引擎选择逻辑：
  - 默认尝试 edge-tts，失败后自动回退到 espeak-ng
  - 也可通过 engine 参数强制指定

成本对比：
  - edge-tts：免费（云服务，高质量，需联网）
  - espeak-ng：免费（本地，离线，质量较低）
  - 商业 TTS（Azure/ElevenLabs）：按字符收费
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

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

        # 单人模式
        if self.engine == "espeak-ng":
            return self._synthesize_espeak(text, output_path)
        elif self.engine == "edge-tts":
            return self._synthesize_edge(text, output_path)
        elif self.engine == "siliconflow":
            return self._synthesize_siliconflow(text, output_path)
        else:
            engines_to_try = [
                ("siliconflow", self._synthesize_siliconflow),
                ("edge-tts", self._synthesize_edge),
                ("espeak-ng", self._synthesize_espeak),
            ]
            for eng_name, eng_func in engines_to_try:
                try:
                    console.print(f"[dim]尝试 {eng_name} 引擎...[/dim]")
                    result = eng_func(text, output_path)
                    self._active_engine = eng_name
                    return result
                except Exception as e:
                    console.print(f"[yellow]⚠ {eng_name} 不可用: {e}[/yellow]")
            raise RuntimeError("所有 TTS 引擎均不可用")

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

    def _synthesize_dialogue(
        self, segments: list[tuple[str, str]], output_path: str
    ) -> str:
        """
        合成双人对话音频：A 和 B 分别用不同音色合成，最后拼接。

        音色根据播客风格自动分配（硅基流动 CosyVoice2）：
            dialogue/interview: A=david(欢快男), B=claire(温柔女)
            debate:             A=david(激昂男), B=alex(沉稳男) — 同性辩论更自然
            news:               A=benjamin(新闻男), B=claire(沉稳女)
            story:              A=benjamin(沉稳旁白), B=david(活泼主角)
        """
        # 风格 -> 音色映射
        style_voices = {
            "dialogue": {
                "A": "FunAudioLLM/CosyVoice2-0.5B:david",
                "B": "FunAudioLLM/CosyVoice2-0.5B:claire",
            },
            "debate": {
                "A": "FunAudioLLM/CosyVoice2-0.5B:david",    # 支持方：激昂
                "B": "FunAudioLLM/CosyVoice2-0.5B:alex",     # 质疑方：沉稳
            },
            "interview": {
                "A": "FunAudioLLM/CosyVoice2-0.5B:david",    # 记者：欢快
                "B": "FunAudioLLM/CosyVoice2-0.5B:claire",   # 作者：温柔
            },
            "news": {
                "A": "FunAudioLLM/CosyVoice2-0.5B:benjamin",  # 主播甲：正式
                "B": "FunAudioLLM/CosyVoice2-0.5B:claire",   # 主播乙：沉稳
            },
            "story": {
                "A": "FunAudioLLM/CosyVoice2-0.5B:benjamin",  # 旁白：沉稳
                "B": "FunAudioLLM/CosyVoice2-0.5B:david",    # 主角：活泼
            },
        }

        voice_map = style_voices.get(self.style, style_voices["dialogue"])

        console.print(
            f"[dim]检测到双人对话（{len(segments)} 段），"
            f"A={voice_map['A'].split(':')[-1]}, B={voice_map['B'].split(':')[-1]}[/dim]"
        )

        # 逐段合成
        temp_files: list[str] = []
        original_voice = self.voice

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(description="双人对话合成中...", total=len(segments))
            for i, (speaker, content) in enumerate(segments):
                temp_path = output_path.replace(".mp3", f"_seg{i}_{speaker}.mp3")
                self.voice = voice_map.get(speaker, voice_map["A"])
                progress.update(
                    task, advance=1,
                    description=f"[{i+1}/{len(segments)}] {speaker}: {content[:30]}..."
                )
                # 使用硅基流动合成（双人模式强制使用）
                try:
                    self._synthesize_siliconflow(content, temp_path)
                except Exception:
                    # 回退到 espeak-ng
                    self._synthesize_espeak(content, temp_path)
                temp_files.append(temp_path)

        self.voice = original_voice

        # 拼接所有片段
        self._concat_audio(temp_files, output_path)
        for f in temp_files:
            try:
                os.remove(f)
            except OSError:
                pass

        file_size = os.path.getsize(output_path)
        console.print(
            f"[green]✓ 双人对话合成完成: {output_path}[/green] "
            f"[dim]({file_size / 1024:.1f} KB, {len(segments)} 段)[/dim]"
        )
        self._active_engine = "siliconflow-dialogue"
        return output_path

    # ------------------------------------------------------------------
    # 硅基流动 TTS 引擎（最高优先级，高质量神经网络语音）
    # ------------------------------------------------------------------

    def _synthesize_siliconflow(self, text: str, output_path: str) -> str:
        """使用硅基流动 CosyVoice2 合成语音（HTTP 协议，高质量）"""
        from .config import TTS_API_KEY, TTS_BASE_URL, TTS_MODEL
        from openai import OpenAI

        if not TTS_API_KEY:
            raise RuntimeError("硅基流动 TTS 需要配置 TTS_API_KEY")

        # 选择音色
        voice = self.voice or DEFAULT_VOICE["siliconflow"].get(
            self.language, DEFAULT_VOICE["siliconflow"]["zh"]
        )

        # 解析语速："+10%" -> 1.1
        if self.rate.startswith("+"):
            pct = int(self.rate.strip("+%"))
            speed = 1.0 + pct / 100
        elif self.rate.startswith("-"):
            pct = int(self.rate.strip("-%"))
            speed = 1.0 - pct / 100
        else:
            speed = 1.0

        # 分段处理（CosyVoice2 建议单次不超过 500 字）
        chunks = self._split_text(text, max_chars=500)

        client = OpenAI(api_key=TTS_API_KEY, base_url=TTS_BASE_URL)

        if len(chunks) == 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description=f"硅基流动 TTS 合成中（{voice.split(':')[-1]}）...", total=None)
                with client.audio.speech.with_streaming_response.create(
                    model=TTS_MODEL,
                    voice=voice,
                    input=chunks[0],
                    response_format="mp3",
                    speed=speed,
                ) as response:
                    response.stream_to_file(output_path)
        else:
            console.print(f"[dim]文本较长（{len(text)} 字），分 {len(chunks)} 段合成[/dim]")
            temp_files: list[str] = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(description="硅基流动分段合成...", total=len(chunks))
                for i, chunk in enumerate(chunks):
                    temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
                    with client.audio.speech.with_streaming_response.create(
                        model=TTS_MODEL,
                        voice=voice,
                        input=chunk,
                        response_format="mp3",
                        speed=speed,
                    ) as response:
                        response.stream_to_file(temp_path)
                    temp_files.append(temp_path)
                    progress.update(task, advance=1, description=f"已合成 {i+1}/{len(chunks)} 段")

            # 拼接 MP3
            self._concat_audio(temp_files, output_path)
            for f in temp_files:
                try:
                    os.remove(f)
                except OSError:
                    pass

        file_size = os.path.getsize(output_path)
        console.print(
            f"[green]✓ 硅基流动 TTS 合成完成: {output_path}[/green] "
            f"[dim]({file_size / 1024:.1f} KB)[/dim]"
        )
        return output_path

    # ------------------------------------------------------------------
    # edge-tts 引擎
    # ------------------------------------------------------------------

    def _synthesize_edge(self, text: str, output_path: str) -> str:
        """使用 edge-tts 合成语音"""
        import edge_tts

        voice = self.voice or DEFAULT_VOICE["edge-tts"].get(
            self.language, DEFAULT_VOICE["edge-tts"]["zh"]
        )

        # 解析语速："+10%" -> "+10%"
        rate = self.rate if self.rate != "+0%" else "+0%"

        chunks = self._split_text(text, max_chars=3000)

        async def synth_chunk(chunk: str, out_path: str):
            communicate = edge_tts.Communicate(
                text=chunk, voice=voice, rate=rate, volume=self.volume
            )
            await communicate.save(out_path)

        if len(chunks) == 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task(description="edge-tts 合成中...", total=None)
                asyncio.run(synth_chunk(chunks[0], output_path))
        else:
            console.print(f"[dim]文本较长（{len(text)} 字），分 {len(chunks)} 段合成[/dim]")
            temp_files: list[str] = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(description="edge-tts 分段合成...", total=len(chunks))
                for i, chunk in enumerate(chunks):
                    temp_path = output_path.replace(".mp3", f"_part{i}.mp3")
                    asyncio.run(synth_chunk(chunk, temp_path))
                    temp_files.append(temp_path)
                    progress.update(task, advance=1, description=f"已合成 {i+1}/{len(chunks)} 段")

            self._concat_audio(temp_files, output_path)
            for f in temp_files:
                try:
                    os.remove(f)
                except OSError:
                    pass

        file_size = os.path.getsize(output_path)
        console.print(
            f"[green]✓ edge-tts 合成完成: {output_path}[/green] "
            f"[dim]({file_size / 1024:.1f} KB)[/dim]"
        )
        return output_path

    # ------------------------------------------------------------------
    # espeak-ng 引擎（离线回退）
    # ------------------------------------------------------------------

    def _synthesize_espeak(self, text: str, output_path: str) -> str:
        """使用 espeak-ng 合成语音（离线，无需联网）"""
        # 检查 espeak-ng 是否可用
        if not shutil.which("espeak-ng"):
            raise RuntimeError(
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
        final_ext = ".mp3" if has_ffmpeg else ".wav"

        chunks = self._split_text(text, max_chars=2000)

        console.print(
            f"[dim]espeak-ng 合成中（语音: {voice}, 语速: {speed}）...[/dim]"
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
            console.print(f"[dim]文本较长（{len(text)} 字），分 {len(chunks)} 段合成[/dim]")
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
                result = subprocess.run(cmd, capture_output=True, timeout=120)

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
        console.print(
            f"[green]✓ espeak-ng 合成完成: {output_path}[/green] "
            f"[dim]({file_size / 1024:.1f} KB)[/dim]"
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
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(
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
        result = subprocess.run(cmd, capture_output=True, timeout=120)
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
            result = subprocess.run(cmd, capture_output=True, timeout=120)
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
        """检查各引擎的可用性"""
        status = {}

        # 硅基流动 TTS
        try:
            from .config import TTS_API_KEY, TTS_MODEL
            status["siliconflow"] = {
                "available": bool(TTS_API_KEY),
                "note": f"CosyVoice2 神经网络语音（{TTS_MODEL}）",
            }
        except ImportError:
            status["siliconflow"] = {"available": False, "note": "config.py 未配置"}

        # edge-tts
        try:
            import edge_tts
            status["edge-tts"] = {"available": True, "note": "需联网（WebSocket）"}
        except ImportError:
            status["edge-tts"] = {"available": False, "note": "未安装: pip install edge-tts"}

        # espeak-ng
        if shutil.which("espeak-ng"):
            status["espeak-ng"] = {"available": True, "note": "离线可用（质量较低）"}
        else:
            status["espeak-ng"] = {
                "available": False,
                "note": "未安装: apt-get install espeak-ng",
            }

        # ffmpeg
        status["ffmpeg"] = {
            "available": shutil.which("ffmpeg") is not None,
            "note": "音频处理" if shutil.which("ffmpeg") else "未安装",
        }

        return status

"""
config.py —— 集中配置管理

所有配置优先从环境变量读取，环境变量未设置时使用此处的默认值。
修改默认值后无需再手动设置环境变量。
"""

import os

# ── LLM 配置（硅基流动 SiliconFlow）──────────────────────────────
# 硅基流动提供 9B 以下模型永久免费：https://siliconflow.cn
# 以下 API Key 为演示用，请替换为您自己的 Key
LLM_API_KEY = os.environ.get(
    "LLM_API_KEY",
    "sk-uqelhavcdhfxjzjesdenxpbtqombamjniazzjtbssmdcwdvg"
)
LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL",
    "https://api.siliconflow.cn/v1"
)

# 免费模型列表（9B 以下永久免费）：
#   - THUDM/GLM-4-9B-0414           （智谱 GLM-4，中文优秀，推荐）
#   - Qwen/Qwen2.5-7B-Instruct      （通义千问，中文不错）
#   - 01-ai/Yi-1.5-9B-Chat-16K      （零一万物）
LLM_MODEL = os.environ.get(
    "LLM_MODEL",
    "THUDM/GLM-4-9B-0414"
)

# ── GitHub 配置 ──────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ── TTS 配置 ─────────────────────────────────────────────────────
# 引擎优先级（auto 模式下依次尝试）：
#   1. siliconflow  —— 硅基流动 CosyVoice2（高质量神经网络，HTTP 协议）
#   2. edge-tts     —— 微软 Edge TTS（高质量，需 WebSocket）
#   3. espeak-ng    —— 离线合成（质量低，无需联网）
TTS_ENGINE = os.environ.get("TTS_ENGINE", "auto")
TTS_RATE = os.environ.get("TTS_RATE", "+0%")

# 硅基流动 TTS 配置（复用 LLM_API_KEY）
TTS_API_KEY = os.environ.get("TTS_API_KEY", LLM_API_KEY)
TTS_BASE_URL = os.environ.get("TTS_BASE_URL", LLM_BASE_URL)
TTS_MODEL = os.environ.get("TTS_MODEL", "FunAudioLLM/CosyVoice2-0.5B")

# 硅基流动预置音色
# 男生: alex(沉稳) benjamin(低沉) charles(磁性) david(欢快)
# 女生: anna(沉稳) bella(激情)  claire(温柔) diana(欢快)
TTS_VOICE_ZH = os.environ.get("TTS_VOICE_ZH", "FunAudioLLM/CosyVoice2-0.5B:alex")
TTS_VOICE_EN = os.environ.get("TTS_VOICE_EN", "FunAudioLLM/CosyVoice2-0.5B:alex")

#!/usr/bin/env python3
"""
GitHub Trending Audio —— 入口文件

自动获取 GitHub 最新高价值项目 -> 生成通俗易懂的音频文档 -> 合成 MP3 语音

快速开始:
    pip install -r requirements.txt
    python main.py --days 7 --limit 3

可选环境变量:
    GITHUB_TOKEN   GitHub Token（提高 API 配额，可选）
    LLM_API_KEY    LLM API 密钥（启用 --use-llm 时需要）
    LLM_BASE_URL   LLM API 地址（默认 OpenAI）
    LLM_MODEL      LLM 模型名（默认 gpt-4o-mini）
"""

from gh_trending_audio.cli import main

if __name__ == "__main__":
    main()

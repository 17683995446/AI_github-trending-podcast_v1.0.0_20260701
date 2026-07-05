#!/usr/bin/env python3
"""
GitHub Trending Audio —— 入口文件

自动获取 GitHub 最新高价值项目 -> 生成通俗易懂的音频文档 -> 合成 MP3 语音

快速开始:
    pip install -r requirements.txt
    python main.py quick            # 零配置快速体验（3个Python项目，中文音频）
    python main.py --days 7 --limit 3  # 完整参数模式

可选环境变量:
    GITHUB_TOKEN   GitHub Token（提高 API 配额，可选）
    LLM_API_KEY    LLM API 密钥（启用 --use-llm 或 podcast 子命令时需要）
    LLM_BASE_URL   LLM API 地址（默认硅基流动 https://api.siliconflow.cn/v1）
    LLM_MODEL      LLM 模型名（默认 THUDM/GLM-4-9B-0414，9B 以下永久免费）
"""

from gh_trending_audio.cli import main

if __name__ == "__main__":
    main()

"""
GitHub Trending Audio —— 自动获取 GitHub 高价值项目并转化为音频文档

站在巨人的肩膀上：
  - 数据源：GitHub 官方 Search API（免费、稳定）
  - 语音合成：edge-tts（微软 Edge 在线 TTS，零成本、高质量）
  - 可选增强：LLM 生成更生动的播客式脚本（需自备 API Key）

公共 API::

    from gh_trending_audio import GitHubFetcher, TTSEngine, DocumentGenerator
    from gh_trending_audio import RepoInfo, AudioDocument
    from gh_trending_audio import AppConfig, get_config
"""

__version__ = "1.0.0"
__author__ = "gh-trending-audio"

# ── 延迟导出公共 API（避免导入时副作用）──────────────────────────────

_LAZY_EXPORTS = {
    "GitHubFetcher": "gh_trending_audio.github_fetcher",
    "RepoInfo": "gh_trending_audio.github_fetcher",
    "DocumentGenerator": "gh_trending_audio.document_generator",
    "AudioDocument": "gh_trending_audio.models",
    "TTSEngine": "gh_trending_audio.tts_engine",
    "VOICES": "gh_trending_audio.tts_engine",
    "LLMEnhancer": "gh_trending_audio.llm_enhancer",
    "AppConfig": "gh_trending_audio.config",
    "LLMConfig": "gh_trending_audio.config",
    "TTSConfig": "gh_trending_audio.config",
    "GitHubConfig": "gh_trending_audio.config",
    "get_config": "gh_trending_audio.config",
    "load_config": "gh_trending_audio.config",
    "GhTrendingError": "gh_trending_audio.exceptions",
    "GitHubAPIError": "gh_trending_audio.exceptions",
    "TTSError": "gh_trending_audio.exceptions",
    "LLMError": "gh_trending_audio.exceptions",
    # 注册机制（阶段4: 可扩展架构）
    "TTSBackend": "gh_trending_audio.registry",
    "register_tts_engine": "gh_trending_audio.registry",
    "register_style": "gh_trending_audio.registry",
    "get_tts_engine": "gh_trending_audio.registry",
    "list_tts_engines": "gh_trending_audio.registry",
    "LLMBackend": "gh_trending_audio.registry",
    "register_llm_backend": "gh_trending_audio.registry",
    "get_llm_backend": "gh_trending_audio.registry",
    "list_llm_backends": "gh_trending_audio.registry",
    "get_auto_llm_backend": "gh_trending_audio.registry",
    "PodcastStyle": "gh_trending_audio.registry",
    "SpeakerRole": "gh_trending_audio.registry",
    # 播客订阅源（阶段6: RSS + OPML）
    "generate_podcast_feed": "gh_trending_audio.podcast_feed",
    "generate_opml": "gh_trending_audio.podcast_feed",
    "get_feed_stats": "gh_trending_audio.podcast_feed",
    # 字幕生成（阶段7: SRT/VTT 无障碍访问）
    "generate_srt": "gh_trending_audio.subtitle_gen",
    "generate_vtt": "gh_trending_audio.subtitle_gen",
    "parse_dialogue": "gh_trending_audio.subtitle_gen",
    # 多格式导出（阶段9: PDF/EPUB/JSON/ZIP）
    "export_project": "gh_trending_audio.exporter",
    "export_json": "gh_trending_audio.exporter",
    "export_zip": "gh_trending_audio.exporter",
    "export_pdf": "gh_trending_audio.exporter",
    "export_epub": "gh_trending_audio.exporter",
    # 本地后端检测（阶段10: Ollama + Piper）
    "detect_ollama": "gh_trending_audio.local_backends",
    "detect_piper": "gh_trending_audio.local_backends",
    "get_system_backends": "gh_trending_audio.local_backends",
    # 代码智能（阶段12: ripgrep + tree-sitter + Prism.js）
    "ripgrep_search": "gh_trending_audio.code_intel",
    "extract_symbols": "gh_trending_audio.code_intel",
    "detect_ripgrep": "gh_trending_audio.code_intel",
    "detect_tree_sitter": "gh_trending_audio.code_intel",
    # 全文搜索（阶段13: 倒排索引 + BM25）
    "build_index": "gh_trending_audio.search_engine",
    "search": "gh_trending_audio.search_engine",
    "get_search_suggestions": "gh_trending_audio.search_engine",
    # 项目对比（阶段14: 并排特性对比表）
    "compare_projects": "gh_trending_audio.comparison_engine",
    "generate_comparison_table": "gh_trending_audio.comparison_engine",
    "generate_radar_data": "gh_trending_audio.comparison_engine",
    # 用户偏好+收藏（阶段15-16）
    "get_preferences_schema": "gh_trending_audio.user_prefs",
    "merge_preferences": "gh_trending_audio.user_prefs",
    "toggle_favorite": "gh_trending_audio.user_prefs",
    "DEFAULT_PREFERENCES": "gh_trending_audio.user_prefs",
    # 核心层工具（阶段2: 从 web 上移）
    "scan_projects": "gh_trending_audio.project_scanner",
    "get_project_detail": "gh_trending_audio.project_scanner",
    "get_audio_duration": "gh_trending_audio.project_scanner",
    "parse_md_metadata": "gh_trending_audio.markdown_utils",
    "markdown_to_html": "gh_trending_audio.markdown_utils",
}


def __getattr__(name: str):
    """PEP 562 延迟导入：首次访问时才加载对应模块。"""
    if name in _LAZY_EXPORTS:
        import importlib

        module_path = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_path)
        attr = getattr(module, name)
        globals()[name] = attr  # 缓存到 globals 避免重复导入
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """列出所有可导出的名称。"""
    return list(_LAZY_EXPORTS.keys()) + ["__version__", "__author__"]

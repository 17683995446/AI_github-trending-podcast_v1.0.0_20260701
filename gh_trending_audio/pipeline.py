"""共享流水线编排（Phase 4: 解耦 CLI/Web 流水线重复）。

提取 fetch→enrich→generate→save→tts 流水线为单一入口，
CLI 和 Web handler 都委托给本模块，消除两套独立编排实现。

.. note::
    当前状态：本模块的 ``process_single_repo`` 提供了标准化的流水线编排接口，
    但 CLI（``cli._run_single_repo``）和 Web（``web/handlers/pipeline.start_pipeline``）
    仍各自内联实现了类似流程。后续迭代应让两方逐步委托本模块，
    消除重复的 fetch→enrich→generate→save→tts 编排逻辑。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from .exceptions import TTSError
from .github_fetcher import GitHubFetcher
from .models import RepoInfo
from .logging_config import get_logger
from .models import AudioDocument

logger = get_logger(__name__)


def process_single_repo(
    repo: RepoInfo,
    output_path: Path,
    *,
    language: str = "zh",
    use_llm: bool = False,
    style: str = "dialogue",
    generate_audio: bool = True,
    skip_if_exists: bool = True,
    output_dir: Path | None = None,
    on_progress: Callable[[str, str], None] | None = None,
) -> dict:
    """处理单个仓库的完整流水线：enrich→generate→save→tts。

    Args:
        repo: 仓库信息（需已 fetch 基本数据）。
        output_path: 输出目录。
        language: 输出语言 zh/en。
        use_llm: 是否使用 LLM 增强。
        style: 播客风格。
        generate_audio: 是否生成音频。
        skip_if_exists: 已存在时是否跳过。
        output_dir: 项目根目录（用于跨目录去重检查）。
        on_progress: 进度回调 (stage, message)。

    Returns:
        结果字典：{"repo": str, "doc": bool, "audio": bool, "skipped": bool, "error": str|None}
    """
    def _log(stage: str, msg: str) -> None:
        logger.debug("[%s] %s", stage, msg)
        if on_progress:
            on_progress(stage, msg)

    safe_name = repo.full_name.replace("/", "_")
    md_filename = f"{safe_name}.md"

    # 去重检查
    if skip_if_exists and output_dir:
        for d in output_dir.iterdir():
            if d.is_dir() and d.name.startswith("output"):
                if (d / md_filename).exists():
                    _log("skip", f"{repo.full_name} 已存在，跳过")
                    return {"repo": repo.full_name, "doc": False, "audio": False,
                            "skipped": True, "error": None}

    # 1. Enrich README
    # README 已由调用方获取（repo.readme_text），深度信息也由调用方通过
    # fetcher.enrich_with_details(repo) 填充，此处不再重复获取

    # 2. Generate document
    _log("generate", "生成播客文档...")
    from .document_generator import DocumentGenerator
    gen = DocumentGenerator(language=language, use_llm=use_llm, style=style)
    doc = gen.generate(repo)
    md_path = output_path / f"{safe_name}.md"
    script_path = output_path / f"{safe_name}_script.txt"
    doc.save(str(md_path), str(script_path))
    _log("generate", f"文档已保存: {md_path.name}")

    # 3. Generate audio
    audio_ok = False
    if generate_audio:
        _log("tts", "合成音频...")
        audio_path = output_path / f"{safe_name}.mp3"
        try:
            from .tts_engine import TTSEngine
            tts = TTSEngine(language=language, style=style)
            tts.text_to_speech(doc.audio_script, str(audio_path))
            audio_ok = True
            _log("tts", f"音频已保存: {audio_path.name}")
        except (TTSError, OSError) as e:
            logger.error("音频合成失败: %s", e, exc_info=True)
            _log("tts", f"音频合成失败: {e}")
            # 清理空文件
            if os.path.exists(str(audio_path)) and os.path.getsize(str(audio_path)) == 0:
                os.remove(str(audio_path))

    return {
        "repo": repo.full_name,
        "doc": True,
        "audio": audio_ok,
        "skipped": False,
        "error": None,
    }


def run_batch(
    repos: list[RepoInfo],
    output_path: Path,
    *,
    language: str = "zh",
    use_llm: bool = False,
    style: str = "dialogue",
    generate_audio: bool = True,
    skip_if_exists: bool = True,
    output_dir: Path | None = None,
    on_progress: Callable[[str, str], None] | None = None,
) -> list[dict]:
    """批量处理多个仓库。

    Args:
        repos: 仓库列表。
        output_path: 输出目录。
        language: 输出语言 zh/en。
        use_llm: 是否使用 LLM 增强。
        style: 播客风格。
        generate_audio: 是否生成音频。
        skip_if_exists: 已存在时是否跳过。
        output_dir: 项目根目录（用于跨目录去重检查）。
        on_progress: 进度回调 (stage, message)。

    Returns:
        每个仓库的处理结果列表。
    """
    results = []
    for i, repo in enumerate(repos, 1):
        logger.info("[%d/%d] %s", i, len(repos), repo.full_name)
        result = process_single_repo(
            repo, output_path,
            language=language, use_llm=use_llm, style=style,
            generate_audio=generate_audio, skip_if_exists=skip_if_exists,
            output_dir=output_dir, on_progress=on_progress,
        )
        results.append(result)
    return results

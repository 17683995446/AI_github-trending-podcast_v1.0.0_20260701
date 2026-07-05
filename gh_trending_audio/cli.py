"""
cli.py —— 命令行入口

完整工作流：
  1. 从 GitHub 获取最近高价值项目（GitHub Search API）
  2. 获取每个项目的 README
  3. 生成通俗易懂的音频文档（模板 / LLM）
  4. 用 edge-tts 合成 MP3 音频

用法示例：
  # 获取最近 7 天 Python 热门项目，生成中文音频
  python main.py --days 7 --limit 3 --language python

  # 获取 AI 相关项目，英文音频
  python main.py --topic ai --lang en --voice en-US-GuyNeural

  # 启用 LLM 增强（需设置 LLM_API_KEY 环境变量）
  python main.py --use-llm --limit 2

  # 列出可用的中文语音
  python main.py --list-voices
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table

from .exceptions import GhTrendingError
from .github_fetcher import GitHubFetcher
from .models import RepoInfo
from .document_generator import DocumentGenerator, AudioDocument
from .logging_config import get_logger
from .tts_engine import TTSEngine, VOICES

console = Console()
logger = get_logger(__name__)

# 输出根目录（用于跨目录去重检查）
# cli.py 在 gh_trending_audio/gh_trending_audio/cli.py，项目根目录是上两级
OUTPUT_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════════════════════════
# 共享辅助函数（阶段3: 消除 CLI 中的重复模式）
# ═══════════════════════════════════════════════════════════════════

def _print_engine_status() -> None:
    """打印 TTS 引擎可用性状态（消除 4 处重复）。"""
    engines = TTSEngine.check_engines()
    for name, info in engines.items():
        status_str = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status_str} {name}: {info['note']}")


def _safe_name(full_name: str) -> str:
    """将仓库全名转为安全的文件名。"""
    return full_name.replace("/", "_")


def _cleanup_empty_audio(audio_path: str) -> None:
    """清理失败的空音频文件（消除 5+ 处重复）。"""
    if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
        os.remove(audio_path)


def _synthesize_audio(
    tts: TTSEngine,
    script: str,
    audio_path: str,
    label: str = "",
    failure_hint: str = (
        "提示：所有 TTS 引擎均不可用。请安装 espeak-ng: apt-get install espeak-ng"
    ),
) -> bool:
    """合成音频并处理失败（返回是否成功）。

    Args:
        tts:          TTS 引擎实例
        script:       音频脚本文本
        audio_path:   输出音频文件路径
        label:        错误前缀标签（如仓库名或「音频合成失败」）
        failure_hint: 失败时显示的提示信息
    """
    try:
        tts.text_to_speech(script, audio_path)
        return True
    except Exception as e:
        logger.warning("音频合成失败: %s", e, exc_info=True)
        console.print(f"  [red]✗ {label or '音频合成失败'}: {e}[/red]")
        _cleanup_empty_audio(audio_path)
        console.print(f"  [dim]    {failure_hint}[/dim]")
        return False


def _is_project_already_processed(base_dir: str, md_filename: str) -> bool:
    """
    检查项目是否已在任何 output_* 目录中处理过。

    遍历所有 output_* 子目录，如果存在同名 .md 文件则视为已处理。
    """
    if not os.path.isdir(base_dir):
        return False
    for d in os.listdir(base_dir):
        if not d.startswith("output"):
            continue
        dir_path = os.path.join(base_dir, d)
        if not os.path.isdir(dir_path):
            continue
        if os.path.exists(os.path.join(dir_path, md_filename)):
            return True
    return False


def run_pipeline(args: argparse.Namespace) -> None:
    """执行趋势项目抓取和播客生成流水线。

    根据参数属性自动选择批量、串行、单仓库或对比模式。

    Args:
        args: 命令行参数（argparse.Namespace）。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output or f"output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    console.print("\n[bold cyan]═══ GitHub Trending Audio ═══[/bold cyan]")

    # 对比模式：对比 2-3 个仓库，生成对比播客（借鉴 Zread.ai）
    if getattr(args, "compare", None):
        console.print(f"[dim]输出目录: {output_dir}/ | 模式: 多仓库对比[/dim]\n")
        _run_compare(args, output_dir)
        return

    # 单仓库模式：直接处理用户指定的 GitHub 仓库，跳过去重检查
    if getattr(args, "repo_url", None):
        console.print(f"[dim]输出目录: {output_dir}/ | 模式: 单仓库[/dim]\n")
        _run_single_repo(args, output_dir)
        return

    mode_label = "串行" if args.serial else "批量"
    console.print(f"[dim]输出目录: {output_dir}/ | 模式: {mode_label}[/dim]\n")

    if args.serial:
        _run_serial(args, output_dir)
    else:
        _run_batch(args, output_dir)


def _run_batch(args: argparse.Namespace, output_dir: str) -> None:
    """批量模式：先全部获取项目，再统一处理（适合少量项目）。

    Args:
        args: 命令行参数。
        output_dir: 输出目录路径。
    """
    # ── Step 1: 获取 GitHub 趋势项目 ──
    console.print("[bold]Step 1/4[/bold] 获取 GitHub 高价值项目...")
    fetcher = GitHubFetcher(token=args.token)
    repos = fetcher.fetch_trending(
        days=args.days,
        limit=args.limit,
        language=args.language,
        min_stars=args.min_stars,
        topic=args.topic,
    )

    if not repos:
        console.print("[red]✗ 未找到符合条件的项目[/red]")
        return

    _print_repo_table(repos)

    # ── Step 1.5: 去重 ──
    original_count = len(repos)
    repos = [
        repo for repo in repos
        if not _is_project_already_processed(
            OUTPUT_BASE_DIR, f"{_safe_name(repo.full_name)}.md"
        )
    ]
    skipped = original_count - len(repos)
    if skipped > 0:
        console.print(f"  [yellow]⚠ 跳过 {skipped} 个已处理的项目[/yellow]")
    if not repos:
        console.print("[yellow]所有项目均已处理过，无需重复生成[/yellow]")
        return

    # ── Step 2: 获取 README + 深度信息 ──
    console.print("\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    for repo in repos:
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)
        console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成音频文档 ──
    console.print("\n[bold]Step 3/4[/bold] 生成音频文档...")
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    documents: list[tuple[RepoInfo, AudioDocument]] = []

    for repo in repos:
        doc = gen.generate(repo)
        documents.append((repo, doc))

        # 保存 Markdown
        safe_name = _safe_name(repo.full_name)
        md_path = os.path.join(output_dir, f"{safe_name}.md")
        script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
        doc.save(md_path, script_path)
        console.print(f"  [green]✓[/green] {repo.full_name} -> {safe_name}.md")

    # ── Step 4: 合成音频 ──
    console.print(f"\n[bold]Step 4/4[/bold] 合成语音（引擎: {args.engine}）...")
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine)

    _print_engine_status()

    audio_files: list[str] = []
    for repo, doc in documents:
        safe_name = _safe_name(repo.full_name)
        audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
        if _synthesize_audio(tts, doc.audio_script, audio_path, label=repo.full_name):
            audio_files.append(audio_path)

    _print_summary(output_dir, len(documents), len(audio_files))


def _run_serial(args: argparse.Namespace, output_dir: str) -> None:
    """串行模式：逐个项目完整处理（获取→README→文档→音频）。

    边获取边处理，内存占用低，单个项目失败不影响其他，适合大量项目。

    Args:
        args: 命令行参数。
        output_dir: 输出目录路径。
    """
    console.print("[bold]串行模式[/bold] 逐个项目处理（获取→文档→音频）\n")

    fetcher = GitHubFetcher(token=args.token)
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine, style=args.style)

    _print_engine_status()

    doc_count = 0
    audio_count = 0
    repo_list: list[RepoInfo] = []

    # 使用生成器逐个获取项目
    for repo in fetcher.fetch_trending_iter(
        days=args.days,
        limit=args.limit,
        language=args.language,
        min_stars=args.min_stars,
        topic=args.topic,
    ):
        repo_list.append(repo)
        idx = len(repo_list)

        console.print(f"\n[bold cyan]── [{idx}/{args.limit}] {repo.full_name} ──[/bold cyan]")

        # 0) 去重检查：跳过已处理过的项目
        safe_name = _safe_name(repo.full_name)
        md_filename = f"{safe_name}.md"
        if _is_project_already_processed(OUTPUT_BASE_DIR, md_filename):
            console.print("  [yellow]⚠ 已存在，跳过（如需重新生成请先删除）[/yellow]")
            continue

        # 1) 获取 README + 深度信息
        console.print("  [dim]获取 README 和深度信息...[/dim]")
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)

        # 2) 生成文档
        console.print("  [dim]生成音频文档...[/dim]")
        doc = gen.generate(repo)
        safe_name = _safe_name(repo.full_name)
        md_path = os.path.join(output_dir, f"{safe_name}.md")
        script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
        doc.save(md_path, script_path)
        doc_count += 1
        console.print("  [green]✓ 文档已保存[/green]")

        # 3) 合成音频
        audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
        if _synthesize_audio(
            tts, doc.audio_script, audio_path,
            label="音频合成失败",
            failure_hint="文档已保存，可稍后手动生成音频",
        ):
            audio_count += 1

    # 打印项目总表
    if repo_list:
        _print_repo_table(repo_list)

    _print_summary(output_dir, doc_count, audio_count)


def _run_single_repo(args: argparse.Namespace, output_dir: str) -> None:
    """单仓库模式：处理 --repo-url 指定的单个 GitHub 仓库。

    跳过去重检查，允许重复生成用户手动指定的仓库。

    Args:
        args: 命令行参数。
        output_dir: 输出目录路径。
    """
    console.print("[bold]单仓库模式[/bold] 处理指定 GitHub 仓库\n")

    fetcher = GitHubFetcher(token=args.token)

    # ── Step 1: 获取仓库信息 ──
    console.print("[bold]Step 1/4[/bold] 获取仓库信息...")
    try:
        repo = fetcher.fetch_single_repo(args.repo_url)
    except Exception as e:
        console.print(f"[red]✗ 获取仓库失败: {e}[/red]")
        return

    _print_repo_table([repo])

    # ── Step 2: 获取 README + 深度信息 ──
    console.print("\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    fetcher.enrich_with_readme(repo)
    if args.use_llm:
        fetcher.enrich_with_details(repo)
    console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成音频文档 ──
    console.print("\n[bold]Step 3/4[/bold] 生成音频文档...")
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    doc = gen.generate(repo)
    safe_name = _safe_name(repo.full_name)
    md_path = os.path.join(output_dir, f"{safe_name}.md")
    script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
    doc.save(md_path, script_path)
    console.print(f"  [green]✓[/green] {repo.full_name} -> {safe_name}.md")

    # ── Step 4: 合成音频 ──
    console.print(f"\n[bold]Step 4/4[/bold] 合成语音（引擎: {args.engine}）...")
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine, style=args.style)

    _print_engine_status()

    audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
    audio_count = 1 if _synthesize_audio(
        tts, doc.audio_script, audio_path, label=repo.full_name
    ) else 0

    _print_summary(output_dir, 1, audio_count)


def _run_compare(args: argparse.Namespace, output_dir: str) -> None:
    """对比模式：对比 2-3 个仓库并生成对比文档和对比播客（需 LLM）。

    借鉴 Zread.ai，强制启用 LLM 进行多仓库技术对比分析。

    Args:
        args: 命令行参数。
        output_dir: 输出目录路径。
    """
    # ── 解析仓库 URL 列表 ──
    raw_urls = args.compare or ""
    urls = [u.strip() for u in raw_urls.split(",") if u.strip()]
    if len(urls) < 2:
        console.print("[red]✗ 对比模式至少需要 2 个仓库 URL（用逗号分隔）[/red]")
        console.print(
            "[dim]  用法：python main.py --compare "
            "\"https://github.com/a/b,https://github.com/c/d\" --use-llm[/dim]"
        )
        return
    if len(urls) > 3:
        console.print(
            f"[yellow]⚠ 对比最多支持 3 个项目，已截取前 3 个（传入 {len(urls)} 个）[/yellow]"
        )
        urls = urls[:3]

    console.print("[bold]多仓库对比模式[/bold] 逐个获取仓库并生成对比播客\n")

    fetcher = GitHubFetcher(token=args.token)

    # ── Step 1: 获取各仓库信息 ──
    console.print(f"[bold]Step 1/4[/bold] 获取 {len(urls)} 个仓库信息...")
    repos: list[RepoInfo] = []
    for idx, url in enumerate(urls, 1):
        try:
            repo = fetcher.fetch_single_repo(url)
            repos.append(repo)
            console.print(f"  [green]✓[/green] [{idx}/{len(urls)}] {repo.full_name}")
        except Exception as e:
            console.print(f"  [red]✗[/red] [{idx}/{len(urls)}] {url}: {e}")
    if len(repos) < 2:
        console.print("[red]✗ 成功获取的仓库不足 2 个，无法进行对比[/red]")
        return

    _print_repo_table(repos)

    # ── Step 2: 获取 README + 深度信息 ──
    console.print("\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    for repo in repos:
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)
        console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成对比文档和脚本 ──
    console.print("\n[bold]Step 3/4[/bold] 生成对比文档和对比播客...")

    if not args.use_llm:
        console.print(
            "[yellow]⚠ 对比模式需要 LLM，已自动启用 --use-llm[/yellow]"
        )
        args.use_llm = True

    try:
        from .llm_enhancer import LLMEnhancer
        from openai import OpenAI

        enhancer = LLMEnhancer(language=args.lang, style=args.style)
        client = OpenAI(api_key=enhancer.api_key, base_url=enhancer.base_url)

        # 对每个项目做技术分析（复用 Step 1 分析逻辑）
        analyses: list[str] = []
        for idx, repo in enumerate(repos, 1):
            console.print(f"[dim]  分析项目 {idx}/{len(repos)}: {repo.name}...[/dim]")
            analysis = enhancer._analyze_project(client, repo, repo.readme_text)
            analyses.append(analysis)

        # 生成对比文档和脚本
        markdown, audio_script = enhancer.generate_comparison(repos, analyses)
    except Exception as e:
        console.print(f"[red]✗ 对比分析失败: {e}[/red]")
        console.print_exception()
        return

    # 构建对比文件名：compare_A_vs_B_vs_C
    safe_names = [r.name for r in repos]
    base_name = "compare_" + "_vs_".join(safe_names)
    md_path = os.path.join(output_dir, f"{base_name}.md")
    script_path = os.path.join(output_dir, f"{base_name}_script.txt")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(audio_script)
    console.print(f"  [green]✓[/green] 对比文档 -> {base_name}.md")

    # ── Step 4: 合成音频 ──
    console.print(f"\n[bold]Step 4/4[/bold] 合成对比播客语音（引擎: {args.engine}）...")
    tts = TTSEngine(
        voice=args.voice, language=args.lang, rate=args.rate,
        engine=args.engine, style=args.style,
    )

    _print_engine_status()

    audio_path = os.path.join(output_dir, f"{base_name}.mp3")
    audio_count = 1 if _synthesize_audio(
        tts, audio_script, audio_path,
        label="对比播客音频合成失败",
        failure_hint="文档已保存，可稍后手动生成音频",
    ) else 0

    _print_summary(output_dir, 1, audio_count)


def _print_summary(output_dir: str, doc_count: int, audio_count: int) -> None:
    """打印最终汇总。

    Args:
        output_dir: 输出目录路径。
        doc_count: 生成的文档数量。
        audio_count: 生成的音频数量。
    """
    console.print("\n[bold green]═══ 完成！═══[/bold green]")
    console.print(f"生成 {doc_count} 篇文档 + {audio_count} 个音频文件")
    console.print(f"[dim]输出目录: {os.path.abspath(output_dir)}/[/dim]\n")

    # 打印输出文件列表
    table = Table(title="输出文件", show_header=True, header_style="bold magenta")
    table.add_column("文件", style="cyan")
    table.add_column("大小", justify="right")
    for f in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, f)
        size = os.path.getsize(fpath)
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
        table.add_row(f, size_str)
    console.print(table)


def _print_repo_table(repos: list[RepoInfo]) -> None:
    """用表格展示获取到的项目。

    Args:
        repos: 仓库信息列表。
    """
    table = Table(title="获取到的热门项目", show_header=True, header_style="bold blue")
    table.add_column("#", style="dim", width=3)
    table.add_column("项目", style="cyan")
    table.add_column("⭐ Stars", justify="right", style="yellow")
    table.add_column("语言", style="green")
    table.add_column("描述", max_width=50)

    for i, repo in enumerate(repos, 1):
        desc = (repo.description or "")[:50]
        if len(repo.description or "") > 50:
            desc += "..."
        table.add_row(str(i), repo.full_name, f"{repo.stars:,}", repo.language, desc)
    console.print(table)


def list_voices(lang: str) -> None:
    """列出可用语音。

    Args:
        lang: 语言过滤（如 zh、en），为空则列出全部。
    """
    console.print("\n[bold]预设语音列表[/bold]\n")
    for lang_key, voices in VOICES.items():
        if lang and lang != lang_key:
            continue
        table = Table(title=f"{lang_key.upper()} 语音", show_header=True)
        table.add_column("别名", style="cyan")
        table.add_column("语音名称", style="green")
        for alias, name in voices.items():
            table.add_row(alias, name)
        console.print(table)
    console.print(
        "\n[dim]提示：完整语音列表请访问 https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support[/dim]"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gh-trending-audio",
        description="自动获取 GitHub 高价值项目并转化为音频文档（零成本，基于 edge-tts / 硅基流动）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
预设命令（推荐新用户使用）:
  python main.py quick                # 快速体验：3个Python项目，中文音频，零配置
  python main.py podcast              # 高质量播客：启用LLM双人对话，需设置LLM_API_KEY
  python main.py compare <urls>       # 多仓库对比播客

高级用法（完整参数）:
  # 获取最近 7 天的 Python 热门项目，生成中文音频
  python main.py --days 7 --limit 3 --language python

  # 获取 50 个项目（自动分页，突破单页 30 条限制）
  python main.py --limit 50 --language python

  # 串行模式：逐个项目处理（边获取边生成，适合大量项目）
  python main.py --limit 100 --serial --language python

  # 获取 AI/LLM 相关项目
  python main.py --topic llm --limit 5

  # 英文播客
  python main.py --output-lang en --voice en-US-GuyNeural

  # 启用 LLM 增强（更生动的播客脚本）
  export LLM_API_KEY=sk-xxx
  python main.py --use-llm --limit 2

  # 处理单个指定仓库（任意 GitHub URL，跳过去重）
  python main.py --repo-url https://github.com/owner/repo

  # 多仓库对比模式：对比 2-3 个项目，生成对比播客（借鉴 Zread.ai）
  python main.py --compare "https://github.com/a/b,https://github.com/c/d" --use-llm

  # 查看可用语音
  python main.py --list-voices
""",
    )

    # ── 预设子命令 ──
    sub = p.add_subparsers(dest="command", help="预设命令（简化常用操作）")

    # quick: 零配置快速体验
    quick = sub.add_parser("quick", help="快速体验：3个Python项目，中文音频，零配置")
    quick.add_argument("--language", type=str, default="python", help="编程语言过滤（默认 python）")
    quick.add_argument("--limit", type=int, default=3, help="项目数量（默认 3）")

    # podcast: 高质量双人对话播客
    pod = sub.add_parser("podcast", help="高质量播客：启用LLM双人对话")
    pod.add_argument("--language", type=str, default=None, help="编程语言过滤")
    pod.add_argument("--limit", type=int, default=5, help="项目数量（默认 5）")
    pod.add_argument("--style", type=str, default="dialogue",
        choices=["dialogue", "debate", "interview", "news", "story"],
        help="播客风格（默认 dialogue）")
    pod.add_argument("--output-lang", type=str, default="zh", choices=["zh", "en"],
        help="输出语言（默认 zh）")

    # compare: 多仓库对比播客
    cmp = sub.add_parser("compare", help="多仓库对比播客")
    cmp.add_argument("urls", type=str, help='仓库URL（逗号分隔），如 "https://github.com/a/b,https://github.com/c/d"')
    cmp.add_argument("--output-lang", type=str, default="zh", choices=["zh", "en"],
        help="输出语言（默认 zh）")

    # ── 完整参数模式（向后兼容） ──
    p.add_argument("--days", type=int, default=7, help="查看最近 N 天创建的项目（默认 7）")
    p.add_argument("--limit", type=int, default=5, help="获取前 N 个项目（默认 5）")
    p.add_argument("--language", type=str, default=None, help="按编程语言过滤（如 python、rust）")
    p.add_argument("--topic", type=str, default=None, help="按 topic 过滤（如 ai、llm、web）")
    p.add_argument("--min-stars", type=int, default=50, help="最低 star 数（默认 50）")

    p.add_argument(
        "--repo-url",
        type=str,
        default=None,
        help="指定 GitHub 仓库 URL（如 https://github.com/owner/repo），直接处理单个项目",
    )

    p.add_argument(
        "--compare",
        type=str,
        default=None,
        help=(
            "对比模式：指定多个仓库 URL（逗号分隔），生成对比播客。"
            "用法：--compare \"https://github.com/a/b,https://github.com/c/d\" --use-llm"
        ),
    )

    p.add_argument("--output-lang", type=str, default="zh", choices=["zh", "en"],
                   help="输出语言（默认 zh）")
    p.add_argument("--lang", type=str, default=None, choices=["zh", "en"],
                   help=argparse.SUPPRESS)  # 已废弃，保留向后兼容
    p.add_argument("--voice", type=str, default=None, help="指定语音（默认按语言选择）")
    p.add_argument("--rate", type=str, default="+0%", help="语速，如 +10%% 加速（默认 +0%%）")
    p.add_argument(
        "--engine",
        type=str,
        default="auto",
        choices=["auto", "siliconflow", "edge-tts", "espeak-ng"],
        help="TTS 引擎：auto（自动回退）、siliconflow（硅基流动 CosyVoice2）、edge-tts、espeak-ng",
    )

    p.add_argument("--use-llm", action="store_true", help="启用 LLM 增强（需设置 LLM_API_KEY）")
    p.add_argument("--style", type=str, default="dialogue",
        choices=["dialogue", "debate", "interview", "news", "story"],
        help="播客风格：dialogue(双人对话) debate(辩论式) interview(采访式) news(新闻播报) story(故事式)")
    p.add_argument("--serial", action="store_true", help="串行模式：逐个项目处理（获取→文档→音频），适合大量项目")
    p.add_argument("--token", type=str, default=None, help="GitHub Token（可选，提高 API 配额）")
    p.add_argument("--output", "-o", type=str, default=None, help="输出目录（默认自动生成）")

    p.add_argument("--list-voices", action="store_true", help="列出可用的预设语音")

    return p


def _apply_preset(args: argparse.Namespace) -> None:
    """将预设子命令映射为完整参数。

    Args:
        args: 命令行参数，原地修改。
    """
    cmd = getattr(args, "command", None)
    if cmd == "quick":
        # quick: 零配置快速体验，3个Python项目，模板模式，中文
        args.days = 7
        args.min_stars = 50
        args.topic = None
        args.repo_url = None
        args.compare = None
        args.output_lang = "zh"
        args.voice = None
        args.rate = "+0%"
        args.engine = "auto"
        args.use_llm = False
        args.style = "dialogue"
        args.serial = False
        args.token = None
        args.output = None
    elif cmd == "podcast":
        # podcast: 启用LLM双人对话，高质量播客
        args.days = 7
        args.min_stars = 50
        args.topic = None
        args.repo_url = None
        args.compare = None
        args.voice = None
        args.rate = "+0%"
        args.engine = "auto"
        args.use_llm = True
        args.serial = False
        args.token = None
        args.output = None
        # podcast 子命令有自己的 output_lang，映射到主参数
        if hasattr(args, "output_lang") and args.output_lang:
            pass  # 已有值
        else:
            args.output_lang = "zh"
    elif cmd == "compare":
        # compare: 多仓库对比播客
        urls = args.urls
        args.compare = urls
        args.days = 7
        args.limit = 3
        args.language = None
        args.min_stars = 50
        args.topic = None
        args.repo_url = None
        args.voice = None
        args.rate = "+0%"
        args.engine = "auto"
        args.use_llm = True
        args.style = "dialogue"
        args.serial = False
        args.token = None
        args.output = None


def _pre_flight_check(args: argparse.Namespace) -> None:
    """启动前置校验：提前发现配置问题，避免运行中途报错。

    Args:
        args: 命令行参数。
    """
    # --use-llm 时检查 LLM_API_KEY
    if args.use_llm and not getattr(args, "compare", None):
        from .config import LLM_API_KEY
        if not LLM_API_KEY:
            console.print("[red]✗ 启用了 --use-llm 但未设置 LLM_API_KEY[/red]")
            console.print("[dim]  请在 .env 中设置 LLM_API_KEY，或通过环境变量 export LLM_API_KEY=sk-xxx[/dim]")
            console.print("[dim]  硅基流动（9B以下永久免费）: https://cloud.siliconflow.cn/[/dim]")
            sys.exit(1)

    # --compare 模式也需要 LLM
    if getattr(args, "compare", None):
        from .config import LLM_API_KEY
        if not LLM_API_KEY:
            console.print("[red]✗ 对比模式需要 LLM 但未设置 LLM_API_KEY[/red]")
            console.print("[dim]  请在 .env 中设置 LLM_API_KEY[/dim]")
            sys.exit(1)

    # --compare 时检查 repomix
    if getattr(args, "compare", None):
        import shutil
        if not shutil.which("repomix"):
            console.print("[yellow]⚠ 未检测到 repomix（代码架构分析工具，对比模式推荐安装）[/yellow]")
            console.print("[dim]  安装: npm install -g repomix | 不装将仅基于 README 分析[/dim]")

    # --use-llm 时也提示 repomix
    if args.use_llm and not getattr(args, "compare", None):
        import shutil
        if not shutil.which("repomix"):
            console.print("[yellow]⚠ 未检测到 repomix，LLM 增强将仅基于 README（不分析代码架构）[/yellow]")
            console.print("[dim]  安装: npm install -g repomix | 不装也能用，但分析深度降低[/dim]")


def main() -> int:
    """命令行入口：解析参数并执行趋势音频生成流水线。

    Returns:
        程序退出码，0 表示成功，1 表示出错或取消。
    """
    parser = build_parser()
    args = parser.parse_args()

    # 处理预设子命令
    if getattr(args, "command", None):
        _apply_preset(args)

    # --lang 向后兼容：映射到 output_lang
    if hasattr(args, "lang") and args.lang:
        args.output_lang = args.lang
    # 确保 args.lang 始终有值（pipeline 函数引用 args.lang）
    args.lang = args.output_lang

    if args.list_voices:
        list_voices(args.output_lang)
        return

    # 前置校验
    _pre_flight_check(args)

    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(1)
    except GhTrendingError as e:
        logger.error("业务异常: %s", e, exc_info=True)
        console.print(f"\n[red]✗ 出错: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        logger.error("未预期异常: %s", e, exc_info=True)
        console.print(f"\n[red]✗ 出错: {e}[/red]")
        # 对常见错误给出友好提示
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "403" in err_msg:
            console.print("[dim]  GitHub API 速率限制，请设置 GITHUB_TOKEN 环境变量[/dim]")
        elif "websocket" in err_msg or "edge-tts" in err_msg:
            console.print("[dim]  edge-tts 连接失败，请检查网络或尝试 --engine espeak-ng[/dim]")
        else:
            console.print_exception()
        sys.exit(1)

    return 0


if __name__ == "__main__":
    main()

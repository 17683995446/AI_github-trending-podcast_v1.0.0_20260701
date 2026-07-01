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

from .github_fetcher import GitHubFetcher, RepoInfo
from .document_generator import DocumentGenerator, AudioDocument
from .tts_engine import TTSEngine, VOICES

console = Console()

# 输出根目录（用于跨目录去重检查）
# cli.py 在 gh_trending_audio/gh_trending_audio/cli.py，项目根目录是上两级
OUTPUT_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def run_pipeline(args):
    """执行完整流水线（支持批量模式、串行模式、单仓库模式和对比模式）"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output or f"output_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    console.print(f"\n[bold cyan]═══ GitHub Trending Audio ═══[/bold cyan]")

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


def _run_batch(args, output_dir: str):
    """批量模式：先全部获取项目，再统一处理（适合少量项目）"""
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
            OUTPUT_BASE_DIR, f"{repo.full_name.replace('/', '_')}.md"
        )
    ]
    skipped = original_count - len(repos)
    if skipped > 0:
        console.print(f"  [yellow]⚠ 跳过 {skipped} 个已处理的项目[/yellow]")
    if not repos:
        console.print("[yellow]所有项目均已处理过，无需重复生成[/yellow]")
        return

    # ── Step 2: 获取 README + 深度信息 ──
    console.print(f"\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    for repo in repos:
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)
        console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成音频文档 ──
    console.print(f"\n[bold]Step 3/4[/bold] 生成音频文档...")
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    documents: list[tuple[RepoInfo, AudioDocument]] = []

    for repo in repos:
        doc = gen.generate(repo)
        documents.append((repo, doc))

        # 保存 Markdown
        safe_name = repo.full_name.replace("/", "_")
        md_path = os.path.join(output_dir, f"{safe_name}.md")
        script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
        doc.save(md_path, script_path)
        console.print(f"  [green]✓[/green] {repo.full_name} -> {safe_name}.md")

    # ── Step 4: 合成音频 ──
    console.print(f"\n[bold]Step 4/4[/bold] 合成语音（引擎: {args.engine}）...")
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine)

    # 显示引擎可用性
    engines = TTSEngine.check_engines()
    for name, info in engines.items():
        status_str = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status_str} {name}: {info['note']}")

    audio_files: list[str] = []
    for repo, doc in documents:
        safe_name = repo.full_name.replace("/", "_")
        audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
        try:
            tts.text_to_speech(doc.audio_script, audio_path)
            audio_files.append(audio_path)
        except Exception as e:
            console.print(f"  [red]✗[/red] {repo.full_name}: {e}")
            if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
                os.remove(audio_path)
            console.print(
                f"[dim]    提示：所有 TTS 引擎均不可用。"
                f"请安装 espeak-ng: apt-get install espeak-ng[/dim]"
            )

    _print_summary(output_dir, len(documents), len(audio_files))


def _run_serial(args, output_dir: str):
    """
    串行模式：逐个项目完整处理（获取→README→文档→音频）

    优势：
        - 边获取边处理，无需等待所有项目下载完毕
        - 内存占用低（不缓存全部结果）
        - 某个项目失败不影响其他项目
        - 适合大量项目（如 50+ 个）
        - 第一个音频文件很快就生成，无需等全部完成
    """
    console.print("[bold]串行模式[/bold] 逐个项目处理（获取→文档→音频）\n")

    fetcher = GitHubFetcher(token=args.token)
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine, style=args.style)

    # 显示引擎可用性
    engines = TTSEngine.check_engines()
    for name, info in engines.items():
        status_str = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status_str} {name}: {info['note']}")

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
        safe_name = repo.full_name.replace("/", "_")
        md_filename = f"{safe_name}.md"
        if _is_project_already_processed(OUTPUT_BASE_DIR, md_filename):
            console.print(f"  [yellow]⚠ 已存在，跳过（如需重新生成请先删除）[/yellow]")
            continue

        # 1) 获取 README + 深度信息
        console.print(f"  [dim]获取 README 和深度信息...[/dim]")
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)

        # 2) 生成文档
        console.print(f"  [dim]生成音频文档...[/dim]")
        doc = gen.generate(repo)
        safe_name = repo.full_name.replace("/", "_")
        md_path = os.path.join(output_dir, f"{safe_name}.md")
        script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
        doc.save(md_path, script_path)
        doc_count += 1
        console.print(f"  [green]✓ 文档已保存[/green]")

        # 3) 合成音频
        audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
        try:
            tts.text_to_speech(doc.audio_script, audio_path)
            audio_count += 1
        except Exception as e:
            console.print(f"  [red]✗ 音频合成失败: {e}[/red]")
            if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
                os.remove(audio_path)
            console.print(f"  [dim]    文档已保存，可稍后手动生成音频[/dim]")

    # 打印项目总表
    if repo_list:
        _print_repo_table(repo_list)

    _print_summary(output_dir, doc_count, audio_count)


def _run_single_repo(args, output_dir: str):
    """
    单仓库模式：处理用户通过 --repo-url 指定的单个 GitHub 仓库。

    与批量/串行模式的区别：
        - 调用 fetch_single_repo 而非 fetch_trending_iter
        - 跳过去重检查（用户手动指定的仓库允许重复生成）
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
    console.print(f"\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    fetcher.enrich_with_readme(repo)
    if args.use_llm:
        fetcher.enrich_with_details(repo)
    console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成音频文档 ──
    console.print(f"\n[bold]Step 3/4[/bold] 生成音频文档...")
    gen = DocumentGenerator(language=args.lang, use_llm=args.use_llm, style=args.style)
    doc = gen.generate(repo)
    safe_name = repo.full_name.replace("/", "_")
    md_path = os.path.join(output_dir, f"{safe_name}.md")
    script_path = os.path.join(output_dir, f"{safe_name}_script.txt")
    doc.save(md_path, script_path)
    console.print(f"  [green]✓[/green] {repo.full_name} -> {safe_name}.md")

    # ── Step 4: 合成音频 ──
    console.print(f"\n[bold]Step 4/4[/bold] 合成语音（引擎: {args.engine}）...")
    tts = TTSEngine(voice=args.voice, language=args.lang, rate=args.rate, engine=args.engine, style=args.style)

    # 显示引擎可用性
    engines = TTSEngine.check_engines()
    for name, info in engines.items():
        status_str = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status_str} {name}: {info['note']}")

    audio_path = os.path.join(output_dir, f"{safe_name}.mp3")
    audio_count = 0
    try:
        tts.text_to_speech(doc.audio_script, audio_path)
        audio_count = 1
    except Exception as e:
        console.print(f"  [red]✗[/red] {repo.full_name}: {e}")
        if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
            os.remove(audio_path)
        console.print(
            f"[dim]    提示：所有 TTS 引擎均不可用。"
            f"请安装 espeak-ng: apt-get install espeak-ng[/dim]"
        )

    _print_summary(output_dir, 1, audio_count)


def _run_compare(args, output_dir: str):
    """
    对比模式：对比 2-3 个 GitHub 仓库，生成对比文档和对比播客。

    借鉴 Zread.ai 的多仓库对比能力：
        1. 解析 --compare 指定的逗号分隔 URL 列表
        2. 逐个获取仓库信息 + README + 深度信息
        3. 对每个项目做技术分析（复用 LLMEnhancer._analyze_project）
        4. 调用 LLMEnhancer.generate_comparison 生成对比文档和脚本
        5. 保存并合成 TTS 音频

    与单仓库模式的区别：
        - 处理多个仓库而非单个
        - 输出是「对比文档 + 对比播客」而非逐个项目文档
        - 强制要求 LLM 模式（对比分析需要 LLM）
    """
    # ── 解析仓库 URL 列表 ──
    raw_urls = args.compare or ""
    urls = [u.strip() for u in raw_urls.split(",") if u.strip()]
    if len(urls) < 2:
        console.print("[red]✗ 对比模式至少需要 2 个仓库 URL（用逗号分隔）[/red]")
        console.print(
            f"[dim]  用法：python main.py --compare "
            f"\"https://github.com/a/b,https://github.com/c/d\" --use-llm[/dim]"
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
    console.print(f"\n[bold]Step 2/4[/bold] 获取 README 和项目深度信息...")
    for repo in repos:
        fetcher.enrich_with_readme(repo)
        if args.use_llm:
            fetcher.enrich_with_details(repo)
        console.print(f"  [green]✓[/green] {repo.full_name}")

    # ── Step 3: 生成对比文档和脚本 ──
    console.print(f"\n[bold]Step 3/4[/bold] 生成对比文档和对比播客...")

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

    engines = TTSEngine.check_engines()
    for name, info in engines.items():
        status_str = "[green]✓[/green]" if info["available"] else "[red]✗[/red]"
        console.print(f"  {status_str} {name}: {info['note']}")

    audio_path = os.path.join(output_dir, f"{base_name}.mp3")
    audio_count = 0
    try:
        tts.text_to_speech(audio_script, audio_path)
        audio_count = 1
    except Exception as e:
        console.print(f"  [red]✗[/red] 对比播客音频合成失败: {e}")
        if os.path.exists(audio_path) and os.path.getsize(audio_path) == 0:
            os.remove(audio_path)
        console.print(
            f"[dim]    文档已保存，可稍后手动生成音频[/dim]"
        )

    _print_summary(output_dir, 1, audio_count)


def _print_summary(output_dir: str, doc_count: int, audio_count: int):
    """打印最终汇总"""
    console.print(f"\n[bold green]═══ 完成！═══[/bold green]")
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


def _print_repo_table(repos: list[RepoInfo]):
    """用表格展示获取到的项目"""
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


def list_voices(lang: str):
    """列出可用语音"""
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
        description="自动获取 GitHub 高价值项目并转化为音频文档（基于 edge-tts，零成本）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取最近 7 天的 Python 热门项目，生成中文音频
  python main.py --days 7 --limit 3 --language python

  # 获取 50 个项目（自动分页，突破单页 30 条限制）
  python main.py --limit 50 --language python

  # 串行模式：逐个项目处理（边获取边生成，适合大量项目）
  python main.py --limit 100 --serial --language python

  # 获取 AI/LLM 相关项目
  python main.py --topic llm --limit 5

  # 英文播客
  python main.py --lang en --voice en-US-GuyNeural

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

    p.add_argument("--lang", type=str, default="zh", choices=["zh", "en"], help="输出语言（默认 zh）")
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


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_voices:
        list_voices(args.lang)
        return

    try:
        run_pipeline(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ 出错: {e}[/red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()

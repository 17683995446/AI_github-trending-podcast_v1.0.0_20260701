"""
document_generator.py —— 将 GitHub 项目信息转化为通俗易懂的音频文档

两种模式：
  1. 模板模式（默认，零成本）：基于结构化模板生成播客式脚本
  2. LLM 模式（可选）：调用大模型生成更生动的内容

输出两种格式：
  - Markdown 文档（.md）：人可阅读
  - 音频脚本（纯文本）：供 TTS 引擎朗读
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console

from .github_fetcher import RepoInfo

console = Console()


@dataclass
class AudioDocument:
    """一个项目的完整音频文档"""

    repo: RepoInfo
    title: str               # 文档标题
    markdown: str            # Markdown 全文
    audio_script: str       # TTS 朗读脚本（纯文本，无 Markdown 符号）

    def save(self, md_path: str, script_path: str):
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self.markdown)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(self.audio_script)


class DocumentGenerator:
    """生成通俗易懂的音频文档"""

    def __init__(self, language: str = "zh", use_llm: bool = False, style: str = "dialogue"):
        """
        Args:
            language: 输出语言，"zh"（中文）或 "en"（英文）
            use_llm:  是否使用 LLM 增强（需要配置 API Key）
            style:    播客风格 (dialogue/debate/interview/news/story)
        """
        self.language = language
        self.use_llm = use_llm
        self.style = style

    def generate(self, repo: RepoInfo, readme_text: str = "") -> AudioDocument:
        """生成单个项目的音频文档"""
        if self.use_llm:
            return self._generate_with_llm(repo, readme_text)
        return self._generate_with_template(repo, readme_text)

    # ------------------------------------------------------------------
    # 模板模式（零成本，无需任何 API Key）
    # ------------------------------------------------------------------

    def _generate_with_template(self, repo: RepoInfo, readme_text: str) -> AudioDocument:
        readme_preview = readme_text or repo.readme_text or repo.description

        if self.language == "zh":
            return self._template_zh(repo, readme_preview)
        return self._template_en(repo, readme_preview)

    def _template_zh(self, repo: RepoInfo, readme: str) -> AudioDocument:
        """中文模板：播客式音频脚本"""
        topics_str = "、".join(repo.topics[:5]) if repo.topics else "暂无标签"
        readme_excerpt = self._extract_key_sections(readme, max_chars=1500)
        arch_mermaid = self._gen_mermaid_arch(repo, language="zh")
        flow_mermaid = self._gen_mermaid_flow(repo, language="zh")

        # Phase 6: 优先使用 Jinja2 模板渲染
        markdown = self._render_jinja2("doc_zh.j2", repo=repo, topics_str=topics_str,
                                       readme_excerpt=readme_excerpt,
                                       arch_mermaid=arch_mermaid, flow_mermaid=flow_mermaid)
        if markdown is None:
            # 退化到 f-string 模板
            markdown = f"""# {repo.full_name}：{repo.description[:60] if repo.description else 'GitHub 热门项目'}

> 本文档由 GitHub Trending Audio 自动生成

## 项目概览

| 属性 | 信息 |
|------|------|
| 仓库 | [{repo.full_name}]({repo.url}) |
| Star 数 | ⭐ {repo.stars:,} |
| Fork 数 | 🍴 {repo.forks:,} |
| 编程语言 | {repo.language} |
| 开源协议 | {repo.license_name} |
| 标签 | {topics_str} |
| 创建时间 | {repo.created_at[:10] if repo.created_at else '未知'} |

## 项目简介

{repo.description or '该项目暂无描述。'}

## 架构图

```mermaid
{arch_mermaid}
```

## 使用流程

```mermaid
{flow_mermaid}
```

## 详细解读

{readme_excerpt}

## 相关链接

- 仓库地址：{repo.url}
"""
            if repo.homepage:
                markdown += f"- 项目主页：{repo.homepage}\n"

        # 音频脚本（播客风格，纯文本，适合 TTS）
        # 将 README 关键内容转为口语化句子
        spoken_points = self._readme_to_spoken_zh(readme_excerpt)
        spoken_body = "\n".join(spoken_points) if spoken_points else ""

        audio_script = f"""大家好，欢迎收听 GitHub 趋势榜。

今天给大家介绍一个最近非常火爆的开源项目，叫做 {repo.name}。

这个项目目前已经有 {repo.stars:,} 颗 Star，{repo.forks:,} 个 Fork，可以说是非常受欢迎了。它使用 {repo.language} 语言开发，采用 {repo.license_name} 开源协议。

那么，这个项目到底是做什么的呢？

简单来说，{repo.description or '它是一个在 GitHub 上广受关注的开源项目。'}

下面我来给大家详细介绍一下这个项目的关键信息。

{spoken_body}

如果你对这个项目感兴趣，可以到 GitHub 上搜索 {repo.full_name}，仓库地址我会在文档中附上。{f'项目主页是 {repo.homepage}。' if repo.homepage else ''}

它打的标签包括：{topics_str}。这些标签也反映了项目的技术方向和应用场景。

总的来说，这个项目之所以能在短期内获得这么多关注，说明它确实解决了某个痛点问题。如果你正在相关领域工作，不妨去试试看。

好，今天的 GitHub 趋势榜就到这里，我们下期再见！
"""
        return AudioDocument(
            repo=repo,
            title=f"{repo.full_name} 音频解读",
            markdown=markdown,
            audio_script=audio_script,
        )

    def _template_en(self, repo: RepoInfo, readme: str) -> AudioDocument:
        """English template: podcast-style audio script"""
        topics_str = ", ".join(repo.topics[:5]) if repo.topics else "N/A"
        readme_excerpt = self._extract_key_sections(readme, max_chars=1500)
        arch_mermaid = self._gen_mermaid_arch(repo, language="en")
        flow_mermaid = self._gen_mermaid_flow(repo, language="en")

        # Phase 6: 优先使用 Jinja2 模板渲染
        markdown = self._render_jinja2("doc_en.j2", repo=repo, topics_str=topics_str,
                                       readme_excerpt=readme_excerpt,
                                       arch_mermaid=arch_mermaid, flow_mermaid=flow_mermaid)
        if markdown is None:
            # 退化到 f-string 模板
            markdown = f"""# {repo.full_name}: {repo.description[:60] if repo.description else 'Trending GitHub Project'}

> Auto-generated by GitHub Trending Audio

## Overview

| Field | Info |
|-------|------|
| Repository | [{repo.full_name}]({repo.url}) |
| Stars | ⭐ {repo.stars:,} |
| Forks | 🍴 {repo.forks:,} |
| Language | {repo.language} |
| License | {repo.license_name} |
| Topics | {topics_str} |
| Created | {repo.created_at[:10] if repo.created_at else 'N/A'} |

## Architecture

```mermaid
{arch_mermaid}
```

## Usage Flow

```mermaid
{flow_mermaid}
```

## Description

{repo.description or 'No description available.'}

## Deep Dive

{readme_excerpt}

## Links

- Repository: {repo.url}
"""
            if repo.homepage:
                markdown += f"- Homepage: {repo.homepage}\n"

        spoken_points_en = self._readme_to_spoken_en(readme_excerpt)
        spoken_body_en = "\n".join(spoken_points_en) if spoken_points_en else ""

        audio_script = f"""Hello and welcome to the GitHub Trending Report.

Today, I want to introduce a project that's been gaining a lot of attention recently. It's called {repo.name}.

This project currently has {repo.stars:,} stars and {repo.forks:,} forks on GitHub, which means it's quite popular. It's written in {repo.language} and licensed under {repo.license_name}.

So, what exactly does this project do?

In short, {repo.description or 'it is an open-source project that has been gaining significant traction on GitHub.'}

Let me walk you through the key details of this project.

{spoken_body_en}

If you're interested in this project, you can find it on GitHub by searching for {repo.full_name}. {f'The project homepage is {repo.homepage}.' if repo.homepage else ''}

Its topics include: {topics_str}. These tags reflect the technical direction and use cases of the project.

Overall, the fact that this project gained so much attention in a short period means it really solves a real problem. If you work in a related field, it's definitely worth checking out.

That's it for today's GitHub Trending Report. See you next time!
"""
        return AudioDocument(
            repo=repo,
            title=f"{repo.full_name} Audio Review",
            markdown=markdown,
            audio_script=audio_script,
        )

    # ------------------------------------------------------------------
    # LLM 模式（可选，需要 API Key）
    # ------------------------------------------------------------------

    def _generate_with_llm(self, repo: RepoInfo, readme_text: str) -> AudioDocument:
        """使用 LLM 生成更生动的播客式脚本"""
        try:
            from .llm_enhancer import LLMEnhancer

            enhancer = LLMEnhancer(language=self.language, style=self.style)
            content = enhancer.generate_script(repo, readme_text)

            markdown = content.get("markdown", "")
            audio_script = content.get("audio_script", "")

            if not markdown or not audio_script:
                console.print("[yellow]⚠ LLM 返回为空，回退到模板模式[/yellow]")
                return self._generate_with_template(repo, readme_text)

            return AudioDocument(
                repo=repo,
                title=f"{repo.full_name} AI 解读",
                markdown=markdown,
                audio_script=audio_script,
            )
        except ImportError:
            console.print("[yellow]⚠ 未安装 openai 库，回退到模板模式[/yellow]")
            console.print("[dim]  pip install openai  可启用 LLM 模式[/dim]")
            return self._generate_with_template(repo, readme_text)
        except Exception as e:
            console.print(f"[yellow]⚠ LLM 调用失败: {e}，回退到模板模式[/yellow]")
            return self._generate_with_template(repo, readme_text)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_key_sections(text: str, max_chars: int = 1500) -> str:
        """
        从 README 中提取关键内容：
        - 优先取描述、特性、功能等段落
        - 去除安装说明、贡献指南、导航链接等冗余部分
        """
        if not text:
            return "（暂无详细信息）"

        # 需要跳过的章节标题（中英文）
        skip_keywords = [
            "install", "installation", "安装", "setup", "部署",
            "contributing", "贡献", "contribute",
            "license", "许可", "changelog",
            "faq", "常见问题", "troubleshoot",
            "security", "安全",
            "acknowledgment", "credit", "致谢",
        ]

        lines = text.split("\n")
        result: list[str] = []
        char_count = 0
        skip_section = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            lower = stripped.lower()

            # 检测章节切换
            if stripped.startswith("#"):
                skip_section = any(kw in lower for kw in skip_keywords)
                # 标题本身也保留（但跳过不重要的章节内容）
                if not skip_section:
                    clean_title = stripped.lstrip("#").strip()
                    if len(clean_title) > 2:
                        result.append(f"【{clean_title}】")
                        char_count += len(clean_title) + 2
                continue

            if skip_section:
                continue

            # 跳过过短的行（导航链接、按钮文字等）
            if len(stripped) < 8:
                continue

            # 跳过看起来像导航/菜单的行（单独的短词组合）
            if len(stripped) < 25 and not any(c in stripped for c in "。，.!?,；："):
                continue

            # 跳过纯链接行
            if stripped.startswith("http") or stripped.startswith("[!") or stripped.startswith("<img"):
                continue

            result.append(stripped)
            char_count += len(stripped)
            if char_count >= max_chars:
                break

        return "\n".join(result) if result else text[:max_chars]

    @staticmethod
    def _readme_to_spoken_zh(readme: str) -> list[str]:
        """
        将 README 关键内容转为适合朗读的中文口语化句子列表。
        每个元素是一句完整的口语化描述。
        """
        if not readme or len(readme) < 20:
            return []

        sentences: list[str] = []
        lines = [l.strip() for l in readme.split("\n") if l.strip()]

        for line in lines:
            # 跳过标题标记行
            if line.startswith("【") and line.endswith("】"):
                title = line.strip("【】")
                sentences.append(f"关于{title}方面，")
                continue

            # 跳过过短行
            if len(line) < 10:
                continue

            # 如果是英文行，简单翻译为中文引导语
            if all(ord(c) < 128 for c in line):
                # 英文内容，保留但加引导
                sentences.append(f"项目文档提到：{line}。")
            else:
                sentences.append(f"{line}。")

            if len(sentences) >= 6:
                break

        return sentences

    # ------------------------------------------------------------------
    # Phase 6: Jinja2 模板渲染（替代 f-string，支持复杂逻辑与继承）
    # ------------------------------------------------------------------

    @staticmethod
    def _render_jinja2(template_name: str, **context) -> Optional[str]:
        """使用 Jinja2 渲染文档模板。

        若 jinja2 未安装或模板文件缺失，返回 None（触发 f-string 回退）。

        Args:
            template_name: 模板文件名（如 "doc_zh.j2"），位于 templates/ 目录
            **context: 传递给模板的上下文变量

        Returns:
            渲染后的 Markdown 字符串，或 None（回退到 f-string）
        """
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError:
            return None

        templates_dir = Path(__file__).parent / "templates"
        if not templates_dir.exists():
            return None

        template_path = templates_dir / template_name
        if not template_path.exists():
            return None

        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(template_name)
        return template.render(**context)

    # ------------------------------------------------------------------
    # Mermaid 架构图 / 流程图生成（模板模式兜底，零 LLM 依赖）
    # ------------------------------------------------------------------

    @staticmethod
    def _gen_mermaid_arch(repo, language: str = "zh") -> str:
        """根据 repo 信息生成 Mermaid 架构图。

        不依赖 LLM，纯模板拼接，保证每次都能生成。
        """
        lang = repo.language or "Unknown"
        topics = repo.topics[:4] if repo.topics else []
        desc = (repo.description or "")[:40]
        name = repo.full_name.split("/")[-1] if "/" in repo.full_name else repo.full_name

        if language == "zh":
            label_core = "核心模块"
            label_input = "输入层"
            label_output = "输出层"
            label_comm = "社区生态"
            label_docs = "文档与测试"
        else:
            label_core = "Core Module"
            label_input = "Input Layer"
            label_output = "Output Layer"
            label_comm = "Community"
            label_docs = "Docs & Tests"

        topic_nodes = ""
        for i, t in enumerate(topics):
            safe_t = t.replace("-", "_").replace(".", "_")
            topic_nodes += f"    T{i}[{t}] --> Core\n"

        return f"""graph TD
    subgraph {label_input}
        GH[GitHub Source]
        RD[README / Docs]
    end
    subgraph {label_core}
        Core[{name}<br/>{lang}]
        {topic_nodes}    end
    subgraph {label_output}
        MD[Markdown 文档]
        AU[音频播客]
    end
    subgraph {label_comm}
        ST[⭐ {repo.stars:,} Stars]
        FK[🍴 {repo.forks:,} Forks]
    end
    subgraph {label_docs}
        DT[文档]
        CI[CI/CD]
    end
    GH --> Core
    RD --> Core
    Core --> MD
    Core --> AU
    ST -.-> Core
    FK -.-> Core
    Core -.-> DT
    Core -.-> CI"""

    @staticmethod
    def _gen_mermaid_flow(repo, language: str = "zh") -> str:
        """根据 repo 信息生成 Mermaid 使用流程图。"""
        name = repo.full_name.split("/")[-1] if "/" in repo.full_name else repo.full_name

        if language == "zh":
            steps = [
                ("A", "🔍 发现项目", f"GitHub Trending / 搜索"),
                ("B", "📥 克隆仓库", f"git clone {repo.full_name}"),
                ("C", "📖 阅读文档", "README + 文档"),
                ("D", "⚙️ 安装依赖", f"基于 {repo.language or '项目'} 环境"),
                ("E", "🚀 运行项目", "本地启动 / 部署"),
                ("F", "💡 实际使用", "集成到自己的项目"),
            ]
        else:
            steps = [
                ("A", "🔍 Discover", "GitHub Trending / Search"),
                ("B", "📥 Clone Repo", f"git clone {repo.full_name}"),
                ("C", "📖 Read Docs", "README + Documentation"),
                ("D", "⚙️ Install Dependencies", f"{repo.language or 'Project'} environment"),
                ("E", "🚀 Run Project", "Local start / Deploy"),
                ("F", "💡 Use in Practice", "Integrate into your project"),
            ]

        nodes = "\n".join(f'    {sid}["{label}<br/><small>{detail}</small>"]' for sid, label, detail in steps)
        arrows = " --> ".join(sid for sid, _, _ in steps)
        return f"graph LR\n{nodes}\n    {arrows}"

    @staticmethod
    def _readme_to_spoken_en(readme: str) -> list[str]:
        """Convert README key content to spoken English sentences."""
        if not readme or len(readme) < 20:
            return []

        sentences: list[str] = []
        lines = [l.strip() for l in readme.split("\n") if l.strip()]

        for line in lines:
            if line.startswith("【") and line.endswith("】"):
                title = line.strip("【】")
                sentences.append(f"Regarding {title},")
                continue

            if len(line) < 10:
                continue

            sentences.append(f"{line}.")
            if len(sentences) >= 6:
                break

        return sentences

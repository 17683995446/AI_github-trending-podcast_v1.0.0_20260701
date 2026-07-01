"""
llm_enhancer.py —— 可选的 LLM 增强：生成更生动的播客式脚本

设计原则：
  - 不绑定特定 LLM 提供商，默认用 OpenAI 兼容接口
  - 支持 OpenAI / DeepSeek / 通义千问等（均兼容 OpenAI API 格式）
  - 完全可选：不安装也能用模板模式
  - 通过环境变量配置，零硬编码

成本控制：
  - 仅处理 README 摘要（限制 token），不发送全文
  - 使用低成本模型即可（如 deepseek-chat / gpt-4o-mini）

模块拆分说明：
  - 播客风格定义 → gh_trending_audio.styles
  - LLM prompt 模板 → gh_trending_audio.prompts
  - 本模块只保留 LLM 调用与脚本后处理等技术逻辑（_analyze_project /
    _clean_audio_script / _extract_mermaid / _insert_mermaid_into_md）
"""

from __future__ import annotations

from rich.console import Console

from .github_fetcher import RepoInfo
from .prompts import (
    comparison_system_prompt,
    comparison_user_prompt,
    dialogue_prompt,
    onboarding_user_prompt,
    system_prompt,
)
from .styles import STYLES

console = Console()


# ── Phase 5: 结构化输出模型（instructor + pydantic）──────────────
try:
    from pydantic import BaseModel, Field

    class PodcastScript(BaseModel):
        """LLM 结构化输出：播客文档 + 对话脚本。"""
        markdown: str = Field(..., description="项目深度解读的 Markdown 文档")
        audio_script: str = Field(..., description="双人对话脚本，格式 A: / B: 交替")

    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False


class LLMEnhancer:
    """使用 LLM 生成更生动的音频脚本，支持多种播客风格"""

    # ── 播客风格定义（委托给 styles.STYLES，保留类属性以兼容旧用法）──
    STYLES = STYLES

    def __init__(self, language: str = "zh", style: str = "dialogue"):
        """
        从 config.py 读取默认配置（硅基流动），也可通过环境变量覆盖。

        默认使用硅基流动 SiliconFlow 免费模型：
          - 模型: Qwen/Qwen2.5-7B-Instruct（9B 以下永久免费）
          - 无需自备 OpenAI API Key
        """
        from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

        self.language = language
        self.style = style if style in self.STYLES else "dialogue"
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.model = LLM_MODEL

        if not self.api_key:
            raise ValueError(
                "LLM API Key 未配置。请在 gh_trending_audio/config.py 中设置 LLM_API_KEY，"
                "或设置环境变量 LLM_API_KEY。"
            )

    def generate_script(self, repo: RepoInfo, readme_text: str) -> dict:
        """
        两步调用 LLM 生成播客式音频脚本：

        Step 1: 技术分析 —— 让 LLM 先从深度信息中提取技术要点
        Step 2: 对话生成 —— 基于技术要点生成双人对话脚本

        分步调用避免 7B 模型处理过多上下文时产生幻觉。

        Returns:
            {"markdown": str, "audio_script": str}
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # ── Step 1: 技术分析 ──
        console.print(f"[dim]调用 LLM ({self.model}) Step 1: 技术分析...[/dim]")
        tech_analysis = self._analyze_project(client, repo, readme_text)

        # ── Step 2: 生成对话 ──
        console.print(f"[dim]调用 LLM ({self.model}) Step 2: 生成对话...[/dim]")
        sys_prompt = system_prompt(self.style, self.language)
        user_prompt = dialogue_prompt(repo, tech_analysis, self.style, self.language)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=4000,
            top_p=0.85,
            frequency_penalty=0.3,
            presence_penalty=0.2,
        )

        content = response.choices[0].message.content or ""

        # Phase 5: 优先使用 instructor 结构化输出（消除 ===AUDIO=== 字符串分割）
        markdown = ""
        audio_script = ""
        used_instructor = False

        if _HAS_PYDANTIC:
            try:
                import instructor
                structured_client = instructor.from_openai(client)
                result = structured_client.chat.completions.create(
                    model=self.model,
                    response_model=PodcastScript,
                    messages=[
                        {"role": "system", "content": sys_prompt + "\n\n请以 JSON 格式返回，包含 markdown 和 audio_script 两个字段。"},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=4000,
                    top_p=0.85,
                )
                markdown = result.markdown
                audio_script = result.audio_script
                used_instructor = True
                console.print("[dim]  使用 instructor 结构化输出[/dim]")
            except Exception as e:
                console.print(f"[dim]  instructor 不可用，退化到字符串解析: {str(e)[:80]}[/dim]")

        if not used_instructor:
            # 退化到 ===AUDIO=== 字符串分割
            parts = content.split("===AUDIO===")
            markdown = parts[0].strip()
            audio_script = parts[1].strip() if len(parts) > 1 else content

        # 将 Step 1 技术分析中的 Mermaid 架构图注入 Markdown 文档
        mermaid_code = self._extract_mermaid(tech_analysis)
        if mermaid_code:
            markdown = self._insert_mermaid_into_md(markdown, mermaid_code)
            console.print("[dim]  已注入 Mermaid 架构图[/dim]")
        else:
            # LLM 未生成 Mermaid，使用模板兜底
            from .document_generator import DocumentGenerator
            arch_fallback = DocumentGenerator._gen_mermaid_arch(repo, language=self.language)
            flow_fallback = DocumentGenerator._gen_mermaid_flow(repo, language=self.language)
            fallback_block = f"\n## 架构图\n\n```mermaid\n{arch_fallback}\n```\n\n## 使用流程\n\n```mermaid\n{flow_fallback}\n```\n"
            markdown += fallback_block
            console.print("[dim]  LLM 未生成架构图，已注入模板兜底[/dim]")

        # 后处理
        audio_script = self._clean_audio_script(audio_script)

        return {"markdown": markdown, "audio_script": audio_script}

    # ------------------------------------------------------------------
    # 多仓库对比（借鉴 Zread.ai 的多仓库对比能力）
    # ------------------------------------------------------------------

    def generate_comparison(self, repos: list, analyses: list) -> tuple[str, str]:
        """
        生成多仓库对比文档和对比播客脚本。

        借鉴 Zread.ai 的多仓库对比能力：让用户可以选 2-3 个项目进行对比，
        生成对比分析文档和对比播客。A（主持人）和 B（技术专家）会围绕多个项目展开
        定位差异、技术架构对比、优劣势分析、适用场景推荐和综合评价。

        Args:
            repos: RepoInfo 列表（2-3 个）
            analyses: 每个项目的技术分析文本列表（与 repos 一一对应）

        Returns:
            (markdown_doc, audio_script)
        """
        from openai import OpenAI

        if not repos:
            raise ValueError("repos 不能为空，至少需要 2 个项目进行对比")
        if len(repos) < 2:
            raise ValueError("对比至少需要 2 个项目")
        if len(repos) > 3:
            console.print(
                f"[yellow]⚠ 对比最多支持 3 个项目，已截取前 3 个（传入 {len(repos)} 个）[/yellow]"
            )
            repos = repos[:3]
            analyses = analyses[:3]
        if len(analyses) < len(repos):
            # 分析不足时补齐空串，保证一一对应
            analyses = list(analyses) + [""] * (len(repos) - len(analyses))

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        console.print(
            f"[dim]调用 LLM ({self.model}) 生成 {len(repos)} 个项目的对比分析...[/dim]"
        )

        sys_prompt = comparison_system_prompt(self.style, self.language)
        user_prompt = comparison_user_prompt(repos, analyses, self.language)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=5000,
            top_p=0.85,
            frequency_penalty=0.3,
            presence_penalty=0.2,
        )

        content = response.choices[0].message.content or ""

        # 解析 LLM 返回（与 generate_script 一致的分隔符协议）
        parts = content.split("===AUDIO===")
        markdown = parts[0].strip()
        audio_script = parts[1].strip() if len(parts) > 1 else content

        # 如果模型未按结构输出标题，补一个标准标题
        if markdown and not markdown.lstrip().startswith("# 项目对比"):
            names = " vs ".join(r.name for r in repos)
            markdown = f"# 项目对比：{names}\n\n{markdown}"

        # 后处理音频脚本
        audio_script = self._clean_audio_script(audio_script)

        console.print(
            f"[dim]  对比分析完成（文档 {len(markdown)} 字，脚本 {len(audio_script)} 字）[/dim]"
        )
        return markdown, audio_script

    # ------------------------------------------------------------------
    # 受众定制入门指南（借鉴 Zread.ai 的受众定制化入门指南）
    # ------------------------------------------------------------------

    def generate_onboarding(self, repo_info, tech_analysis: str, audience: str = "beginner") -> str:
        """
        生成受众定制的新手入门指南。

        借鉴 Zread.ai 的受众定制化入门指南：根据项目技术分析，为不同受众
        （新手 / 开发者 / 架构师）生成侧重点不同的 Markdown 入门指南。

        Args:
            repo_info: RepoInfo 对象（至少包含 name / full_name / description 等）
            tech_analysis: Step 1 技术分析结果（或项目 Markdown 文档作为上下文）
            audience: "beginner"（新手）| "developer"（开发者）| "architect"（架构师）

        Returns:
            Markdown 格式的入门指南
        """
        from openai import OpenAI

        valid_audiences = {"beginner", "developer", "architect"}
        if audience not in valid_audiences:
            audience = "beginner"

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        console.print(
            f"[dim]调用 LLM ({self.model}) 生成入门指南（受众: {audience}）...[/dim]"
        )

        sys_prompt = (
            "你是项目入门指南生成器，根据项目技术分析为特定受众生成 Markdown 格式的入门指南。"
            "指南要实用、具体、可操作。"
        )
        user_prompt = onboarding_user_prompt(repo_info, tech_analysis, audience, self.language)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=3000,
            top_p=0.85,
        )

        guide = (response.choices[0].message.content or "").strip()
        console.print(f"[dim]  入门指南生成完成（{len(guide)} 字）[/dim]")
        return guide

    # ------------------------------------------------------------------
    # 技术方法：分析 / 后处理 / Mermaid 处理
    # ------------------------------------------------------------------

    def _analyze_project(self, client, repo: RepoInfo, readme: str) -> str:
        """
        Step 1: 让 LLM 分析项目深度信息，提取技术要点。
        这样 Step 2 只需要处理精炼的要点，不会过载。

        上下文来源：
          - Repomix 压缩的代码架构（函数签名、类定义、目录结构）
          - README
          - 版本发布、热门问题、语言占比、贡献者
        """
        # 构建深度信息摘要
        info_parts = []
        info_parts.append(f"项目描述: {repo.description or '无'}")
        info_parts.append(f"星标: {repo.stars:,} | 派生: {repo.forks:,} | 语言: {repo.language}")

        # Repomix 代码架构（包含目录结构 + 压缩的源码签名）
        if repo.file_tree:
            info_parts.append(f"代码架构（Repomix 压缩，含目录结构和函数签名）:\n{repo.file_tree[:8000]}")
        if repo.recent_releases:
            info_parts.append(f"版本发布:\n{repo.recent_releases[:400]}")
        if repo.recent_issues:
            info_parts.append(f"热门问题:\n{repo.recent_issues[:300]}")
        if repo.languages_breakdown:
            info_parts.append(f"语言占比: {repo.languages_breakdown}")
        if repo.contributors_count:
            info_parts.append(f"贡献者: {repo.contributors_count}")

        readme_short = readme[:600] if readme else ""
        info_parts.append(f"README:\n{readme_short}")

        raw_info = "\n\n".join(info_parts)

        if self.language == "zh":
            analysis_prompt = f"""你是一位资深技术分析师。请分析以下开源项目信息，提取关键技术要点。

以下信息包含 Repomix 工具压缩的代码架构（函数签名、类定义、import 关系和目录结构），以及社区动态信息。

{raw_info}

请输出以下内容（纯中文）：
1. 核心定位：一句话说明这个项目是做什么的
2. 技术架构：从代码架构分析项目的模块设计、分层模式和核心抽象
3. 核心类和函数：从函数签名中识别 3-5 个最重要的类或函数，解释它们的作用
4. 技术栈：从代码中发现的依赖库和框架（如有版本号请列出）
5. 创新点：这个项目有什么独特的设计模式或方法
6. 适用场景：什么人、什么场景下使用
7. 架构图：用 Mermaid 语法画出核心模块的关系图（graph TD 格式），展示模块间的依赖和数据流向，请用 ```mermaid 代码块包裹
"""
        else:
            analysis_prompt = f"""You are a senior technical analyst. Analyze the following project info and extract key technical points.

{raw_info}

Output:
1. Core positioning: one sentence
2. Technical architecture: from directory structure
3. Tech stack: from config files (with versions)
4. Core modules: 3-4 key modules and their purposes
5. Innovation: unique design or approach
6. Use cases
7. Architecture diagram: draw the core module relationship diagram using Mermaid syntax (graph TD format), showing module dependencies and data flow, wrapped in a ```mermaid code block
"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.2,
            max_tokens=2000,
            top_p=0.8,
        )
        analysis = response.choices[0].message.content or ""
        console.print(f"[dim]  技术分析完成（{len(analysis)} 字）[/dim]")
        return analysis

    @staticmethod
    def _clean_audio_script(text: str) -> str:
        """清理 LLM 输出的音频脚本，保留 A:/B: 说话人标记，确保适合 TTS 朗读"""
        import re

        lines = text.split("\n")
        cleaned_lines = []
        skip_header = True  # 跳过开头的标题行

        for line in lines:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 检测说话人标记（A: 或 B: 开头，保留不清理）
            is_dialogue = bool(re.match(r"^[AB][:：]", line))

            if not is_dialogue:
                # 移除 Markdown 标题符号
                line = re.sub(r"^#+\s*", "", line)

                # 移除表格相关内容
                if line.startswith("|") or line.startswith("---"):
                    continue

                # 移除 Markdown 链接，保留文字
                line = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", line)

                # 移除 URL
                line = re.sub(r"https?://\S+", "", line)

                # 移除 Markdown 格式符号
                line = re.sub(r"[*_>`#|-]", "", line)

                # 跳过开头的标题行
                if skip_header:
                    if re.match(r"^(音频脚本|第二部分|第三部分|纯文本|脚本|双人对话)[:：]?", line):
                        continue
                    if len(line) < 15 and ("脚本" in line or "部分" in line or "音频" in line or "对话" in line):
                        continue
                    skip_header = False
            else:
                # 对话行：只清理说话内容部分，保留 A:/B: 前缀
                speaker = line[0]
                content = line[2:].strip()

                # 清理格式符号
                content = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", content)
                content = re.sub(r"https?://\S+", "", content)
                content = re.sub(r"[*_>`#]", "", content)

                # 中文模式：清理英文连词和英文标点
                # 替换英文连词为中文
                content = re.sub(r"\s+and\s+", "和", content)
                content = re.sub(r"\s+to\s+", "到", content)
                content = re.sub(r"\s+the\s+", "", content)
                content = re.sub(r"\s+of\s+", "的", content)
                content = re.sub(r"\s+for\s+", "用于", content)
                content = re.sub(r"\s+with\s+", "使用", content)
                content = re.sub(r"\s+in\s+", "在", content)

                # 英文标点转中文标点（但保留版本号中的点，如 2.9.1）
                # 先保护版本号格式（数字.数字）
                content = re.sub(r"(\d)\.(\d)", r"\1§DOT§\2", content)
                content = content.replace(". ", "。")
                content = content.replace(".", "。")
                content = content.replace(", ", "，")
                content = content.replace(",", "，")
                content = content.replace("? ", "？")
                content = content.replace("?", "？")
                content = content.replace("! ", "！")
                content = content.replace("!", "！")
                content = content.replace(": ", "：")
                # 恢复版本号中的点
                content = content.replace("§DOT§", ".")

                # 修复重复字符（如 "解解算法" -> "解算法"，"configconfig" -> "config"）
                content = re.sub(r"(.)\1{2,}", r"\1", content)
                # 修复重复词（英文，如 "configconfig" -> "config"）
                content = re.sub(r"([a-zA-Z]{3,})\1", r"\1", content)

                # 跳过乱码行（中文字符太少且整体太短）
                chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", content))
                if chinese_chars < 3 and len(content) < 10:
                    continue

                line = f"{speaker}: {content}"

            # 修复重复双字词（如 "可以可以" -> "可以"）
            for length in [2, 3, 4]:
                pattern = r"(.{" + str(length) + r"})\1{1,}"
                line = re.sub(pattern, r"\1", line)

            # 去除连续重复行
            if cleaned_lines and line.strip() == cleaned_lines[-1].strip():
                continue

            # 清理多余的句号
            line = re.sub(r"。{2,}", "。", line)
            line = re.sub(r"^[。.,，]+", "", line.strip())

            if line.strip():
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def _extract_mermaid(analysis: str) -> str:
        """从技术分析结果中提取 Mermaid 图表代码。

        LLM 可能以下列形式输出图表：
          - ```mermaid ... ``` 围栏代码块（首选，最易解析）
          - 普通 ``` ... ``` 围栏代码块，内容以 graph/flowchart 开头
          - 纯文本中以 graph TD/LR ... 开头的行块
        返回纯净的 Mermaid 代码（不含围栏）；提取失败返回空串。
        """
        import re

        if not analysis:
            return ""

        # 1. 优先匹配 ```mermaid ... ``` 围栏代码块
        m = re.search(r"```mermaid\s*\n(.*?)```", analysis, re.DOTALL)
        if m:
            return m.group(1).strip()

        # 2. 匹配任意围栏代码块，取出其中以 graph/flowchart 开头的内容
        for m in re.finditer(r"```[a-zA-Z]*\s*\n(.*?)```", analysis, re.DOTALL):
            code = m.group(1).strip()
            if re.match(r"(graph|flowchart)\b", code):
                return code

        # 3. 退化：匹配以 graph/flowchart 开头的文本块，且块内确实包含 Mermaid 连接线
        #    （要求连接线可避免把散文中的 "graph" 一词误判为图表）
        m = re.search(
            r"((?:graph|flowchart)\b[^\n]*\n(?:(?!\n\s*\n)[^\n]*\n?)*)",
            analysis,
        )
        if m:
            block = m.group(1).strip()
            if re.search(r"(-->|---|-\.->|==>|~~>|-\.-)", block):
                return block

        return ""

    @staticmethod
    def _insert_mermaid_into_md(markdown: str, mermaid_code: str) -> str:
        """将 Mermaid 架构图代码块插入 Markdown 文档（「核心亮点」章节之后）。

        文档结构通常为：核心亮点 → 创新点分析 → 适用场景。
        在「核心亮点」章节结束、下一个章节标题之前插入 Mermaid 图。
        找不到锚点时回退到「创新点」之前，或追加到文档末尾。
        """
        import re

        if not mermaid_code:
            return markdown

        # 直接拼接，避免 mermaid_code 中的 {} 被 str.format 误解析
        mermaid_block = "\n## 架构图\n\n```mermaid\n" + mermaid_code + "\n```\n"

        lines = markdown.split("\n")

        def _find_header(keywords):
            """返回第一个包含任一关键词的 Markdown 标题行索引"""
            for i, line in enumerate(lines):
                if re.match(r"^#{1,6}\s", line):
                    low = line.lower()
                    if any(kw.lower() in low for kw in keywords):
                        return i
            return None

        def _next_header(after_idx):
            """返回 after_idx 之后的第一个 Markdown 标题行索引"""
            for j in range(after_idx + 1, len(lines)):
                if re.match(r"^#{1,6}\s", lines[j]):
                    return j
            return len(lines)

        # 优先在「核心亮点」章节之后插入
        highlight_idx = _find_header(["核心亮点", "核心功能", "highlight", "key feature"])
        if highlight_idx is None:
            # 退化：匹配任意含「核心亮点」的行（非标准标题格式）
            for i, line in enumerate(lines):
                if "核心亮点" in line:
                    highlight_idx = i
                    break

        if highlight_idx is not None:
            insert_idx = _next_header(highlight_idx)
            new_lines = lines[:insert_idx] + [mermaid_block.rstrip(), ""] + lines[insert_idx:]
            return "\n".join(new_lines)

        # 回退 1：在「创新点」标题之前插入
        innovation_idx = _find_header(["创新点", "innovation"])
        if innovation_idx is not None:
            new_lines = lines[:innovation_idx] + [mermaid_block.rstrip(), ""] + lines[innovation_idx:]
            return "\n".join(new_lines)

        # 回退 2：追加到文档末尾
        return markdown.rstrip() + "\n" + mermaid_block

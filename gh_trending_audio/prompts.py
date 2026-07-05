"""
prompts.py —— LLM prompt 模板生成

把原本 LLMEnhancer 中庞大的 _system_prompt / _dialogue_prompt / _comparison_*
/ _onboarding_user_prompt 等方法拆解为独立的纯函数，便于单测与复用。

设计原则：
  - 纯函数：输入风格 / 语言 / 上下文，输出 prompt 字符串，无副作用
  - _system_prompt 中巨大的 if-else 拆为每种风格一个辅助函数：
      * 结构模板：_dialogue_structure / _debate_structure / ...
      * 语气提示：_dialogue_tone / _debate_tone / ...
  - 文案与原实现逐字保持一致，确保 LLM 行为不发生变化
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .styles import PodcastStyle, get_style

if TYPE_CHECKING:
    from .models import RepoInfo


# =====================================================================
# 一、单仓库播客 system prompt（按风格生成）
# =====================================================================

# ── 各风格的对话结构模板 ──────────────────────────────────────────


def _dialogue_structure() -> str:
    return (
        "1. 开场（A 引入话题，B 点出项目名称和定位）\n"
        "2. 痛点分析（A 抛出问题，B 解释怎么解决）\n"
        "3. 核心功能深挖（A 追问，B 用比喻讲解 2-3 个模块的技术原理）\n"
        "4. 创新点解读（B 讲独特设计，A 追问为什么）\n"
        "5. 技术栈亮点（B 讲依赖库选型，A 帮理解）\n"
        "6. 实用建议（A 问谁该用，B 给建议）\n"
        "7. 结尾（A 总结，B 展望）"
    )


def _debate_structure() -> str:
    return (
        "1. 开场（A 提出项目亮点并看好，B 表示谨慎态度）\n"
        "2. 核心优势辩论（A 列举创新点，B 质疑是否真正创新或实用）\n"
        "3. 技术选型辩论（A 认为选型合理，B 指出潜在问题或更好替代）\n"
        "4. 适用场景辩论（A 认为适用面广，B 指出局限性）\n"
        "5. 风险与改进（B 指出安全/维护/文档风险，A 尝试辩护）\n"
        "6. 最终结论（双方各给一句总结性评价）\n"
        "注意：B 的质疑要有理有据，不是抬杠，而是指出真实的技术局限"
    )


def _interview_structure() -> str:
    return (
        "1. 开场（A 作为记者介绍背景，B 以作者身份打招呼）\n"
        "2. 灵感来源（A 问为什么做这个项目，B 分享开发动机）\n"
        "3. 技术选型（A 追问为什么选这个框架/库，B 解释决策原因）\n"
        "4. 核心架构（A 问最自豪的设计，B 讲解核心模块的实现思路）\n"
        "5. 踩坑经验（A 问开发中最大的挑战，B 分享遇到的困难）\n"
        "6. 未来计划（A 问后续方向，B 分享路线图）\n"
        "7. 结尾（A 感谢，B 总结）"
    )


def _news_structure() -> str:
    return (
        "1. 开场（A 播报今日开源速递，B 补充背景）\n"
        "2. 项目快讯（A 播报项目基本数据和动态，B 分析技术趋势）\n"
        "3. 技术解读（A 介绍核心技术栈，B 深入分析架构设计）\n"
        "4. 社区动态（A 播报星标增长和社区活跃度，B 评论生态健康度）\n"
        "5. 专家点评（B 给出专业评价，A 补充行业对比）\n"
        "6. 结尾（A 播报下期预告，B 总结本期要点）\n"
        "注意：语气正式，像新闻联播，不要口语化"
    )


def _story_structure() -> str:
    return (
        "1. 序幕（A 旁白交代行业背景和时代需求）\n"
        "2. 诞生（B 以作者视角讲述项目起源的灵感时刻）\n"
        "3. 成长（A 叙述社区采纳过程，B 讲述迭代开发经历）\n"
        "4. 挑战（A 描述遇到的技术瓶颈，B 讲述如何克服）\n"
        "5. 突破（A 叙述关键版本的创新突破，B 分享技术实现）\n"
        "6. 尾声（A 总结项目的行业影响，B 展望未来方向）\n"
        "注意：有叙事弧线，像讲故事，有起承转合"
    )


_STRUCTURE_MAP = {
    "dialogue": _dialogue_structure,
    "debate": _debate_structure,
    "interview": _interview_structure,
    "news": _news_structure,
    "story": _story_structure,
}


def _structure(style: str) -> str:
    """按风格返回对话结构模板，未知风格回退到 dialogue。"""
    return _STRUCTURE_MAP.get(style, _dialogue_structure)()


# ── 各风格的语气提示 ──────────────────────────────────────────────


def _dialogue_tone() -> str:
    return (
        "A 的台词要多样自然，可以用「这个我很好奇」「等等，你说的这个...」"
        "「能不能举个例子」等不同表达。B 要讲出具体的技术细节。"
    )


def _debate_tone() -> str:
    return (
        "A 和 B 要有对抗性但保持理性。A 用「我觉得」「从我的角度看」表达观点，"
        "B 用「但问题在于」「不过你有没有考虑过」来反驳。"
        "双方都要引用技术分析报告中的事实支撑论点。"
    )


def _interview_tone() -> str:
    return (
        "A 用「当时你是怎么想的」「为什么选择这个方案」等追问。"
        "B 用「当时的情况是」「我当时的考虑是」以第一人称回忆。语气亲切像老友聊天。"
    )


def _news_tone() -> str:
    return (
        "A 的语气正式客观，用「据了解」「数据显示」。"
        "B 做分析点评，用「从技术角度来看」「值得关注的是」。不要口语化表达。"
    )


def _story_tone() -> str:
    return (
        "A 的旁白有画面感和节奏感，用「那是一个...的时期」「故事要从...说起」。"
        "B 的讲述有情感起伏，用「我记得当时」「那一刻我意识到」。有叙事张力。"
    )


_TONE_MAP = {
    "dialogue": _dialogue_tone,
    "debate": _debate_tone,
    "interview": _interview_tone,
    "news": _news_tone,
    "story": _story_tone,
}


def _tone(style: str) -> str:
    """按风格返回语气提示，未知风格回退到 dialogue。"""
    return _TONE_MAP.get(style, _dialogue_tone)()


def system_prompt(style: str, language: str = "zh") -> str:
    """根据风格生成单仓库播客的 system prompt。"""
    style_def: PodcastStyle = get_style(style)
    sp_a = style_def.speakers["A"]
    sp_b = style_def.speakers["B"]

    if language == "zh":
        structure = _structure(style)
        tone = _tone(style)
        return (
            f"你正在创作一档{style_def.name}科技播客，{style_def.desc}。\n"
            f"两位角色如下：\n"
            f"A（{sp_a.role}）：{sp_a.trait}\n"
            f"B（{sp_b.role}）：{sp_b.trait}\n\n"
            f"输出格式要求（严格遵守）：\n"
            f"第一部分：Markdown 项目文档（标题、概览表格、项目简介、核心亮点、创新点分析、适用场景）\n"
            f"第二部分：分隔符（独占一行）\n===AUDIO===\n\n"
            f"第三部分：双人对话脚本，每行以 A: 或 B: 开头\n\n"
            f"对话结构：\n{structure}\n\n"
            f"语言要求（非常重要）：\n"
            f"- 全程纯中文，禁止在中文句子中出现英文连词（and、to、the、of 等）\n"
            f"- 英文专有名词可保留（如 Python、PyTorch），但要自然融入中文句子\n"
            f"- 中文句子用中文标点（。、，、？、！）\n"
            f"- Star 翻译为星标，Fork 翻译为派生\n\n"
            f"风格要求：\n{tone}\n"
            f"- A 和 B 交替发言，不要一人连续超过 2 句\n"
            f"- 每句话要完整通顺，不要出现乱码或重复字\n"
            f"- 对话总字数 1000 到 1500 字\n"
            f"- 禁止 Markdown 符号、URL、代码片段"
        )

    return (
        f"You are creating a {style_def.name} tech podcast.\n"
        f"A ({sp_a.role}): {sp_a.trait}\n"
        f"B ({sp_b.role}): {sp_b.trait}\n\n"
        f"Output: Markdown document, then ===AUDIO===, then dialogue (each line starts with A: or B:).\n"
        f"B must reference specific technical details.\n"
        f"Alternate speakers, max 2 consecutive lines.\n"
        f"600-1000 words total."
    )


def dialogue_prompt(
    repo: "RepoInfo",
    tech_analysis: str,
    style: str = "dialogue",
    language: str = "zh",
) -> str:
    """Step 2: 基于技术分析生成对话脚本。

    注意：``style`` 参数当前未参与文案生成（原实现即如此），保留以维持调用接口对称，
    便于后续按风格差异化 user prompt。
    """
    if language == "zh":
        return f"""以下是技术分析师对项目 {repo.name} 的深度分析，请基于这些内容创作双人对话播客。

【技术分析报告】
{tech_analysis}

要求：
1. 第一部分输出 Markdown 文档（含标题、表格、亮点、创新点、适用场景）
2. 第二部分输出 ===AUDIO=== 分隔符
3. 第三部分输出双人对话脚本，每行以 A: 或 B: 开头

4. B（老陈）必须在对话中引用技术分析报告中的具体内容：
   - 讲出具体的模块名称和它们的作用
   - 讲出具体的依赖库和版本号（如 PyTorch、Transformers）
   - 讲出架构设计的特点
   - 讲出创新点是什么、为什么重要

5. A（小林）的台词必须多样化，禁止连续使用相同句式：
   - 好的开场白：「大家好，欢迎收听开源雷达」
   - 追问时用：「这个我很好奇，能不能展开说说？」「等等，你刚说的这个...」「能不能给个通俗的例子？」「哇，这个设计确实有意思」「所以换句话说...」「那实际用起来效果怎么样？」
   - 禁止每句都用「那...呢？」的句式
   - A 每句台词不超过 2 个问句

6. 语言要求（非常重要）：
   - 全程纯中文，禁止在中文句子中出现英文连词（and、to、the、of）
   - 英文专有名词可保留（Python、PyTorch 等），但必须用中文标点
   - 句号用「。」，逗号用「，」，问号用「？」

7. 对话总字数 1000 到 1500 字
8. 每行必须以 A: 或 B: 开头，交替发言，不要一人连续超过 2 句
"""
    return f"""Based on the following technical analysis, create a two-person podcast dialogue.

【Technical Analysis】
{tech_analysis}

Output: Markdown document, then ===AUDIO===, then dialogue (each line starts with A: or B:, 600-1000 words). B must reference specific technical details from the analysis.
"""


# =====================================================================
# 二、多仓库对比播客 prompt
# =====================================================================


def comparison_system_prompt(style: str, language: str = "zh") -> str:
    """对比播客的 system prompt：A 和 B 围绕多个项目展开对比讨论。"""
    style_def: PodcastStyle = get_style(style)
    sp_a = style_def.speakers["A"]
    sp_b = style_def.speakers["B"]

    if language == "zh":
        return (
            f"你正在创作一档{style_def.name}科技播客的「多仓库对比」特别节目。\n"
            f"主持人 A（{sp_a.role}）：{sp_a.trait}\n"
            f"技术专家 B（{sp_b.role}）：{sp_b.trait}\n\n"
            f"这期节目要对比 2 到 3 个开源项目，A 和 B 必须围绕以下维度展开对比：\n"
            f"1. 定位差异：每个项目解决什么问题，目标人群和核心理念有什么不同\n"
            f"2. 技术架构对比：模块设计、技术栈选型、核心抽象的异同\n"
            f"3. 优劣势分析：每个项目的长处和短板，对比着说\n"
            f"4. 适用场景推荐：什么情况下选哪个项目更合适\n"
            f"5. 综合评价：给出整体性结论和选择建议\n\n"
            f"输出格式要求（严格遵守）：\n"
            f"第一部分：Markdown 对比文档，结构如下\n"
            f"  # 项目对比：A vs B vs C\n"
            f"  ## 概览对比表（星标、语言、协议、活跃度）\n"
            f"  ## 定位差异\n"
            f"  ## 技术架构对比\n"
            f"  ## 优势与劣势\n"
            f"  ## 适用场景推荐\n"
            f"  ## 综合评价\n"
            f"第二部分：分隔符（独占一行）\n===AUDIO===\n\n"
            f"第三部分：双人对话脚本，每行以 A: 或 B: 开头\n\n"
            f"语言要求（非常重要）：\n"
            f"- 全程纯中文，禁止在中文句子中出现英文连词（and、to、the、of 等）\n"
            f"- 英文专有名词可保留（如 Python、PyTorch），但要自然融入中文句子\n"
            f"- 中文句子用中文标点（。、，、？、！）\n"
            f"- Star 翻译为星标，Fork 翻译为派生\n\n"
            f"风格要求：\n"
            f"- A 负责抛出对比问题、引导话题，台词要多样自然\n"
            f"- B 必须引用各项目技术分析中的具体细节支撑对比结论（模块名、依赖库、星标数等）\n"
            f"- A 和 B 交替发言，不要一人连续超过 2 句\n"
            f"- 对比时要公平客观，既讲优势也讲短板\n"
            f"- 对话总字数 1200 到 1800 字\n"
            f"- 禁止 Markdown 符号、URL、代码片段出现在对话中"
        )

    return (
        f"You are creating a {style_def.name} tech podcast 'multi-repo comparison' special.\n"
        f"A ({sp_a.role}): {sp_a.trait}\n"
        f"B ({sp_b.role}): {sp_b.trait}\n\n"
        f"A and B must compare 2-3 open-source projects across these dimensions: "
        f"positioning differences, technical architecture, pros and cons, "
        f"use case recommendations, and overall evaluation.\n\n"
        f"Output: Markdown comparison document (with overview table, positioning, "
        f"architecture, pros/cons, use cases, overall evaluation), then ===AUDIO===, "
        f"then dialogue (each line starts with A: or B:, 800-1200 words). "
        f"B must reference specific technical details. Alternate speakers, max 2 consecutive lines."
    )


def comparison_user_prompt(repos: list, analyses: list, language: str = "zh") -> str:
    """对比播客的 user prompt：拼接各项目的基本信息和技术分析。"""
    names = " vs ".join(r.name for r in repos)
    project_blocks = []

    for idx, (repo, analysis) in enumerate(zip(repos, analyses), 1):
        topics = ", ".join(repo.topics[:6]) if getattr(repo, "topics", None) else "无"
        block = (
            f"【项目 {idx}：{repo.full_name}】\n"
            f"- 描述：{repo.description or '暂无'}\n"
            f"- 星标：{getattr(repo, 'stars', 0):,} | 派生：{getattr(repo, 'forks', 0):,} | "
            f"语言：{repo.language or '未知'}\n"
            f"- 开源协议：{getattr(repo, 'license_name', '') or '未知'}\n"
            f"- 最近更新：{getattr(repo, 'pushed_at', '')[:10] or '未知'}\n"
            f"- 标签：{topics}\n"
        )
        if analysis:
            block += f"- 技术分析报告：\n{analysis[:2500]}\n"
        project_blocks.append(block)

    projects_text = "\n\n".join(project_blocks)

    if language == "zh":
        return f"""请基于以下 {len(repos)} 个项目的信息和技术分析报告，生成对比文档和对比播客脚本。

{projects_text}

要求：
1. 第一部分输出 Markdown 对比文档，必须包含以下结构：
   # 项目对比：{names}
   ## 概览对比表（星标、语言、协议、活跃度）
   ## 定位差异
   ## 技术架构对比
   ## 优势与劣势
   ## 适用场景推荐
   ## 综合评价

2. 第二部分输出 ===AUDIO=== 分隔符（独占一行）

3. 第三部分输出双人对话脚本，每行以 A: 或 B: 开头

4. B 必须引用各项目技术分析报告中的具体内容做对比：
   - 对比各项目的模块设计和核心抽象
   - 对比依赖库和技术栈选型
   - 用星标数、活跃度等数据支撑结论
   - 明确指出哪个项目在哪个维度更强或更弱

5. A 的台词要多样化，用「这几个项目有什么本质区别？」「从架构上看呢？」「那如果我要选一个的话该选哪个？」等不同表达

6. 全程纯中文，禁止英文连词；中文标点；对话总字数 1200 到 1800 字
"""
    return f"""Based on the following {len(repos)} projects' info and technical analyses, generate a comparison document and podcast script.

{projects_text}

Output: Markdown comparison document (overview table, positioning, architecture, pros/cons, use cases, overall evaluation), then ===AUDIO===, then dialogue (each line starts with A: or B:, 800-1200 words). B must reference specific technical details to support comparisons.
"""


# =====================================================================
# 三、受众定制入门指南 prompt
# =====================================================================

# 不同受众的指南侧重（中英双版）
_AUDIENCE_PROFILES = {
    "beginner": {
        "label_zh": "新手",
        "label_en": "Beginner",
        "focus_zh": (
            "1. 项目是做什么的：用通俗语言解释它的作用和价值\n"
            "2. 为什么需要它：解决了什么实际问题，没有它会怎样\n"
            "3. 安装步骤：详细分步骤的安装指引（环境要求、依赖安装、命令行操作）\n"
            "4. 5 分钟上手示例：一个最小可运行的入门示例，附完整代码和预期输出\n"
            "5. 常见问题：新手最容易踩的 3-5 个坑及解决办法"
        ),
        "focus_en": (
            "1. What it does: explain in plain language\n"
            "2. Why you need it: the problem it solves\n"
            "3. Installation: detailed step-by-step (env, deps, commands)\n"
            "4. 5-minute quickstart: a minimal runnable example with code and expected output\n"
            "5. Common pitfalls: 3-5 issues beginners hit and how to fix them"
        ),
    },
    "developer": {
        "label_zh": "开发者",
        "label_en": "Developer",
        "focus_zh": (
            "1. 核心 API 和接口：列出 3-5 个最重要的 API/接口，说明参数、返回值和使用场景\n"
            "2. 如何集成到现有项目：集成步骤、依赖引入方式、配置项说明\n"
            "3. 扩展点和自定义方式：项目提供的扩展机制（插件、钩子、配置）及自定义方法\n"
            "4. 调试技巧：如何开启调试日志、常见报错的排查思路\n"
            "5. 代码贡献指南：如何搭建开发环境、运行测试、提交 PR 的规范"
        ),
        "focus_en": (
            "1. Core APIs: list 3-5 most important APIs with params, returns, use cases\n"
            "2. Integration: how to integrate into an existing project (deps, config)\n"
            "3. Extension points: plugins, hooks, config-based customization\n"
            "4. Debugging tips: enable debug logging, troubleshoot common errors\n"
            "5. Contributing: dev setup, running tests, PR guidelines"
        ),
    },
    "architect": {
        "label_zh": "架构师",
        "label_en": "Architect",
        "focus_zh": (
            "1. 整体架构设计：模块划分、分层结构、核心抽象和数据流\n"
            "2. 技术选型理由：为什么选这些库/框架，对比过哪些替代方案\n"
            "3. 扩展性和性能考量：横向扩展能力、性能瓶颈点、吞吐量/延迟特性\n"
            "4. 部署方案：推荐的部署架构、容器化方式、依赖的基础设施\n"
            "5. 替代方案对比：同类项目对比，各自的适用场景和取舍"
        ),
        "focus_en": (
            "1. Overall architecture: modules, layering, core abstractions, data flow\n"
            "2. Tech choices: why these libs/frameworks, alternatives considered\n"
            "3. Scalability & performance: horizontal scaling, bottlenecks, throughput/latency\n"
            "4. Deployment: recommended topology, containerization, infra dependencies\n"
            "5. Alternatives: comparison with similar projects, trade-offs"
        ),
    },
}


def onboarding_user_prompt(
    repo_info: "RepoInfo",
    tech_analysis: str,
    audience: str = "beginner",
    language: str = "zh",
) -> str:
    """构建入门指南的 user prompt，根据受众侧重不同内容。"""
    name = getattr(repo_info, "name", "") or ""
    full_name = getattr(repo_info, "full_name", "") or name
    desc = getattr(repo_info, "description", "") or "暂无"
    lang = getattr(repo_info, "language", "") or "未知"
    stars = getattr(repo_info, "stars", 0) or 0

    profile = _AUDIENCE_PROFILES[audience]
    context = (tech_analysis or "").strip() or "（暂无技术分析，请基于项目基本信息生成）"

    if language == "zh":
        return f"""请为项目 {name}（{full_name}）生成面向「{profile['label_zh']}」的入门指南。

【项目基本信息】
- 名称：{name}
- 全称：{full_name}
- 描述：{desc}
- 编程语言：{lang}
- 星标：{stars:,}

【项目技术分析报告（作为事实依据，请基于其中具体信息撰写）】
{context[:4000]}

请按以下结构生成 Markdown 入门指南，并侧重以下内容：
{profile['focus_zh']}

要求：
1. 输出纯 Markdown，以一级标题 `# {name} 入门指南（{profile['label_zh']}版）` 开头
2. 内容必须基于上述技术分析报告中的具体信息，不要编造不存在的 API、模块或功能
3. 代码示例用围栏代码块包裹并标注语言（如 ```bash、```python）
4. 步骤要具体可操作，给出真实的命令和代码
5. 全程中文，英文专有名词可保留，使用中文标点
"""
    return f"""Generate an onboarding guide for project {name} ({full_name}) targeted at "{profile['label_en']}".

【Project Info】
- Name: {name}
- Full name: {full_name}
- Description: {desc}
- Language: {lang}
- Stars: {stars:,}

【Technical Analysis Report (use as factual basis)】
{context[:4000]}

Generate a Markdown onboarding guide focusing on:
{profile['focus_en']}

Output pure Markdown starting with `# {name} Onboarding Guide ({profile['label_en']})`. Base content on the technical analysis; do not fabricate APIs. Use fenced code blocks with language tags. Be concrete and actionable.
"""

"""Mermaid 图表生成器（Phase 4: 解耦循环依赖）。

从 ``document_generator.py`` 提取 Mermaid 图表生成逻辑到独立模块，
消除 ``document_generator ↔ llm_enhancer`` 之间的循环依赖。

两个模块都通过 ``from .mermaid_gen import gen_mermaid_arch, gen_mermaid_flow``
导入，不再互相调用私有方法。
"""

from __future__ import annotations

from .models import RepoInfo


def gen_mermaid_arch(repo: RepoInfo, language: str = "zh") -> str:
    """根据 repo 信息生成 Mermaid 架构图。

    不依赖 LLM，纯模板拼接，保证每次都能生成。

    Args:
        repo: 仓库信息
        language: "zh"（中文）或 "en"（英文）

    Returns:
        Mermaid graph TD 语法的字符串
    """
    lang = repo.language or "Unknown"
    topics = repo.topics[:4] if repo.topics else []
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
        ST[{repo.stars:,} Stars]
        FK[{repo.forks:,} Forks]
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


def gen_mermaid_flow(repo: RepoInfo, language: str = "zh") -> str:
    """根据 repo 信息生成 Mermaid 使用流程图。

    Args:
        repo: 仓库信息
        language: "zh"（中文）或 "en"（英文）

    Returns:
        Mermaid graph LR 语法的字符串
    """
    if language == "zh":
        steps = [
            ("A", "发现项目", "GitHub Trending / 搜索"),
            ("B", "克隆仓库", f"git clone {repo.full_name}"),
            ("C", "阅读文档", "README + 文档"),
            ("D", "安装依赖", f"基于 {repo.language or '项目'} 环境"),
            ("E", "运行项目", "本地启动 / 部署"),
            ("F", "实际使用", "集成到自己的项目"),
        ]
    else:
        steps = [
            ("A", "Discover", "GitHub Trending / Search"),
            ("B", "Clone Repo", f"git clone {repo.full_name}"),
            ("C", "Read Docs", "README + Documentation"),
            ("D", "Install Dependencies", f"{repo.language or 'Project'} environment"),
            ("E", "Run Project", "Local start / Deploy"),
            ("F", "Use in Practice", "Integrate into your project"),
        ]

    nodes = "\n".join(f'    {sid}["{label}<br/><small>{detail}</small>"]' for sid, label, detail in steps)
    arrows = " --> ".join(sid for sid, _, _ in steps)
    return f"graph LR\n{nodes}\n    {arrows}"

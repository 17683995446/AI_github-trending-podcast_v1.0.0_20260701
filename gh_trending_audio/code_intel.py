"""代码智能分析模块（阶段12: ripgrep + tree-sitter + Prism.js）。

集成三个开源工具提升代码搜索与理解能力：

    - **ripgrep**：极速代码搜索（比 grep 快 10-100 倍）
    - **tree-sitter**：AST 级别的符号提取（函数/类/方法定义）
    - **Prism.js**：前端语法高亮（200+ 语言支持）

核心功能：
    - ``ripgrep_search()``     → 使用 ripgrep 搜索代码
    - ``extract_symbols()``    → 使用 tree-sitter 提取代码符号
    - ``detect_ripgrep()``     → 检测 ripgrep 可用性
    - ``detect_tree_sitter()`` → 检测 tree-sitter 可用性

设计原则：
    - 第一性原理：代码搜索应快速且准确
    - 优雅降级：ripgrep/tree-sitter 不可用时回退到现有方案
    - 零侵入：独立模块，增强而非替代现有功能
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .constants import RIPGREP_TIMEOUT
from .logging_config import get_logger

logger = get_logger(__name__)

# 文件扩展名 → 语言映射
_EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".kt": "kotlin",
    ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp", ".h": "c",
    ".hpp": "cpp", ".cs": "csharp", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".m": "objc", ".scala": "scala", ".clj": "clojure",
    ".ex": "elixir", ".exs": "elixir", ".erl": "erlang", ".hs": "haskell",
    ".lua": "lua", ".r": "r", ".dart": "dart", ".vue": "vue",
    ".svelte": "svelte", ".html": "html", ".css": "css", ".scss": "scss",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".xml": "xml", ".md": "markdown", ".sh": "bash", ".bash": "bash",
    ".zsh": "bash", ".fish": "bash", ".ps1": "powershell",
    ".sql": "sql", ".dockerfile": "dockerfile", ".makefile": "makefile",
}

# 文件扩展名 → Prism.js 语言类名
_EXT_TO_PRISM = {
    ".py": "language-python", ".js": "language-javascript", ".ts": "language-typescript",
    ".jsx": "language-jsx", ".tsx": "language-tsx", ".java": "language-java",
    ".go": "language-go", ".rs": "language-rust", ".c": "language-c",
    ".cpp": "language-cpp", ".h": "language-c", ".hpp": "language-cpp",
    ".cs": "language-csharp", ".rb": "language-ruby", ".php": "language-php",
    ".swift": "language-swift", ".scala": "language-scala", ".lua": "language-lua",
    ".r": "language-r", ".dart": "language-dart", ".html": "language-html",
    ".css": "language-css", ".scss": "language-scss", ".json": "language-json",
    ".yaml": "language-yaml", ".yml": "language-yaml", ".toml": "language-toml",
    ".xml": "language-xml", ".md": "language-markdown", ".sh": "language-bash",
    ".bash": "language-bash", ".sql": "language-sql",
}


def detect_ripgrep() -> bool:
    """检测 ripgrep 是否已安装。"""
    return shutil.which("rg") is not None


def detect_tree_sitter() -> bool:
    """检测 tree-sitter 是否可用。"""
    try:
        import tree_sitter_languages  # noqa: F401
        return True
    except ImportError:
        return False


def get_language_from_extension(filepath: str) -> str:
    """从文件扩展名推断编程语言。"""
    ext = Path(filepath).suffix.lower()
    # 特殊文件名
    name = Path(filepath).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    if name == "makefile":
        return "makefile"
    return _EXT_TO_LANG.get(ext, "unknown")


def get_prism_class(filepath: str) -> str:
    """获取文件对应的 Prism.js 语言类名。"""
    ext = Path(filepath).suffix.lower()
    name = Path(filepath).name.lower()
    if name == "dockerfile":
        return "language-docker"
    if name == "makefile":
        return "language-makefile"
    return _EXT_TO_PRISM.get(ext, "language-none")


def ripgrep_search(
    search_root: str,
    pattern: str,
    *,
    file_pattern: str = "",
    max_results: int = 50,
    context_lines: int = 2,
    regex_mode: bool = False,
) -> list[dict[str, Any]]:
    """使用 ripgrep 搜索代码。

    Args:
        search_root: 搜索根目录
        pattern: 搜索模式（自然语言或正则）
        file_pattern: 文件过滤模式（如 "*.py"）
        max_results: 最大结果数
        context_lines: 上下文行数
        regex_mode: 是否使用正则模式

    Returns:
        搜索结果列表，每项含 file/line_number/content/context
    """
    rg_bin = shutil.which("rg")
    if not rg_bin:
        logger.warning("ripgrep 不可用，无法执行搜索")
        return []

    cmd = [
        rg_bin,
        "--json",
        f"--max-count={max_results}",
        f"--context={context_lines}",
        "--no-ignore",
        "--hidden",
    ]

    if not regex_mode:
        cmd.append("--fixed-strings")

    if file_pattern:
        cmd.extend(["--glob", file_pattern])

    cmd.extend([pattern, search_root])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=RIPGREP_TIMEOUT,
        )
        if result.returncode not in (0, 1):  # 0=found, 1=not found
            logger.error(f"ripgrep 错误: {result.stderr}")
            return []
    except subprocess.TimeoutExpired:
        logger.warning("ripgrep 搜索超时")
        return []
    except (OSError, subprocess.SubprocessError):
        logger.error("ripgrep 执行失败", exc_info=True)
        return []

    results: list[dict[str, Any]] = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("type") == "match":
            data = entry.get("data", {})
            matches = data.get("submatches", [])
            results.append({
                "file": data.get("path", {}).get("text", ""),
                "line_number": data.get("line_number", 0),
                "content": data.get("lines", {}).get("text", "").rstrip(),
                "matches": [m.get("match", {}).get("text", "") for m in matches],
                "language": get_language_from_extension(data.get("path", {}).get("text", "")),
            })
            if len(results) >= max_results:
                break

    return results


def extract_symbols(filepath: str, content: str | None = None) -> list[dict[str, Any]]:
    """使用 tree-sitter 提取代码符号（函数/类/方法定义）。

    Args:
        filepath: 文件路径（用于推断语言）
        content: 文件内容，None 则从文件读取

    Returns:
        符号列表，每项含 name/type/start_line/end_line
    """
    if not detect_tree_sitter():
        return []

    lang = get_language_from_extension(filepath)
    if lang == "unknown":
        return []

    if content is None:
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

    try:
        from tree_sitter_languages import get_parser
        parser = get_parser(lang)
        tree = parser.parse(content.encode("utf-8"))
    except (OSError, RuntimeError, ValueError):
        logger.debug(f"tree-sitter 解析失败: {lang}", exc_info=True)
        return []

    symbols: list[dict[str, Any]] = []
    _walk_tree(tree.root_node, content, symbols)
    return symbols


def _walk_tree(node, content: str, symbols: list, depth: int = 0) -> None:
    """递归遍历 AST 提取符号定义。"""
    # 定义类型的节点
    symbol_types = {
        "function_definition": "function",
        "class_definition": "class",
        "method_definition": "method",
        "decorator_definition": "decorator",
        "function_declaration": "function",
        "class_declaration": "class",
        "method_declaration": "method",
        "export_statement": "export",
        "function_item": "function",
        "struct_item": "struct",
        "impl_item": "impl",
        "enum_item": "enum",
        "trait_item": "trait",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
    }

    node_type = node.type
    if node_type in symbol_types:
        # 尝试提取名称
        name = _extract_name(node, content)
        if name:
            symbols.append({
                "name": name,
                "type": symbol_types[node_type],
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
            })

    # 递归子节点
    if depth < 5:  # 限制递归深度
        for child in node.children:
            _walk_tree(child, content, symbols, depth + 1)


def _extract_name(node, content: str) -> str:
    """从 AST 节点提取符号名称。"""
    # 尝试从 identifier/name 子节点提取
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier", "type_identifier"):
            start = child.start_byte
            end = child.end_byte
            return content[start:end].strip()

    # 回退：从行文本提取
    lines = content.split("\n")
    if node.start_point[0] < len(lines):
        line = lines[node.start_point[0]]
        # 简单提取 def/class/function 后的名称
        import re
        match = re.search(r"(?:def|class|function|fn|func|func\s+)\s+(\w+)", line)
        if match:
            return match.group(1)
    return ""


def get_code_intel_status() -> dict[str, Any]:
    """获取代码智能工具状态。"""
    return {
        "ripgrep": {
            "available": detect_ripgrep(),
            "path": shutil.which("rg") or "",
        },
        "tree_sitter": {
            "available": detect_tree_sitter(),
        },
        "prism_js": {
            "available": True,  # CDN 资源，始终可用
        },
    }

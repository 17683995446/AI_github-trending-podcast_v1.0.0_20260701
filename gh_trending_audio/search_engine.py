"""全文搜索引擎（阶段13: 跨项目内容搜索）。

使用倒排索引实现跨所有已生成 Markdown 文档的全文搜索，
支持中文分词、模糊匹配、高亮显示和搜索排序。

核心功能：
    - ``build_index()``    → 构建搜索索引
    - ``search()``         → 执行全文搜索
    - ``get_search_suggestions()`` → 搜索建议

设计原则：
    - 第一性原理：搜索 = 分词 + 倒排索引 + 排序
    - 零依赖：纯 Python 标准库实现，不依赖 whoosh/elasticsearch
    - 增量更新：索引可持久化到磁盘，避免每次重建
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .project_scanner import scan_projects

logger = get_logger(__name__)

# 索引文件存储路径
_INDEX_DIR = os.path.expanduser("~/.cache/gh_trending_audio/search_index")

# 中文分词：按标点/空格/中英文边界切分，再对中文按2-3字组合
_TOKEN_PATTERN = re.compile(
    r"[a-zA-Z_][a-zA-Z0-9_]*"  # 英文/代码标识符
    r"|[0-9]+"  # 数字
    r"|[\u4e00-\u9fff]+"  # 中文连续字符
)


@dataclass
class SearchDocument:
    """搜索文档：一个可被搜索的内容单元。"""
    doc_id: str  # "dir_name/proj_name"
    title: str
    language: str
    content: str
    path: str  # 项目路径


@dataclass
class SearchResult:
    """搜索结果。"""
    doc_id: str
    title: str
    language: str
    score: float
    snippet: str  # 高亮片段
    path: str


@dataclass
class SearchIndex:
    """倒排索引。"""
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    inverted: dict[str, dict[str, int]] = field(default_factory=dict)  # term -> {doc_id: frequency}
    doc_count: int = 0
    avg_doc_length: float = 0.0


def _tokenize(text: str) -> list[str]:
    """中文/英文分词。

    策略：
        1. 英文/代码标识符整体保留
        2. 数字整体保留
        3. 中文按2-gram切分（适合短文本搜索）
    """
    tokens: list[str] = []
    for match in _TOKEN_PATTERN.finditer(text.lower()):
        token = match.group()
        if "\u4e00" <= token[0] <= "\u9fff":
            # 中文：生成 2-gram
            if len(token) <= 2:
                tokens.append(token)
            else:
                for i in range(len(token) - 1):
                    tokens.append(token[i:i+2])
                # 也保留完整词
                if len(token) <= 6:
                    tokens.append(token)
        else:
            tokens.append(token)
    return tokens


def _generate_snippet(content: str, query_terms: list[str], max_length: int = 200) -> str:
    """生成高亮搜索片段。"""
    if not content or not query_terms:
        return content[:max_length] + ("..." if len(content) > max_length else "")

    # 找到第一个匹配位置
    lower_content = content.lower()
    best_pos = 0
    best_score = 0

    for term in query_terms:
        pos = lower_content.find(term.lower())
        if pos >= 0:
            # 优先选择匹配多词的位置
            score = sum(1 for t in query_terms if t.lower() in lower_content[pos:pos+max_length])
            if score > best_score:
                best_score = score
                best_pos = max(0, pos - 50)  # 匹配前50字符开始

    snippet = content[best_pos:best_pos + max_length]
    if best_pos > 0:
        snippet = "..." + snippet
    if best_pos + max_length < len(content):
        snippet = snippet + "..."

    # 高亮匹配词
    for term in query_terms:
        snippet = re.sub(
            f"({re.escape(term)})",
            r"<mark>\1</mark>",
            snippet,
            flags=re.IGNORECASE,
        )

    return snippet


def build_index(output_dir: Path) -> SearchIndex:
    """构建搜索索引。

    扫描所有 output_* 目录中的 Markdown 文件，
    构建倒排索引。

    Args:
        output_dir: 输出根目录

    Returns:
        SearchIndex 对象
    """
    index = SearchIndex()
    projects = scan_projects(output_dir)

    total_length = 0
    for p in projects:
        dir_name = p.get("dir", "")
        name = p.get("name", "")
        if not dir_name or not name:
            continue

        doc_id = f"{dir_name}/{name}"

        # scan_projects 不返回 md_content，需要从文件读取
        md_content = ""
        md_path = output_dir / dir_name / f"{name}.md"
        if md_path.exists():
            try:
                md_content = md_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

        if not md_content:
            continue

        # 分词
        tokens = _tokenize(md_content)
        doc_length = len(tokens)

        # 统计词频
        term_freq: dict[str, int] = {}
        for token in tokens:
            term_freq[token] = term_freq.get(token, 0) + 1

        # 添加到索引
        index.documents[doc_id] = {
            "title": name,
            "language": p.get("language", ""),
            "content": md_content,
            "path": f"/project/{dir_name}/{name}",
            "length": doc_length,
            "stars": p.get("stars", 0),
        }

        for term, freq in term_freq.items():
            if term not in index.inverted:
                index.inverted[term] = {}
            index.inverted[term][doc_id] = freq

        total_length += doc_length

    index.doc_count = len(index.documents)
    index.avg_doc_length = total_length / index.doc_count if index.doc_count > 0 else 0

    logger.info(f"搜索索引构建完成: {index.doc_count} 文档, {len(index.inverted)} 词汇, 平均长度 {index.avg_doc_length:.0f}")
    return index


def search(
    index: SearchIndex,
    query: str,
    max_results: int = 20,
) -> list[SearchResult]:
    """执行全文搜索。

    使用 BM25 算法排序结果。

    Args:
        index: 搜索索引
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        SearchResult 列表，按相关性排序
    """
    if not query.strip() or not index.documents:
        return []

    # 分词
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    # BM25 参数
    k1 = 1.5
    b = 0.75

    # 计算每个文档的得分
    scores: dict[str, float] = {}

    for term in query_terms:
        postings = index.inverted.get(term)
        if not postings:
            continue

        # IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        df = len(postings)
        idf = math.log((index.doc_count - df + 0.5) / (df + 0.5) + 1)

        for doc_id, freq in postings.items():
            doc = index.documents.get(doc_id)
            if not doc:
                continue

            # BM25 得分
            tf_component = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * doc["length"] / index.avg_doc_length))
            score = idf * tf_component

            scores[doc_id] = scores.get(doc_id, 0) + score

    # 排序并生成结果
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_results]

    results: list[SearchResult] = []
    for doc_id, score in ranked:
        doc = index.documents[doc_id]
        snippet = _generate_snippet(doc["content"], query_terms)
        results.append(SearchResult(
            doc_id=doc_id,
            title=doc["title"],
            language=doc["language"],
            score=round(score, 4),
            snippet=snippet,
            path=doc["path"],
        ))

    return results


def get_search_suggestions(index: SearchIndex, prefix: str, max_suggestions: int = 10) -> list[str]:
    """获取搜索建议（自动补全）。

    Args:
        index: 搜索索引
        prefix: 用户输入的前缀
        max_suggestions: 最大建议数

    Returns:
        建议词列表
    """
    if not prefix.strip():
        return []

    prefix_lower = prefix.lower()
    suggestions: list[tuple[str, int]] = []

    for term in index.inverted:
        if term.startswith(prefix_lower):
            # 建议按文档频率排序
            doc_freq = len(index.inverted[term])
            suggestions.append((term, doc_freq))

    suggestions.sort(key=lambda x: x[1], reverse=True)
    return [term for term, _ in suggestions[:max_suggestions]]


def save_index(index: SearchIndex, path: str = _INDEX_DIR) -> None:
    """持久化搜索索引到磁盘。"""
    os.makedirs(path, exist_ok=True)
    index_file = os.path.join(path, "index.json")

    # 序列化（不保存完整内容，只保存元数据+倒排索引）
    data = {
        "documents": {
            doc_id: {
                "title": doc["title"],
                "language": doc["language"],
                "path": doc["path"],
                "length": doc["length"],
                "stars": doc.get("stars", 0),
            }
            for doc_id, doc in index.documents.items()
        },
        "inverted": index.inverted,
        "doc_count": index.doc_count,
        "avg_doc_length": index.avg_doc_length,
    }

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def load_index(path: str = _INDEX_DIR) -> SearchIndex | None:
    """从磁盘加载搜索索引。"""
    index_file = os.path.join(path, "index.json")
    if not os.path.exists(index_file):
        return None

    try:
        with open(index_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        index = SearchIndex()
        index.documents = data["documents"]
        index.inverted = data["inverted"]
        index.doc_count = data["doc_count"]
        index.avg_doc_length = data["avg_doc_length"]
        return index
    except (OSError, ValueError, TypeError):
        logger.warning("加载搜索索引失败", exc_info=True)
        return None

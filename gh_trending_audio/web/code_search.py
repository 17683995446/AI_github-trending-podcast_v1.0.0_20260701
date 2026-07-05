"""兼容垫片：代码搜索逻辑已上移到 ``gh_trending_audio.code_search``。

阶段5 拆分时该模块位于 ``web`` 子包；现已将其上移到核心业务层
``gh_trending_audio.code_search``，本文件仅作为向后兼容的重新导出层，
现有 ``from .code_search import xxx`` / ``from ..code_search import xxx``
调用无需修改。新代码请直接从 ``gh_trending_audio.code_search`` 导入。
"""

from __future__ import annotations

from ..code_search import (  # noqa: F401
    CodeSearchUnavailable,
    _CodeSearchUnavailable,
    normalize_repo_slug,
    github_api_get,
    github_code_search,
    ext_matches_language,
    classify_line,
    regex_search_in_xml,
    local_code_search,
)

__all__ = [
    "CodeSearchUnavailable",
    "_CodeSearchUnavailable",
    "normalize_repo_slug",
    "github_api_get",
    "github_code_search",
    "ext_matches_language",
    "classify_line",
    "regex_search_in_xml",
    "local_code_search",
]

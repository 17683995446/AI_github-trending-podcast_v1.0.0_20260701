"""API 请求处理器（兼容垫片）。

此模块已拆分为 ``gh_trending_audio.web.handlers`` 包（阶段3: 按领域模块化）。
本文件仅保持向后兼容，re-export handlers 包的所有公共函数。

新的代码应直接从 ``gh_trending_audio.web.handlers`` 导入。
"""

# 公共 API（通过 __all__ 导出）
from .handlers import *  # noqa: F401, F403
from .handlers import __all__  # noqa: F401

# 私有/共享符号（不被 * 导出，需显式 re-export 以保持向后兼容）
from .handlers._common import (  # noqa: F401
    send_json,
    send_xml,
    send_file_download,
    build_repo_from_md,
    get_project_detail,
    scan_projects,
    logger,
    _FILETREE_CACHE,
    _FILE_CONTENT_CACHE,
)

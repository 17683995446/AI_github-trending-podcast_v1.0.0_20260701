"""路由分发器（兼容垫片）。

此模块已由 ``gh_trending_audio.web.route_table`` 取代（阶段5: 声明式路由系统）。
本文件仅保持向后兼容，re-export 声明式路由表的公共接口。

新的代码应直接从 ``gh_trending_audio.web.route_table`` 导入。
"""

# 声明式路由表驱动（阶段5: 替代 if/elif 链）
from .route_table import (  # noqa: F401
    route_get,
    route_post,
    route_delete,
    RouteEntry,
    list_routes,
    add_route,
    OUTPUT_DIR,
    # 向后兼容：部分测试通过 routes 垫片显式访问该私有函数，
    # 故保留导入但不纳入下方 __all__（不通过 * 导出）。
    _parse_path_parts,
)

__all__ = [
    "route_get",
    "route_post",
    "route_delete",
    "RouteEntry",
    "list_routes",
    "add_route",
    "OUTPUT_DIR",
]

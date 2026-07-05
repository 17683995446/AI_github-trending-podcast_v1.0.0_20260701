"""阶段5: 声明式路由系统 验证测试。"""

import pytest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试：路由表结构
# ═══════════════════════════════════════════════════════════════════

class TestRouteTableStructure:
    """验证声明式路由表结构完整性。"""

    def test_route_table_module_exists(self):
        """route_table 模块应存在。"""
        from gh_trending_audio.web import route_table
        assert route_table is not None

    def test_route_entry_dataclass_exists(self):
        """RouteEntry 数据类应存在。"""
        from gh_trending_audio.web.route_table import RouteEntry
        assert RouteEntry is not None

    def test_get_routes_list_exists(self):
        """_GET_ROUTES 路由表应存在且非空。"""
        from gh_trending_audio.web.route_table import _GET_ROUTES
        assert isinstance(_GET_ROUTES, list)
        assert len(_GET_ROUTES) > 10

    def test_post_routes_list_exists(self):
        """_POST_ROUTES 路由表应存在且非空。"""
        from gh_trending_audio.web.route_table import _POST_ROUTES
        assert isinstance(_POST_ROUTES, list)
        assert len(_POST_ROUTES) > 0

    def test_delete_routes_list_exists(self):
        """_DELETE_ROUTES 路由表应存在且非空。"""
        from gh_trending_audio.web.route_table import _DELETE_ROUTES
        assert isinstance(_DELETE_ROUTES, list)
        assert len(_DELETE_ROUTES) > 0

    def test_routes_is_shim(self):
        """routes.py 应为兼容垫片。"""
        import inspect
        from gh_trending_audio.web import routes
        source = inspect.getsource(routes)
        assert "route_table" in source
        assert "re-export" in source.lower() or "兼容" in source


# ═══════════════════════════════════════════════════════════════════
# RouteEntry 功能验证
# ═══════════════════════════════════════════════════════════════════

class TestRouteEntry:
    """RouteEntry 数据类功能测试。"""

    def test_exact_match(self):
        """精确匹配路由应正确匹配。"""
        from gh_trending_audio.web.route_table import RouteEntry
        entry = RouteEntry(
            pattern="/api/projects",
            handler=lambda *a: None,
            args=lambda *a: (),
        )
        matched, parts = entry.matches("/api/projects")
        assert matched is True
        assert parts == []

    def test_exact_match_no_match(self):
        """精确匹配路由不应匹配其他路径。"""
        from gh_trending_audio.web.route_table import RouteEntry
        entry = RouteEntry(
            pattern="/api/projects",
            handler=lambda *a: None,
            args=lambda *a: (),
        )
        matched, parts = entry.matches("/api/stats")
        assert matched is False

    def test_prefix_match(self):
        """前缀匹配路由应正确匹配。"""
        from gh_trending_audio.web.route_table import RouteEntry
        entry = RouteEntry(
            pattern="/api/project/*",
            handler=lambda *a: None,
            args=lambda *a: (),
        )
        matched, parts = entry.matches("/api/project/owner/repo")
        assert matched is True
        assert len(parts) == 2

    def test_prefix_match_no_match(self):
        """前缀匹配路由不应匹配不相关路径。"""
        from gh_trending_audio.web.route_table import RouteEntry
        entry = RouteEntry(
            pattern="/api/project/*",
            handler=lambda *a: None,
            args=lambda *a: (),
        )
        matched, parts = entry.matches("/api/stats")
        assert matched is False

    def test_is_prefix_property(self):
        """is_prefix 属性应正确识别。"""
        from gh_trending_audio.web.route_table import RouteEntry
        exact = RouteEntry("/api/projects", lambda *a: None, lambda *a: ())
        prefix = RouteEntry("/api/project/*", lambda *a: None, lambda *a: ())
        assert exact.is_prefix is False
        assert prefix.is_prefix is True


# ═══════════════════════════════════════════════════════════════════
# 路由分发器验证
# ═══════════════════════════════════════════════════════════════════

class TestRouteDispatch:
    """路由分发器功能测试。"""

    def test_route_get_function_exists(self):
        """route_get 函数应存在。"""
        from gh_trending_audio.web.route_table import route_get
        assert callable(route_get)

    def test_route_post_function_exists(self):
        """route_post 函数应存在。"""
        from gh_trending_audio.web.route_table import route_post
        assert callable(route_post)

    def test_route_delete_function_exists(self):
        """route_delete 函数应存在。"""
        from gh_trending_audio.web.route_table import route_delete
        assert callable(route_delete)

    def test_dispatch_returns_true_on_match(self):
        """分发器应在匹配时返回 True。"""
        from gh_trending_audio.web.route_table import _dispatch, _GET_ROUTES
        from unittest.mock import MagicMock

        handler = MagicMock()
        parsed = MagicMock()
        parsed.path = "/api/projects"
        parsed.query = ""

        result = _dispatch(_GET_ROUTES, handler, parsed)
        assert result is True

    def test_dispatch_returns_false_on_no_match(self):
        """分发器应在无匹配时返回 False。"""
        from gh_trending_audio.web.route_table import _dispatch, _GET_ROUTES
        from unittest.mock import MagicMock

        handler = MagicMock()
        parsed = MagicMock()
        parsed.path = "/nonexistent/path/12345"
        parsed.query = ""

        result = _dispatch(_GET_ROUTES, handler, parsed)
        assert result is False


# ═══════════════════════════════════════════════════════════════════
# 路由完整性验证
# ═══════════════════════════════════════════════════════════════════

class TestRouteCompleteness:
    """验证所有必要路由都已注册。"""

    def test_get_routes_include_all_essential(self):
        """GET 路由表应包含所有核心端点。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        patterns = [r["pattern"] for r in routes]

        essential = [
            "/", "/api/projects", "/api/stats", "/api/status",
            "/api/search", "/feed.xml", "/manifest.json", "/sw.js",
            "/api/system-backends", "/api/preferences-schema",
        ]
        for ep in essential:
            assert any(ep in p for p in patterns), f"缺少路由: {ep}"

    def test_post_routes_include_all_essential(self):
        """POST 路由表应包含所有核心端点。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("POST")
        patterns = [r["pattern"] for r in routes]

        essential = ["/api/run", "/api/compare", "/api/ask", "/api/onboarding"]
        for ep in essential:
            assert any(ep in p for p in patterns), f"缺少POST路由: {ep}"

    def test_delete_routes_exist(self):
        """DELETE 路由表应存在。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("DELETE")
        assert len(routes) > 0

    def test_prefix_routes_exist(self):
        """应包含前缀匹配路由。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        prefix_routes = [r for r in routes if r["type"] == "prefix"]
        assert len(prefix_routes) >= 5, "应至少有 5 个前缀路由"

    def test_no_if_elif_chain_in_route_get(self):
        """route_get 函数不应包含 if/elif 路由链。"""
        import inspect
        from gh_trending_audio.web.route_table import route_get
        source = inspect.getsource(route_get)
        # route_get 应通过 _dispatch 分发，不应有大量 elif
        assert "_dispatch" in source
        assert source.count("elif") == 0, "route_get 不应包含 elif 链"


# ═══════════════════════════════════════════════════════════════════
# 可扩展性验证
# ═══════════════════════════════════════════════════════════════════

class TestRouteExtensibility:
    """验证路由系统的可扩展性。"""

    def test_list_routes_function_exists(self):
        """list_routes 函数应存在。"""
        from gh_trending_audio.web.route_table import list_routes
        assert callable(list_routes)

    def test_add_route_function_exists(self):
        """add_route 函数应存在（运行时扩展）。"""
        from gh_trending_audio.web.route_table import add_route
        assert callable(add_route)

    def test_list_routes_returns_route_info(self):
        """list_routes 应返回路由信息字典列表。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert isinstance(routes, list)
        assert len(routes) > 0
        for r in routes:
            assert "pattern" in r
            assert "type" in r
            assert "handler" in r

    def test_add_route_adds_to_table(self):
        """add_route 应成功添加新路由到表。"""
        from gh_trending_audio.web.route_table import add_route, list_routes, _GET_ROUTES

        original_count = len(_GET_ROUTES)
        add_route("GET", "/api/test-custom-route", lambda *a: None)
        assert len(_GET_ROUTES) == original_count + 1

        routes = list_routes("GET")
        assert any(r["pattern"] == "/api/test-custom-route" for r in routes)

        # 清理：移除添加的路由
        _GET_ROUTES.pop()

    def test_add_route_rejects_invalid_method(self):
        """add_route 应拒绝不支持的 HTTP 方法。"""
        from gh_trending_audio.web.route_table import add_route
        with pytest.raises(ValueError, match="不支持"):
            add_route("PATCH", "/test", lambda *a: None)


# ═══════════════════════════════════════════════════════════════════
# 兼容性验证
# ═══════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """验证 routes.py 兼容垫片正确。"""

    def test_route_get_accessible_from_routes(self):
        """route_get 应可通过 routes 模块访问。"""
        from gh_trending_audio.web.routes import route_get
        assert callable(route_get)

    def test_route_post_accessible_from_routes(self):
        """route_post 应可通过 routes 模块访问。"""
        from gh_trending_audio.web.routes import route_post
        assert callable(route_post)

    def test_route_delete_accessible_from_routes(self):
        """route_delete 应可通过 routes 模块访问。"""
        from gh_trending_audio.web.routes import route_delete
        assert callable(route_delete)

    def test_output_dir_accessible_from_routes(self):
        """OUTPUT_DIR 应可通过 routes 模块访问。"""
        from gh_trending_audio.web.routes import OUTPUT_DIR
        assert OUTPUT_DIR is not None

    def test_parse_path_parts_accessible(self):
        """_parse_path_parts 应可通过 routes 模块访问。"""
        from gh_trending_audio.web.routes import _parse_path_parts
        assert callable(_parse_path_parts)

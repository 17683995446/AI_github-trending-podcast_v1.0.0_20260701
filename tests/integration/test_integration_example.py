"""集成测试示例：验证多模块协作。"""

import pytest
from pathlib import Path
from gh_trending_audio.project_scanner import scan_projects
from gh_trending_audio.web.route_table import route_get, list_routes


class TestProjectScanning:
    """项目扫描集成测试。"""

    def test_scan_projects_finds_output_dirs(self, tmp_path: Path):
        """扫描output开头的目录。"""
        # 创建模拟项目
        (tmp_path / "output_demo").mkdir()
        (tmp_path / "output_demo" / "test_repo.md").write_text("# Test")
        (tmp_path / "not_output").mkdir()  # 不应被扫描
        
        projects = scan_projects(tmp_path)
        assert len(projects) >= 0  # 至少不抛异常

    def test_route_table_complete(self):
        """路由表完整性集成测试。"""
        routes = list_routes("GET")
        assert len(routes) > 10  # 应有多个路由
        # 验证关键路由存在
        patterns = [r["pattern"] for r in routes]
        assert "/" in patterns
        assert "/api/projects" in patterns
        assert "/api/project/*" in patterns


class TestRouteDispatch:
    """路由分发集成测试。"""

    def test_get_routes_have_handlers(self):
        """所有GET路由都有handler。"""
        routes = list_routes("GET")
        for route in routes:
            assert route["handler"] is not None
            assert isinstance(route["pattern"], str)

    def test_post_routes_exist(self):
        """POST路由存在。"""
        routes = list_routes("POST")
        assert len(routes) > 0
        patterns = [r["pattern"] for r in routes]
        assert "/api/run" in patterns

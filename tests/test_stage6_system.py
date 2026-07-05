"""阶段6：系统测试 — Web服务器端到端验证。

启动真实的HTTP服务器实例，验证完整的请求-响应链路，
包括页面渲染、API响应、静态资源、错误处理等。
标记为 @pytest.mark.system，可通过 -m "not system" 排除。
"""

import json
import pytest
import urllib.request
import urllib.error
from http.server import HTTPServer
from pathlib import Path
from threading import Thread

from gh_trending_audio.web.server import create_server


@pytest.fixture(scope="module")
def live_server():
    """启动真实HTTP服务器，返回基础URL。"""
    server = create_server(port=0)  # 端口0=自动分配
    # 获取实际分配的端口
    actual_port = server.server_address[1]
    base_url = f"http://localhost:{actual_port}"
    
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    yield base_url
    
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _fetch(url: str) -> tuple[int, bytes, dict]:
    """发送GET请求，返回 (status_code, body, headers)。"""
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


@pytest.mark.system
class TestWebServerE2E:
    """Web服务器端到端测试。"""

    def test_dashboard_page_loads(self, live_server: str):
        """仪表盘页面完整加载。"""
        status, body, _ = _fetch(f"{live_server}/")
        assert status == 200
        assert b"GitHub Trending Audio" in body
        assert b"<html" in body

    def test_dashboard_route_alias(self, live_server: str):
        """/dashboard 路由别名。"""
        status, body, _ = _fetch(f"{live_server}/dashboard")
        assert status == 200
        assert b"GitHub Trending Audio" in body

    def test_api_projects_returns_json(self, live_server: str):
        """项目列表API返回JSON。"""
        status, body, _ = _fetch(f"{live_server}/api/projects")
        assert status == 200
        data = json.loads(body)
        # 实际响应结构：{"projects": [...], "total": N}
        assert isinstance(data, dict)
        assert "projects" in data
        projects = data["projects"]
        assert isinstance(projects, list)
        # 至少有项目（如果demo数据存在）
        if len(projects) > 0:
            assert "name" in projects[0]

    def test_api_stats_returns_json(self, live_server: str):
        """统计API返回JSON。"""
        status, body, _ = _fetch(f"{live_server}/api/stats")
        assert status == 200
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_api_status_returns_json(self, live_server: str):
        """状态API返回JSON。"""
        status, body, _ = _fetch(f"{live_server}/api/status")
        assert status == 200
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_manifest_json(self, live_server: str):
        """PWA manifest.json 可访问。"""
        status, body, headers = _fetch(f"{live_server}/manifest.json")
        assert status == 200

    def test_feed_xml(self, live_server: str):
        """RSS feed.xml 可访问。"""
        status, body, _ = _fetch(f"{live_server}/feed.xml")
        assert status == 200
        assert b"<?xml" in body or b"<rss" in body

    def test_opml_xml(self, live_server: str):
        """OPML opml.xml 可访问。"""
        status, body, _ = _fetch(f"{live_server}/opml.xml")
        assert status == 200

    def test_404_for_unknown_route(self, live_server: str):
        """未知路由返回404。"""
        status, _, _ = _fetch(f"{live_server}/nonexistent-route-12345")
        assert status == 404

    def test_api_search_empty_query(self, live_server: str):
        """搜索API空查询不崩溃。"""
        status, body, _ = _fetch(f"{live_server}/api/search?q=")
        # 空查询返回400（参数错误）属优雅处理，不应崩溃为500
        assert status in (200, 400)
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_player_page_loads(self, live_server: str):
        """播放器页面加载。"""
        status, body, _ = _fetch(f"{live_server}/player")
        assert status == 200
        assert b"<html" in body

    def test_api_feed_stats(self, live_server: str):
        """Feed统计API。"""
        status, body, _ = _fetch(f"{live_server}/api/feed-stats")
        assert status == 200
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_api_system_backends(self, live_server: str):
        """系统后端API。"""
        status, body, _ = _fetch(f"{live_server}/api/system-backends")
        assert status == 200
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_api_preferences_schema(self, live_server: str):
        """偏好设置schema API。"""
        status, body, _ = _fetch(f"{live_server}/api/preferences-schema")
        assert status == 200

    def test_api_code_intel_status(self, live_server: str):
        """代码智能状态API。"""
        status, body, _ = _fetch(f"{live_server}/api/code-intel-status")
        assert status == 200

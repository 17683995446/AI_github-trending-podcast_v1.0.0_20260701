"""阶段11: PWA 离线支持 测试。"""

import pytest
import json


class TestPWAUnit:
    """PWA 模块单元测试。"""

    def test_get_manifest_returns_json(self):
        from gh_trending_audio.web.pwa import get_manifest
        manifest = get_manifest()
        data = json.loads(manifest)
        assert data["name"] == "GitHub Trending Audio"
        assert data["short_name"] == "GH Audio"
        assert data["display"] == "standalone"
        assert data["start_url"] == "/"
        assert "icons" in data
        assert len(data["icons"]) >= 1

    def test_manifest_has_theme_color(self):
        from gh_trending_audio.web.pwa import get_manifest
        data = json.loads(get_manifest())
        assert "theme_color" in data
        assert "background_color" in data

    def test_manifest_has_icons(self):
        from gh_trending_audio.web.pwa import get_manifest
        data = json.loads(get_manifest())
        assert len(data["icons"]) >= 1
        for icon in data["icons"]:
            assert "src" in icon
            assert "sizes" in icon
            assert "type" in icon

    def test_get_service_worker_returns_js(self):
        from gh_trending_audio.web.pwa import get_service_worker
        sw = get_service_worker()
        assert "CACHE_NAME" in sw
        assert "install" in sw
        assert "activate" in sw
        assert "fetch" in sw
        assert "caches" in sw

    def test_service_worker_has_cache_strategies(self):
        from gh_trending_audio.web.pwa import get_service_worker
        sw = get_service_worker()
        # 网络优先策略
        assert "fetch(event.request)" in sw
        # 缓存优先策略
        assert "caches.match" in sw
        # 预缓存
        assert "addAll" in sw or "cache.addAll" in sw

    def test_get_pwa_meta_tags(self):
        from gh_trending_audio.web.pwa import get_pwa_meta_tags
        tags = get_pwa_meta_tags()
        assert 'rel="manifest"' in tags
        assert 'name="theme-color"' in tags
        assert 'apple-mobile-web-app-capable' in tags

    def test_get_sw_registration_script(self):
        from gh_trending_audio.web.pwa import get_sw_registration_script
        script = get_sw_registration_script()
        assert "serviceWorker" in script
        assert "register" in script


class TestPWAIntegration:
    """PWA 集成测试。"""

    def test_manifest_route_exists(self):
        import inspect
        from gh_trending_audio.web import route_table
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/manifest.json" in r["pattern"] for r in routes)
        source = inspect.getsource(route_table)
        assert "get_manifest" in source

    def test_sw_route_exists(self):
        import inspect
        from gh_trending_audio.web import route_table
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/sw.js" in r["pattern"] for r in routes)
        source = inspect.getsource(route_table)
        assert "get_service_worker" in source

    def test_icon_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/icon-512.jpg" in r["pattern"] for r in routes)

    def test_dashboard_has_manifest_link(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'rel="manifest"' in DASHBOARD_HTML
        assert "/manifest.json" in DASHBOARD_HTML

    def test_dashboard_has_theme_color(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'name="theme-color"' in DASHBOARD_HTML

    def test_dashboard_has_sw_registration(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "serviceWorker" in DASHBOARD_HTML
        assert "/sw.js" in DASHBOARD_HTML

    def test_player_has_manifest_link(self):
        from gh_trending_audio.web.templates import PLAYER_HTML
        assert 'rel="manifest"' in PLAYER_HTML

    def test_project_has_manifest_link(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert 'rel="manifest"' in PROJECT_HTML

    def test_player_has_sw_registration(self):
        from gh_trending_audio.web.templates import PLAYER_HTML
        assert "serviceWorker" in PLAYER_HTML

    def test_project_has_sw_registration(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "serviceWorker" in PROJECT_HTML

    def test_dashboard_has_apple_touch_icon(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "apple-touch-icon" in DASHBOARD_HTML

    def test_icon_file_exists(self):
        from pathlib import Path
        icon = Path("/workspace/gh_trending_audio/gh_trending_audio/web/static/icon-512.jpg")
        assert icon.exists()
        assert icon.stat().st_size > 0

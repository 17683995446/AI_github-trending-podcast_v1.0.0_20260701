"""阶段15-17: 用户偏好 + 收藏系统 + 批量操作 测试。"""

import pytest


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestUserPrefsUnit:
    """用户偏好系统单元测试。"""

    def test_default_preferences_exists(self):
        from gh_trending_audio.user_prefs import DEFAULT_PREFERENCES
        assert "theme" in DEFAULT_PREFERENCES
        assert "playback_rate" in DEFAULT_PREFERENCES
        assert "volume" in DEFAULT_PREFERENCES
        assert "favorites" in DEFAULT_PREFERENCES
        assert "recent_projects" in DEFAULT_PREFERENCES

    def test_get_preferences_schema(self):
        from gh_trending_audio.user_prefs import get_preferences_schema
        schema = get_preferences_schema()
        assert len(schema) > 0
        keys = [s["key"] for s in schema]
        assert "theme" in keys
        assert "playback_rate" in keys

    def test_merge_preferences_empty(self):
        from gh_trending_audio.user_prefs import merge_preferences, DEFAULT_PREFERENCES
        merged = merge_preferences({})
        assert merged == DEFAULT_PREFERENCES

    def test_merge_preferences_partial(self):
        from gh_trending_audio.user_prefs import merge_preferences
        merged = merge_preferences({"theme": "light", "volume": 0.5})
        assert merged["theme"] == "light"
        assert merged["volume"] == 0.5
        assert merged["playback_rate"] == 1.0  # 默认值

    def test_merge_preferences_ignores_unknown(self):
        from gh_trending_audio.user_prefs import merge_preferences
        merged = merge_preferences({"unknown_key": "value"})
        assert "unknown_key" not in merged

    def test_toggle_favorite_add(self):
        from gh_trending_audio.user_prefs import toggle_favorite
        result = toggle_favorite([], "project1")
        assert "project1" in result

    def test_toggle_favorite_remove(self):
        from gh_trending_audio.user_prefs import toggle_favorite
        result = toggle_favorite(["project1", "project2"], "project1")
        assert "project1" not in result
        assert "project2" in result

    def test_add_recent_project(self):
        from gh_trending_audio.user_prefs import add_recent_project
        result = add_recent_project(["a", "b"], "c")
        assert result[0] == "c"
        assert "a" in result

    def test_add_recent_project_dedup(self):
        from gh_trending_audio.user_prefs import add_recent_project
        result = add_recent_project(["a", "b", "c"], "a")
        assert result[0] == "a"
        assert result.count("a") == 1

    def test_add_recent_project_limit(self):
        from gh_trending_audio.user_prefs import add_recent_project
        result = add_recent_project(list(range(10)), "new", max_items=5)
        assert len(result) == 5
        assert result[0] == "new"


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestStage15To17Integration:
    """阶段15-17 API 和 UI 集成测试。"""

    def test_preferences_schema_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/preferences-schema" in r["pattern"] for r in routes)
        assert any("serve_preferences_schema" in r["handler"] for r in routes)

    def test_batch_export_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/batch-export" in r["pattern"] for r in routes)
        assert any("serve_batch_export" in r["handler"] for r in routes)

    def test_preferences_schema_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_preferences_schema
        assert callable(serve_preferences_schema)

    def test_batch_export_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_batch_export
        assert callable(serve_batch_export)

    def test_dashboard_has_prefs_js(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "loadUserPrefs" in DASHBOARD_HTML
        assert "saveUserPref" in DASHBOARD_HTML
        assert "localStorage" in DASHBOARD_HTML

    def test_dashboard_has_favorites_js(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "toggleFavorite" in DASHBOARD_HTML
        assert "getFavorites" in DASHBOARD_HTML
        assert "isFavorite" in DASHBOARD_HTML
        assert "gh_audio_favorites" in DASHBOARD_HTML

    def test_dashboard_has_batch_export_js(self):
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "batchExportAll" in DASHBOARD_HTML
        assert "/api/batch-export" in DASHBOARD_HTML

    def test_lazy_export_user_prefs(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "get_preferences_schema")
        assert hasattr(gh_trending_audio, "merge_preferences")
        assert hasattr(gh_trending_audio, "toggle_favorite")
        assert hasattr(gh_trending_audio, "DEFAULT_PREFERENCES")

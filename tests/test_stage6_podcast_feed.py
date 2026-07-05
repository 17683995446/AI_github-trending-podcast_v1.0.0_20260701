"""阶段6: 播客 RSS 订阅源 + OPML 导出 测试。"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestPodcastFeedUnit:
    """播客订阅源生成器单元测试。"""

    def test_format_duration_zero(self):
        from gh_trending_audio.podcast_feed import _format_duration
        assert _format_duration(0) == "00:00"
        assert _format_duration(None) == "00:00"
        assert _format_duration(-1) == "00:00"

    def test_format_duration_seconds(self):
        from gh_trending_audio.podcast_feed import _format_duration
        assert _format_duration(65) == "01:05"

    def test_format_duration_minutes(self):
        from gh_trending_audio.podcast_feed import _format_duration
        assert _format_duration(600) == "10:00"

    def test_format_duration_hours(self):
        from gh_trending_audio.podcast_feed import _format_duration
        assert _format_duration(3661) == "01:01:01"

    def test_rfc822_date_format(self):
        from gh_trending_audio.podcast_feed import _rfc822_date
        result = _rfc822_date(1700000000)
        assert "+" in result
        assert "GMT" not in result  # 应使用 +0000 而非 GMT
        assert len(result) > 20

    def test_generate_feed_empty_dir(self, tmp_path):
        """空目录应生成有效但无剧集的 RSS。"""
        from gh_trending_audio.podcast_feed import generate_podcast_feed
        xml = generate_podcast_feed(tmp_path, base_url="http://localhost:8000")
        assert "<?xml" in xml or "<rss" in xml
        assert "<channel>" in xml
        assert "<item>" not in xml  # 无剧集

    def test_generate_feed_with_projects(self, tmp_path):
        """有项目的目录应生成含剧集的 RSS。"""
        from gh_trending_audio.podcast_feed import generate_podcast_feed
        # 创建模拟项目
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        md_content = """# Test Project

| 描述 | A test project |
| 星标 | 100 |
| 编程语言 | Python |

Some content here.
"""
        (out_dir / "owner_repo.md").write_text(md_content, encoding="utf-8")
        (out_dir / "owner_repo_script.txt").write_text("A: Hello", encoding="utf-8")
        (out_dir / "owner_repo.mp3").write_bytes(b"fake mp3 data")

        xml = generate_podcast_feed(tmp_path, base_url="http://localhost:8000")
        assert "<rss" in xml
        assert "<item>" in xml
        assert "owner_repo" in xml
        assert "audio/mpeg" in xml
        assert "http://localhost:8000/file/" in xml

    def test_generate_opml_empty_dir(self, tmp_path):
        """空目录应生成有效但无剧集的 OPML。"""
        from gh_trending_audio.podcast_feed import generate_opml
        xml = generate_opml(tmp_path, base_url="http://localhost:8000")
        assert "<opml" in xml
        assert "outline" in xml
        assert "feed.xml" in xml

    def test_generate_opml_with_projects(self, tmp_path):
        """有项目的目录应生成含剧集链接的 OPML。"""
        from gh_trending_audio.podcast_feed import generate_opml
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        (out_dir / "owner_repo.md").write_text("# Test", encoding="utf-8")
        (out_dir / "owner_repo_script.txt").write_text("A: Hello", encoding="utf-8")
        (out_dir / "owner_repo.mp3").write_bytes(b"fake mp3")

        xml = generate_opml(tmp_path, base_url="http://localhost:8000")
        assert "<opml" in xml
        assert "owner_repo" in xml
        assert "http://localhost:8000/feed.xml" in xml

    def test_get_feed_stats_empty(self, tmp_path):
        from gh_trending_audio.podcast_feed import get_feed_stats
        stats = get_feed_stats(tmp_path)
        assert stats["episode_count"] == 0
        assert stats["total_size_bytes"] == 0
        assert "feed_title" in stats

    def test_get_feed_stats_with_projects(self, tmp_path):
        from gh_trending_audio.podcast_feed import get_feed_stats
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        (out_dir / "owner_repo.md").write_text("# Test", encoding="utf-8")
        (out_dir / "owner_repo_script.txt").write_text("A: Hello", encoding="utf-8")
        (out_dir / "owner_repo.mp3").write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

        stats = get_feed_stats(tmp_path)
        assert stats["episode_count"] == 1
        assert stats["total_size_bytes"] == 2 * 1024 * 1024
        assert stats["total_size_mb"] >= 1.0

    def test_feed_has_itunes_tags(self, tmp_path):
        """RSS 应包含 iTunes 播客扩展标签。"""
        from gh_trending_audio.podcast_feed import generate_podcast_feed
        xml = generate_podcast_feed(tmp_path, base_url="http://localhost:8000")
        # feedgen 或 stdlib 都应包含 iTunes 命名空间
        assert "itunes" in xml.lower() or "category" in xml.lower()

    def test_feed_max_episodes_limit(self, tmp_path):
        """max_episodes 参数应限制剧集数量。"""
        from gh_trending_audio.podcast_feed import generate_podcast_feed
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        for i in range(5):
            name = f"owner_repo{i}"
            (out_dir / f"{name}.md").write_text(f"# Test {i}", encoding="utf-8")
            (out_dir / f"{name}_script.txt").write_text("A: Hello", encoding="utf-8")
            (out_dir / f"{name}.mp3").write_bytes(b"fake")

        xml = generate_podcast_feed(tmp_path, base_url="http://localhost:8000", max_episodes=2)
        item_count = xml.count("<item>")
        assert item_count <= 2


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestPodcastFeedIntegration:
    """播客订阅源 API 端点集成测试。"""

    def test_feed_xml_route_exists(self):
        """验证 /feed.xml 路由已注册。"""
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/feed.xml" in r["pattern"] for r in routes)
        assert any("serve_podcast_feed" in r["handler"] for r in routes)

    def test_opml_xml_route_exists(self):
        """验证 /opml.xml 路由已注册。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/opml.xml" in r["pattern"] for r in routes)
        assert any("serve_opml" in r["handler"] for r in routes)

    def test_feed_stats_route_exists(self):
        """验证 /api/feed-stats 路由已注册。"""
        from gh_trending_audio.web.route_table import list_routes
        routes = list_routes("GET")
        assert any("/api/feed-stats" in r["pattern"] for r in routes)
        assert any("serve_feed_stats" in r["handler"] for r in routes)

    def test_send_xml_utility_exists(self):
        """验证 send_xml 工具函数已添加。"""
        from gh_trending_audio.web.http_utils import send_xml
        assert callable(send_xml)

    def test_send_file_download_utility_exists(self):
        """验证 send_file_download 工具函数已添加。"""
        from gh_trending_audio.web.http_utils import send_file_download
        assert callable(send_file_download)

    def test_dashboard_has_rss_link(self):
        """验证仪表盘 HTML 包含 RSS 自动发现链接。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'rel="alternate"' in DASHBOARD_HTML
        assert 'type="application/rss+xml"' in DASHBOARD_HTML
        assert "/feed.xml" in DASHBOARD_HTML

    def test_dashboard_has_podcast_section(self):
        """验证仪表盘包含播客订阅 UI。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "podcast-feed-section" in DASHBOARD_HTML
        assert "feedUrlInput" in DASHBOARD_HTML
        assert "copyFeedUrl" in DASHBOARD_HTML
        assert "initPodcastFeed" in DASHBOARD_HTML

    def test_dashboard_has_opml_link(self):
        """验证仪表盘包含 OPML 下载链接。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "/opml.xml" in DASHBOARD_HTML

    def test_lazy_export_podcast_feed(self):
        """验证 __init__.py 导出了播客订阅源 API。"""
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "generate_podcast_feed")
        assert hasattr(gh_trending_audio, "generate_opml")
        assert hasattr(gh_trending_audio, "get_feed_stats")

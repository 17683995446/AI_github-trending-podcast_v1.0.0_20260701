"""阶段8: ECharts 数据可视化 测试。"""

import pytest


class TestEChartsVisualization:
    """ECharts 数据可视化集成测试。"""

    def test_echarts_cdn_loaded(self):
        """Dashboard 应加载 ECharts CDN。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "echarts" in DASHBOARD_HTML.lower()
        assert "cdn.jsdelivr.net" in DASHBOARD_HTML
        assert "echarts@" in DASHBOARD_HTML.lower() or "echarts/" in DASHBOARD_HTML.lower()

    def test_chart_js_removed(self):
        """Chart.js CDN 应已被移除。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "chart.js@4" not in DASHBOARD_HTML.lower()
        assert "chart.umd.min.js" not in DASHBOARD_HTML.lower()

    def test_charts_section_container(self):
        """Dashboard 应包含图表区域容器。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'id="chartsSection"' in DASHBOARD_HTML

    def test_language_pie_chart(self):
        """Dashboard 应包含语言分布饼图。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'id="langChart"' in DASHBOARD_HTML
        assert "type: 'pie'" in DASHBOARD_HTML

    def test_stars_bar_chart(self):
        """Dashboard 应包含星标对比柱状图。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'id="starsChart"' in DASHBOARD_HTML
        assert "type: 'bar'" in DASHBOARD_HTML

    def test_duration_bar_chart(self):
        """Dashboard 应包含音频时长柱状图。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert 'id="durationChart"' in DASHBOARD_HTML

    def test_echarts_init_code(self):
        """Dashboard 应包含 echarts.init 调用。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "echarts.init" in DASHBOARD_HTML
        assert "setOption" in DASHBOARD_HTML

    def test_chart_grid_layout(self):
        """图表应使用 CSS Grid 布局。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "grid-template-columns" in DASHBOARD_HTML
        assert "repeat(auto-fit" in DASHBOARD_HTML

    def test_chart_theme_colors(self):
        """图表应使用 CSS 变量适配主题。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "--text-dim" in DASHBOARD_HTML
        assert "getComputedStyle" in DASHBOARD_HTML

    def test_chart_error_handling(self):
        """图表初始化应有错误处理。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "catch" in DASHBOARD_HTML
        assert "console.error" in DASHBOARD_HTML

    def test_chart_tooltips(self):
        """图表应包含 tooltip 配置。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "tooltip" in DASHBOARD_HTML

    def test_no_old_chart_section(self):
        """旧的 langChartSection 应已移除。"""
        from gh_trending_audio.web.templates import DASHBOARD_HTML
        assert "langChartSection" not in DASHBOARD_HTML

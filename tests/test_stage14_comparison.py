"""阶段14: 项目对比增强 测试。"""

import pytest
from pathlib import Path


class TestComparisonEngineUnit:
    """项目对比引擎单元测试。"""

    def test_extract_metrics_from_md(self):
        from gh_trending_audio.comparison_engine import _extract_metrics_from_md
        md = "# My Project\n\n| 描述 | A test project |\n| 星标 | 100 |\n| 编程语言 | Python |\n"
        metrics = _extract_metrics_from_md(md)
        assert "项目名称" in metrics
        assert "编程语言" in metrics
        assert "星标" in metrics

    def test_compare_projects_basic(self, mock_output_dir):
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        assert "projects" in result
        assert len(result["projects"]) == 2
        assert "metrics" in result
        assert result["project_count"] == 2

    def test_compare_projects_single_project(self, tmp_path):
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(tmp_path, ["only_one"])
        assert "error" in result

    def test_compare_projects_not_found(self, tmp_path):
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(tmp_path, ["nonexistent1", "nonexistent2"])
        assert result["project_count"] == 2
        assert all("error" in p for p in result["projects"])

    def test_compare_projects_has_metrics(self, mock_output_dir):
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        metrics = result["metrics"]
        labels = [m["label"] for m in metrics]
        assert "GitHub 星标" in labels
        assert "编程语言" in labels
        assert "开源协议" in labels

    def test_compare_projects_highlight_diff(self, mock_output_dir):
        from gh_trending_audio.comparison_engine import compare_projects
        result = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        # 编程语言不同，应高亮
        lang_metric = next(m for m in result["metrics"] if m["label"] == "编程语言")
        assert lang_metric["is_highlighted"] is True

    def test_generate_comparison_table(self, mock_output_dir):
        from gh_trending_audio.comparison_engine import compare_projects, generate_comparison_table
        comparison = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        html = generate_comparison_table(comparison)
        assert "<table" in html
        assert "owner_repo1" in html
        assert "owner_repo2" in html

    def test_generate_comparison_table_error(self):
        from gh_trending_audio.comparison_engine import generate_comparison_table
        html = generate_comparison_table({"error": "test error"})
        assert "test error" in html

    def test_generate_comparison_table_empty(self):
        from gh_trending_audio.comparison_engine import generate_comparison_table
        html = generate_comparison_table({"projects": [], "metrics": []})
        assert "无对比数据" in html

    def test_generate_radar_data(self, mock_output_dir):
        from gh_trending_audio.comparison_engine import compare_projects, generate_radar_data
        comparison = compare_projects(mock_output_dir, ["owner_repo1", "owner_repo2"])
        radar = generate_radar_data(comparison)
        assert "indicator" in radar
        assert "series" in radar
        assert len(radar["indicator"]) == 4
        assert len(radar["series"]) == 2

    def test_generate_radar_data_empty(self):
        from gh_trending_audio.comparison_engine import generate_radar_data
        radar = generate_radar_data({"projects": []})
        assert radar == {}


class TestComparisonEngineIntegration:
    """项目对比 API 集成测试。"""

    def test_compare_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/compare-projects" in r["pattern"] for r in routes)
        assert any("serve_compare_projects" in r["handler"] for r in routes)

    def test_compare_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_compare_projects
        assert callable(serve_compare_projects)

    def test_lazy_export_comparison(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "compare_projects")
        assert hasattr(gh_trending_audio, "generate_comparison_table")
        assert hasattr(gh_trending_audio, "generate_radar_data")

"""阶段9: 多格式导出 (PDF/EPUB/JSON/ZIP) 测试。"""

import pytest
import json
import zipfile
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestExporterUnit:
    """多格式导出器单元测试。"""

    def _setup_project(self, tmp_path):
        """创建模拟项目。"""
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        (out_dir / "owner_repo.md").write_text(
            "# Test Project\n\n| 描述 | A test project |\n| 星标 | 100 |\n\nSome content here.",
            encoding="utf-8",
        )
        (out_dir / "owner_repo_script.txt").write_text("A: Hello\nB: Welcome", encoding="utf-8")
        (out_dir / "owner_repo.mp3").write_bytes(b"fake mp3 data")
        return tmp_path

    def test_export_json(self, tmp_path):
        from gh_trending_audio.exporter import export_json
        self._setup_project(tmp_path)
        data = export_json(tmp_path, "output_test", "owner_repo")
        assert data is not None
        obj = json.loads(data)
        assert obj["name"] == "owner_repo"
        assert "md_content" in obj
        assert "script_content" in obj

    def test_export_json_not_found(self, tmp_path):
        from gh_trending_audio.exporter import export_json
        data = export_json(tmp_path, "nonexistent", "proj")
        assert data is None

    def test_export_zip(self, tmp_path):
        from gh_trending_audio.exporter import export_zip
        self._setup_project(tmp_path)
        data = export_zip(tmp_path, "output_test", "owner_repo")
        assert data is not None
        zf = zipfile.ZipFile(__import__("io").BytesIO(data))
        names = zf.namelist()
        assert "owner_repo.md" in names
        assert "owner_repo_script.txt" in names
        assert "metadata.json" in names
        # SRT/VTT may or may not be present
        assert any(n.endswith(".srt") for n in names)

    def test_export_zip_not_found(self, tmp_path):
        from gh_trending_audio.exporter import export_zip
        data = export_zip(tmp_path, "nonexistent", "proj")
        assert data is None

    def test_export_pdf(self, tmp_path):
        from gh_trending_audio.exporter import export_pdf
        self._setup_project(tmp_path)
        data = export_pdf(tmp_path, "output_test", "owner_repo")
        assert data is not None
        assert data[:4] == b"%PDF"  # PDF magic number

    def test_export_epub(self, tmp_path):
        from gh_trending_audio.exporter import export_epub
        self._setup_project(tmp_path)
        data = export_epub(tmp_path, "output_test", "owner_repo")
        assert data is not None
        assert data[:2] == b"PK"  # EPUB is a ZIP

    def test_export_project_json(self, tmp_path):
        from gh_trending_audio.exporter import export_project
        self._setup_project(tmp_path)
        data, filename, content_type = export_project(tmp_path, "output_test", "owner_repo", "json")
        assert data is not None
        assert filename == "owner_repo.json"
        assert "json" in content_type

    def test_export_project_zip(self, tmp_path):
        from gh_trending_audio.exporter import export_project
        self._setup_project(tmp_path)
        data, filename, content_type = export_project(tmp_path, "output_test", "owner_repo", "zip")
        assert data is not None
        assert filename == "owner_repo.zip"
        assert "zip" in content_type

    def test_export_project_pdf(self, tmp_path):
        from gh_trending_audio.exporter import export_project
        self._setup_project(tmp_path)
        data, filename, content_type = export_project(tmp_path, "output_test", "owner_repo", "pdf")
        assert data is not None
        assert filename == "owner_repo.pdf"
        assert "pdf" in content_type

    def test_export_project_epub(self, tmp_path):
        from gh_trending_audio.exporter import export_project
        self._setup_project(tmp_path)
        data, filename, content_type = export_project(tmp_path, "output_test", "owner_repo", "epub")
        assert data is not None
        assert filename == "owner_repo.epub"
        assert "epub" in content_type

    def test_export_project_invalid_format(self, tmp_path):
        from gh_trending_audio.exporter import export_project
        data, filename, content_type = export_project(tmp_path, "x", "y", "invalid")
        assert data is None
        assert filename == ""
        assert content_type == ""

    def test_markdown_to_plain_text(self):
        from gh_trending_audio.exporter import _markdown_to_plain_text
        md = "# Title\n\n**Bold** and *italic*\n\n- Item 1\n- Item 2\n\n`code`"
        text = _markdown_to_plain_text(md)
        assert "Title" in text
        assert "Bold" in text
        assert "italic" in text
        assert "Item 1" in text
        assert "#" not in text
        assert "*" not in text

    def test_find_cjk_font(self):
        from gh_trending_audio.exporter import _find_cjk_font
        font = _find_cjk_font()
        # 在有 CJK 字体的系统上应返回路径
        if font:
            assert Path(font).exists()


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestExporterIntegration:
    """多格式导出 API 端点集成测试。"""

    def test_export_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/export/" in r["pattern"] for r in routes)
        assert any("serve_export" in r["handler"] for r in routes)

    def test_export_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_export
        assert callable(serve_export)

    def test_project_html_has_export_placeholder(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "{download_export_btn}" in PROJECT_HTML

    def test_renderer_passes_export_btn(self):
        from gh_trending_audio.web.renderer import render_project
        import inspect
        source = inspect.getsource(render_project)
        assert "download_export_btn" in source
        assert "format=pdf" in source
        assert "format=epub" in source
        assert "format=json" in source
        assert "format=zip" in source

    def test_lazy_export_exporter(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "export_project")
        assert hasattr(gh_trending_audio, "export_json")
        assert hasattr(gh_trending_audio, "export_zip")
        assert hasattr(gh_trending_audio, "export_pdf")
        assert hasattr(gh_trending_audio, "export_epub")

    def test_requirements_has_fpdf2(self):
        from pathlib import Path
        req = Path("/workspace/gh_trending_audio/requirements.txt").read_text()
        assert "fpdf2" in req

    def test_requirements_has_ebooklib(self):
        from pathlib import Path
        req = Path("/workspace/gh_trending_audio/requirements.txt").read_text()
        assert "ebooklib" in req

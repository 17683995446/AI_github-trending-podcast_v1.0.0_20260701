"""阶段7: SRT/VTT 字幕生成 测试。"""

import pytest
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# 单元测试
# ═══════════════════════════════════════════════════════════════════

class TestSubtitleUnit:
    """字幕生成器单元测试。"""

    def test_parse_dialogue_basic(self):
        from gh_trending_audio.subtitle_gen import parse_dialogue
        script = "A: 你好\nB: 你好，欢迎来到播客\nA: 今天我们来聊聊这个项目"
        segments = parse_dialogue(script)
        assert len(segments) == 3
        assert segments[0]["speaker"] == "A"
        assert segments[0]["text"] == "你好"
        assert segments[1]["speaker"] == "B"
        assert segments[2]["speaker"] == "A"

    def test_parse_dialogue_no_speaker(self):
        from gh_trending_audio.subtitle_gen import parse_dialogue
        script = "这是一段旁白文本\n没有说话人标记"
        segments = parse_dialogue(script)
        assert len(segments) == 1
        assert segments[0]["speaker"] == ""

    def test_parse_dialogue_empty(self):
        from gh_trending_audio.subtitle_gen import parse_dialogue
        assert parse_dialogue("") == []
        assert parse_dialogue("\n\n") == []

    def test_parse_dialogue_multiline_speaker(self):
        from gh_trending_audio.subtitle_gen import parse_dialogue
        script = "A: 第一行\n第二行继续\nB: 回复"
        segments = parse_dialogue(script)
        assert len(segments) == 2
        assert "第一行" in segments[0]["text"]
        assert "第二行继续" in segments[0]["text"]

    def test_estimate_timestamps_with_duration(self):
        from gh_trending_audio.subtitle_gen import estimate_timestamps, parse_dialogue
        script = "A: 你好欢迎来到节目\nB: 今天我们来聊一个有趣的项目"
        segments = parse_dialogue(script)
        subs = estimate_timestamps(segments, total_duration_seconds=10.0)
        assert len(subs) == 2
        assert subs[0].start_ms == 0
        assert subs[0].end_ms > 0
        assert subs[1].start_ms == subs[0].end_ms
        assert subs[1].end_ms == 10000  # 10秒 = 10000ms

    def test_estimate_timestamps_without_duration(self):
        from gh_trending_audio.subtitle_gen import estimate_timestamps, parse_dialogue
        script = "A: 你好"
        segments = parse_dialogue(script)
        subs = estimate_timestamps(segments, total_duration_seconds=None)
        assert len(subs) == 1
        assert subs[0].start_ms == 0
        assert subs[0].end_ms > 0  # 应按默认语速估算

    def test_split_long_text(self):
        from gh_trending_audio.subtitle_gen import _split_long_text
        long_text = "这是第一句话。这是第二句话。这是第三句话。" * 10
        chunks = _split_long_text(long_text, max_chars=30)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 30

    def test_split_short_text(self):
        from gh_trending_audio.subtitle_gen import _split_long_text
        assert _split_long_text("短文本") == ["短文本"]

    def test_format_srt_time(self):
        from gh_trending_audio.subtitle_gen import _format_srt_time
        assert _format_srt_time(0) == "00:00:00,000"
        assert _format_srt_time(1500) == "00:00:01,500"
        assert _format_srt_time(65000) == "00:01:05,000"
        assert _format_srt_time(3661500) == "01:01:01,500"

    def test_format_vtt_time(self):
        from gh_trending_audio.subtitle_gen import _format_vtt_time
        assert _format_vtt_time(0) == "00:00:00.000"
        assert _format_vtt_time(1500) == "00:00:01.500"
        assert _format_vtt_time(65000) == "00:01:05.000"

    def test_generate_srt_format(self):
        from gh_trending_audio.subtitle_gen import generate_srt, SubtitleSegment
        segments = [
            SubtitleSegment(text="你好", start_ms=0, end_ms=2000, speaker="A"),
            SubtitleSegment(text="欢迎", start_ms=2000, end_ms=4000, speaker="B"),
        ]
        srt = generate_srt(segments)
        assert "1" in srt
        assert "00:00:00,000 --> 00:00:02,000" in srt
        assert "A: 你好" in srt
        assert "2" in srt
        assert "00:00:02,000 --> 00:00:04,000" in srt
        assert "B: 欢迎" in srt

    def test_generate_vtt_format(self):
        from gh_trending_audio.subtitle_gen import generate_vtt, SubtitleSegment
        segments = [
            SubtitleSegment(text="你好", start_ms=0, end_ms=2000, speaker="A"),
        ]
        vtt = generate_vtt(segments)
        assert vtt.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in vtt
        assert "A: 你好" in vtt

    def test_generate_srt_no_speaker(self):
        from gh_trending_audio.subtitle_gen import generate_srt, SubtitleSegment
        seg = SubtitleSegment(text="旁白文本", start_ms=0, end_ms=3000, speaker="")
        srt = generate_srt([seg])
        assert "旁白文本" in srt
        assert ":" not in srt.split("\n")[2]  # 第三行是文本，不应有说话人前缀

    def test_generate_subtitle_for_project(self, tmp_path):
        from gh_trending_audio.subtitle_gen import generate_subtitle_for_project
        # 创建模拟项目
        out_dir = tmp_path / "output_test"
        out_dir.mkdir()
        (out_dir / "owner_repo.md").write_text("# Test", encoding="utf-8")
        (out_dir / "owner_repo_script.txt").write_text(
            "A: 欢迎来到播客\nB: 今天我们聊聊这个项目", encoding="utf-8"
        )
        (out_dir / "owner_repo.mp3").write_bytes(b"fake mp3")

        srt = generate_subtitle_for_project(tmp_path, "output_test", "owner_repo", "srt")
        assert srt is not None
        assert "00:00:00,000" in srt
        assert "A: 欢迎来到播客" in srt

        vtt = generate_subtitle_for_project(tmp_path, "output_test", "owner_repo", "vtt")
        assert vtt is not None
        assert vtt.startswith("WEBVTT")

    def test_generate_subtitle_project_not_found(self, tmp_path):
        from gh_trending_audio.subtitle_gen import generate_subtitle_for_project
        result = generate_subtitle_for_project(tmp_path, "nonexistent", "proj", "srt")
        assert result is None

    def test_min_duration_enforced(self):
        from gh_trending_audio.subtitle_gen import estimate_timestamps
        # 极短文本 + 极短时长
        segments = [{"speaker": "A", "text": "嗨"}]
        subs = estimate_timestamps(segments, total_duration_seconds=0.1)
        assert subs[0].end_ms - subs[0].start_ms >= 1500  # _MIN_DURATION_MS


# ═══════════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════════

class TestSubtitleIntegration:
    """字幕生成 API 端点集成测试。"""

    def test_subtitle_route_exists(self):
        from gh_trending_audio.web.route_table import list_routes
        import inspect
        routes = list_routes("GET")
        assert any("/api/subtitle/" in r["pattern"] for r in routes)
        assert any("serve_subtitle" in r["handler"] for r in routes)

    def test_subtitle_handler_exists(self):
        from gh_trending_audio.web.api_handlers import serve_subtitle
        assert callable(serve_subtitle)

    def test_project_html_has_subtitle_placeholder(self):
        from gh_trending_audio.web.templates import PROJECT_HTML
        assert "{download_subtitle_btn}" in PROJECT_HTML

    def test_renderer_passes_subtitle_btn(self):
        from gh_trending_audio.web.renderer import render_project
        import inspect
        source = inspect.getsource(render_project)
        assert "download_subtitle_btn" in source

    def test_renderer_has_vtt_track(self):
        from gh_trending_audio.web.renderer import render_project
        import inspect
        source = inspect.getsource(render_project)
        assert "track" in source
        assert "format=vtt" in source

    def test_lazy_export_subtitle(self):
        import gh_trending_audio
        assert hasattr(gh_trending_audio, "generate_srt")
        assert hasattr(gh_trending_audio, "generate_vtt")
        assert hasattr(gh_trending_audio, "parse_dialogue")

"""Stage 7: 开源工具替换 — 测试套件。

本测试套件验证各阶段开源工具替换的正确性：
- Stage 1 (P0-a): WaveSurfer.js v7 单引擎化，移除 Howler.js
- Stage 2 (P0-b): SweetAlert2 统一弹窗
- Stage 3 (P1-a): DOMPurify 安全修复
- Stage 4 (P1-b): Notyf + clipboard.js + hotkeys-js
- Stage 5 (P2): CountUp.js + SortableJS + Chart.js
- Stage 6 (P3): ky 统一 fetch 封装

测试策略：
- 单元测试：验证模板字符串中的 CDN 引用、API 调用、函数定义
- 集成测试：验证模板渲染后的 HTML 结构完整性
- 系统测试：验证 Web 服务器启动和页面可访问性
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gh_trending_audio.web.templates import (
    DASHBOARD_HTML,
    PLAYER_HTML,
    PROJECT_HTML,
    _AUDIO_SESSION_JS,
    _SHARED_JS_UTILS,
)
from gh_trending_audio.web.renderer import render_dashboard, render_player, render_project


# ══════════════════════════════════════════════════════════════════
# Stage 1: WaveSurfer.js v7 单引擎化 — 移除 Howler.js
# ══════════════════════════════════════════════════════════════════


class TestStage1HowlerRemoval:
    """单元测试：验证 Howler.js 已从所有模板中完全移除。"""

    def test_howler_cdn_removed_from_dashboard(self):
        """DASHBOARD_HTML 不应包含 Howler CDN 引用。"""
        assert "howler" not in DASHBOARD_HTML.lower(), "Dashboard 仍引用 Howler CDN"

    def test_howler_cdn_removed_from_player(self):
        """PLAYER_HTML 不应包含 Howler CDN 引用。"""
        assert "howler" not in PLAYER_HTML.lower(), "Player 仍引用 Howler CDN"

    def test_howler_cdn_removed_from_project(self):
        """PROJECT_HTML 不应包含 Howler CDN 引用。"""
        assert "howler" not in PROJECT_HTML.lower(), "Project 仍引用 Howler CDN"

    def test_no_howl_variable_in_dashboard(self):
        """DASHBOARD_HTML 不应包含 Howl 实例变量（dashHowl）。"""
        assert "dashhowl" not in DASHBOARD_HTML.lower(), "Dashboard 仍含 dashHowl 变量"
        assert "new howl" not in DASHBOARD_HTML.lower(), "Dashboard 仍创建 Howl 实例"

    def test_no_howl_variable_in_player(self):
        """PLAYER_HTML 不应包含 Howl 实例变量（howl）。"""
        assert "new howl" not in PLAYER_HTML.lower(), "Player 仍创建 Howl 实例"
        # 检查变量声明（排除注释中的提及）
        for line in PLAYER_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            assert "var howl" not in stripped.lower(), f"Player 仍声明 howl 变量: {stripped}"

    def test_no_minihowl_variable_in_project(self):
        """PROJECT_HTML 不应包含 miniHowl 变量。"""
        assert "minihowl" not in PROJECT_HTML.lower(), "Project 仍含 miniHowl 变量"
        assert "new howl" not in PROJECT_HTML.lower(), "Project 仍创建 Howl 实例"

    def test_no_howl_internal_src_access(self):
        """不应访问 Howler 内部属性 _src（已用 miniAudioUrl 替代）。"""
        assert "._src" not in PROJECT_HTML, "Project 仍访问 Howler 内部 _src 属性"


class TestStage1WaveSurferSingleEngine:
    """单元测试：验证 WaveSurfer v7 单引擎在 PLAYER_HTML 中正确配置。"""

    def test_wavesurfer_cdn_present_in_player(self):
        """PLAYER_HTML 应包含 WaveSurfer v7 CDN。"""
        assert "wavesurfer.js@7" in PLAYER_HTML, "Player 缺少 WaveSurfer v7 CDN"

    def test_wavesurfer_not_muted(self):
        """WaveSurfer 不应被设置为静音（setVolume(0) 已移除）。"""
        # 查找 setVolume(0) 调用（排除注释）
        for line in PLAYER_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            assert "setvolume(0)" not in stripped.lower(), f"WaveSurfer 仍被静音: {stripped}"

    def test_no_dual_engine_sync(self):
        """不应存在 Howler↔WaveSurfer 双引擎同步代码。"""
        # 同步桥接特征：howl.on('play', ... wavesurfer.play())
        assert "howl.on('play'" not in PLAYER_HTML, "仍存在 Howler→WaveSurfer 同步代码"
        assert "howl.on('pause'" not in PLAYER_HTML, "仍存在 Howler→WaveSurfer 同步代码"
        assert "howl.on('seek'" not in PLAYER_HTML, "仍存在 Howler→WaveSurfer 同步代码"

    def test_wavesurfer_native_events(self):
        """WaveSurfer 应使用原生事件（play/pause/finish/ready）而非 Howler 回调。"""
        assert "wavesurfer.on('play'" in PLAYER_HTML, "WaveSurfer 缺少 play 事件"
        assert "wavesurfer.on('pause'" in PLAYER_HTML, "WaveSurfer 缺少 pause 事件"
        assert "wavesurfer.on('finish'" in PLAYER_HTML, "WaveSurfer 缺少 finish 事件"
        assert "wavesurfer.on('ready'" in PLAYER_HTML, "WaveSurfer 缺少 ready 事件"

    def test_wavesurfer_api_methods(self):
        """WaveSurfer 应使用 v7 API 方法（getCurrentTime/setTime/getDuration/isPlaying）。"""
        assert "wavesurfer.getCurrentTime()" in PLAYER_HTML, "缺少 getCurrentTime() 调用"
        assert "wavesurfer.setTime(" in PLAYER_HTML, "缺少 setTime() 调用"
        assert "wavesurfer.getDuration()" in PLAYER_HTML, "缺少 getDuration() 调用"
        assert "wavesurfer.isPlaying()" in PLAYER_HTML, "缺少 isPlaying() 调用"


class TestStage1NativeAudioAPI:
    """单元测试：验证 DASHBOARD 和 PROJECT 页面使用原生 Audio API。"""

    def test_dashboard_uses_native_audio(self):
        """DASHBOARD_HTML 应使用 new Audio() 而非 new Howl()。"""
        assert "new Audio(" in DASHBOARD_HTML, "Dashboard 未使用原生 Audio API"
        assert "dashAudio" in DASHBOARD_HTML, "Dashboard 缺少 dashAudio 变量"

    def test_dashboard_audio_event_listeners(self):
        """DASHBOARD 应使用 addEventListener 而非 Howler 回调。"""
        assert "addEventListener('play'" in DASHBOARD_HTML, "Dashboard 缺少 play 事件监听"
        assert "addEventListener('pause'" in DASHBOARD_HTML, "Dashboard 缺少 pause 事件监听"
        assert "addEventListener('ended'" in DASHBOARD_HTML, "Dashboard 缺少 ended 事件监听"
        assert "addEventListener('loadedmetadata'" in DASHBOARD_HTML, "Dashboard 缺少 loadedmetadata 事件监听"

    def test_dashboard_audio_properties(self):
        """DASHBOARD 应使用原生 Audio 属性（currentTime/duration/paused）。"""
        assert "dashAudio.currentTime" in DASHBOARD_HTML, "Dashboard 未使用 currentTime"
        assert "dashAudio.duration" in DASHBOARD_HTML, "Dashboard 未使用 duration"
        assert "dashAudio.paused" in DASHBOARD_HTML, "Dashboard 未使用 paused 属性"

    def test_project_uses_native_audio(self):
        """PROJECT_HTML 应使用 new Audio() 而非 new Howl()。"""
        assert "new Audio(" in PROJECT_HTML, "Project 未使用原生 Audio API"
        assert "miniAudio" in PROJECT_HTML, "Project 缺少 miniAudio 变量"

    def test_project_audio_event_listeners(self):
        """PROJECT 应使用 addEventListener 而非 Howler 回调。"""
        assert "addEventListener('play'" in PROJECT_HTML, "Project 缺少 play 事件监听"
        assert "addEventListener('pause'" in PROJECT_HTML, "Project 缺少 pause 事件监听"
        assert "addEventListener('ended'" in PROJECT_HTML, "Project 缺少 ended 事件监听"
        assert "addEventListener('loadedmetadata'" in PROJECT_HTML, "Project 缺少 loadedmetadata 事件监听"

    def test_project_audio_url_tracking(self):
        """PROJECT 应使用 miniAudioUrl 变量而非 Howler._src。"""
        assert "miniAudioUrl" in PROJECT_HTML, "Project 缺少 miniAudioUrl 变量"


class TestStage1AudioSessionIntegrity:
    """集成测试：验证音频会话持久化逻辑在引擎替换后仍正确工作。"""

    def test_audio_session_js_unchanged(self):
        """_AUDIO_SESSION_JS 不应包含 Howler 引用。"""
        assert "howl" not in _AUDIO_SESSION_JS.lower(), "Audio session JS 仍引用 Howler"

    def test_audio_session_functions_present(self):
        """_AUDIO_SESSION_JS 应保留核心函数。"""
        assert "saveAudioSession" in _AUDIO_SESSION_JS
        assert "loadAudioSession" in _AUDIO_SESSION_JS
        assert "clearAudioSession" in _AUDIO_SESSION_JS

    def test_dashboard_pagehide_saves_session(self):
        """DASHBOARD pagehide 应使用 dashAudio 属性保存会话。"""
        assert "dashAudio.currentTime" in DASHBOARD_HTML
        assert "!dashAudio.paused" in DASHBOARD_HTML

    def test_player_pagehide_saves_session(self):
        """PLAYER pagehide 应使用 wavesurfer 属性保存会话。"""
        assert "wavesurfer.getCurrentTime()" in PLAYER_HTML
        assert "wavesurfer.isPlaying()" in PLAYER_HTML

    def test_project_pagehide_saves_session(self):
        """PROJECT pagehide 应使用 miniAudio 属性保存会话。"""
        assert "miniAudio.currentTime" in PROJECT_HTML
        assert "!miniAudio.paused" in PROJECT_HTML


class TestStage1TemplateRendering:
    """集成测试：验证模板渲染后 HTML 结构完整。"""

    def test_dashboard_renders_without_error(self):
        """仪表盘模板渲染不应抛出异常。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        html = render_dashboard(output_dir)
        assert "<html" in html.lower()
        assert "</html>" in html.lower()
        assert "howler" not in html.lower()

    def test_player_renders_without_error(self):
        """播放器模板渲染不应抛出异常。"""
        html = render_player()
        assert "<html" in html.lower()
        assert "</html>" in html.lower()
        assert "howler" not in html.lower()
        assert "wavesurfer" in html.lower()

    def test_project_renders_without_error(self):
        """项目详情模板渲染不应抛出异常。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        # 使用实际存在的项目
        projects = list(output_dir.iterdir())
        md_files = [p for p in projects if p.suffix == ".md"]
        if not md_files:
            pytest.skip("无可用项目数据")
        name = md_files[0].stem
        html = render_project(output_dir, "output_demo", name)
        assert "<html" in html.lower() or "未找到" in html


class TestStage1SystemIntegration:
    """系统测试：验证 Web 服务器启动和页面可访问性。"""

    def test_server_imports_successfully(self):
        """Web 服务器模块应能成功导入。"""
        from gh_trending_audio.web.server import create_server

        assert create_server is not None

    def test_templates_module_imports_successfully(self):
        """templates 模块应能成功导入（无语法错误）。"""
        from gh_trending_audio.web import templates

        assert hasattr(templates, "DASHBOARD_HTML")
        assert hasattr(templates, "PLAYER_HTML")
        assert hasattr(templates, "PROJECT_HTML")

    def test_no_format_string_errors(self):
        """模板中 str.format() 占位符应正确匹配（无花括号错误）。"""
        # 尝试渲染 Player 模板（最简单的渲染，只需 _AUDIO_SESSION_JS）
        try:
            render_player()
        except (ValueError, KeyError) as e:
            pytest.fail(f"Player 模板格式化失败: {e}")

        # 尝试渲染 Dashboard 模板（需要实际数据）
        output_dir = Path(__file__).parent.parent / "output_demo"
        if output_dir.exists():
            try:
                render_dashboard(output_dir)
            except (ValueError, KeyError) as e:
                pytest.fail(f"Dashboard 模板格式化失败: {e}")


# ══════════════════════════════════════════════════════════════════
# Stage 2: SweetAlert2 统一弹窗 — 替换 alert/confirm
# ══════════════════════════════════════════════════════════════════


class TestStage2SweetAlert2CDN:
    """单元测试：验证 SweetAlert2 CDN 已添加到所有模板。"""

    def test_sweetalert2_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 SweetAlert2 CDN 引用。"""
        assert "sweetalert2@11" in DASHBOARD_HTML, "Dashboard 缺少 SweetAlert2 CDN"

    def test_sweetalert2_cdn_in_player(self):
        """PLAYER_HTML 应包含 SweetAlert2 CDN 引用。"""
        assert "sweetalert2@11" in PLAYER_HTML, "Player 缺少 SweetAlert2 CDN"

    def test_sweetalert2_cdn_in_project(self):
        """PROJECT_HTML 应包含 SweetAlert2 CDN 引用。"""
        assert "sweetalert2@11" in PROJECT_HTML, "Project 缺少 SweetAlert2 CDN"

    def test_sweetalert2_cdn_from_jsdelivr(self):
        """SweetAlert2 应从 jsDelivr CDN 加载。"""
        for name, html in [("DASHBOARD", DASHBOARD_HTML), ("PLAYER", PLAYER_HTML), ("PROJECT", PROJECT_HTML)]:
            assert "cdn.jsdelivr.net/npm/sweetalert2" in html, f"{name} SweetAlert2 CDN 源不正确"


class TestStage2AlertReplacement:
    """单元测试：验证原生 alert()/confirm() 已被 SweetAlert2 替换。"""

    def test_no_raw_alert_in_dashboard(self):
        """DASHBOARD_HTML 不应包含原生 alert() 调用（书签代码除外）。"""
        # 排除注释行和书签代码（在 GitHub 外部页面运行，无法加载 SweetAlert2）
        for line in DASHBOARD_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if "请在 GitHub 仓库页面使用此书签" in stripped:
                continue
            assert "alert(" not in stripped, f"Dashboard 仍使用原生 alert(): {stripped}"

    def test_no_raw_confirm_in_dashboard(self):
        """DASHBOARD_HTML 不应包含原生 confirm() 调用。"""
        for line in DASHBOARD_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            assert "confirm(" not in stripped, f"Dashboard 仍使用原生 confirm(): {stripped}"

    def test_no_raw_alert_in_player(self):
        """PLAYER_HTML 不应包含原生 alert() 调用。"""
        for line in PLAYER_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            assert "alert(" not in stripped, f"Player 仍使用原生 alert(): {stripped}"

    def test_bookmarklet_alerts_are_acceptable(self):
        """书签代码中的 alert() 是可接受的（在 GitHub 页面运行，无法加载 SweetAlert2）。"""
        # 书签代码位于字符串拼接中，使用 alert() 是正确的
        bookmarklet_alerts = [l for l in DASHBOARD_HTML.split("\n") if "alert(" in l and "请在 GitHub 仓库页面使用此书签" in l]
        assert len(bookmarklet_alerts) >= 1, "书签代码中的 alert() 应保留"

    def test_no_raw_alert_in_project_outside_bookmarklet(self):
        """PROJECT_HTML 不应包含原生 alert() 调用。"""
        for line in PROJECT_HTML.split("\n"):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            assert "alert(" not in stripped, f"Project 仍使用原生 alert(): {stripped}"


class TestStage2SwalFireUsage:
    """单元测试：验证 Swal.fire() 在正确的场景中使用。"""

    def test_dashboard_uses_swal_for_delete_confirm(self):
        """Dashboard 批量删除应使用 Swal.fire 确认对话框。"""
        assert "Swal.fire" in DASHBOARD_HTML
        assert "确认删除" in DASHBOARD_HTML, "Dashboard 缺少删除确认对话框"

    def test_dashboard_uses_notyf_for_toast(self):
        """Dashboard 应使用 Notyf 进行 toast 通知（Stage 4 升级后）。"""
        assert "notyf" in DASHBOARD_HTML.lower(), "Dashboard 缺少 Notyf 通知库"
        assert "new Notyf" in DASHBOARD_HTML, "Dashboard 未初始化 Notyf"

    def test_dashboard_uses_swal_show_cancel_button(self):
        """Dashboard 确认对话框应包含取消按钮。"""
        assert "showCancelButton: true" in DASHBOARD_HTML, "Dashboard 确认对话框缺少取消按钮"

    def test_dashboard_uses_swal_confirm_button_color(self):
        """Dashboard 删除确认应使用红色确认按钮。"""
        assert "confirmButtonColor: '#d33'" in DASHBOARD_HTML, "Dashboard 删除按钮颜色不正确"

    def test_project_uses_swal_for_readme_error(self):
        """Project README 弹窗应使用 Swal.fire 显示错误信息。"""
        assert "Swal.fire" in PROJECT_HTML
        assert "无法获取 README" in PROJECT_HTML, "Project README 错误提示未替换为 Swal"

    def test_project_uses_swal_for_filetree_error(self):
        """Project 文件目录弹窗应使用 Swal.fire 显示错误信息。"""
        assert "无法获取文件目录" in PROJECT_HTML, "Project 文件目录错误提示未替换为 Swal"


class TestStage2RenderingIntegrity:
    """集成测试：验证 SweetAlert2 替换后模板仍能正确渲染。"""

    def test_dashboard_renders_with_sweetalert2(self):
        """仪表盘模板渲染后应包含 SweetAlert2。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        html = render_dashboard(output_dir)
        assert "sweetalert2" in html.lower()
        assert "Swal.fire" in html

    def test_player_renders_with_sweetalert2(self):
        """播放器模板渲染后应包含 SweetAlert2。"""
        html = render_player()
        assert "sweetalert2" in html.lower()

    def test_project_renders_with_sweetalert2(self):
        """项目模板渲染后应包含 SweetAlert2。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        projects = list(output_dir.iterdir())
        md_files = [p for p in projects if p.suffix == ".md"]
        if not md_files:
            pytest.skip("无可用项目数据")
        name = md_files[0].stem
        html = render_project(output_dir, "output_demo", name)
        assert "sweetalert2" in html.lower() or "未找到" in html


class TestStage2SystemIntegration:
    """系统测试：验证 SweetAlert2 集成不影响系统功能。"""

    def test_server_imports_with_sweetalert2(self):
        """引入 SweetAlert2 后服务器模块应仍能正常导入。"""
        from gh_trending_audio.web.server import create_server

        assert create_server is not None

    def test_no_format_conflicts_with_swal(self):
        """SweetAlert2 的花括号不应与 str.format() 冲突。"""
        try:
            render_player()
        except (ValueError, KeyError) as e:
            pytest.fail(f"Player 模板因 SweetAlert2 格式化失败: {e}")

        output_dir = Path(__file__).parent.parent / "output_demo"
        if output_dir.exists():
            try:
                render_dashboard(output_dir)
            except (ValueError, KeyError) as e:
                pytest.fail(f"Dashboard 模板因 SweetAlert2 格式化失败: {e}")


# ══════════════════════════════════════════════════════════════════
# Stage 3: DOMPurify 安全修复 — 统一 HTML 净化
# ══════════════════════════════════════════════════════════════════


class TestStage3DOMPurifyCDN:
    """单元测试：验证 DOMPurify CDN 已添加到所有模板。"""

    def test_dompurify_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 DOMPurify CDN 引用。"""
        assert "dompurify@3" in DASHBOARD_HTML, "Dashboard 缺少 DOMPurify CDN"

    def test_dompurify_cdn_in_player(self):
        """PLAYER_HTML 应包含 DOMPurify CDN 引用。"""
        assert "dompurify@3" in PLAYER_HTML, "Player 缺少 DOMPurify CDN"

    def test_dompurify_cdn_in_project(self):
        """PROJECT_HTML 应包含 DOMPurify CDN 引用。"""
        assert "dompurify@3" in PROJECT_HTML, "Project 缺少 DOMPurify CDN"

    def test_dompurify_cdn_from_jsdelivr(self):
        """DOMPurify 应从 jsDelivr CDN 加载。"""
        for name, html in [("DASHBOARD", DASHBOARD_HTML), ("PLAYER", PLAYER_HTML), ("PROJECT", PROJECT_HTML)]:
            assert "cdn.jsdelivr.net/npm/dompurify" in html, f"{name} DOMPurify CDN 源不正确"


class TestStage3SanitizeHtmlFunction:
    """单元测试：验证 sanitizeHtml / escapeHtml 通过 _SHARED_JS_UTILS 统一定义并注入到所有模板。"""

    def test_shared_utils_has_sanitize_html(self):
        """_SHARED_JS_UTILS 应定义 sanitizeHtml 函数（统一来源）。"""
        assert "function sanitizeHtml" in _SHARED_JS_UTILS, "共享工具缺少 sanitizeHtml 函数"

    def test_shared_utils_has_escape_html(self):
        """_SHARED_JS_UTILS 应定义通用 escapeHtml 函数（修复 latent bug）。"""
        assert "function escapeHtml" in _SHARED_JS_UTILS, "共享工具缺少 escapeHtml 函数"

    def test_sanitize_html_uses_dompurify(self):
        """sanitizeHtml 应调用 DOMPurify.sanitize。"""
        assert "DOMPurify.sanitize" in _SHARED_JS_UTILS, "sanitizeHtml 未使用 DOMPurify"

    def test_sanitize_html_has_fallback(self):
        """sanitizeHtml 应有 CDN 加载失败的降级策略。"""
        assert "return html" in _SHARED_JS_UTILS, "sanitizeHtml 缺少降级策略"

    def test_dashboard_injects_shared_utils(self):
        """DASHBOARD_HTML 应注入 _SHARED_JS_UTILS。"""
        assert "{_SHARED_JS_UTILS}" in DASHBOARD_HTML, "Dashboard 未注入共享工具函数"

    def test_player_injects_shared_utils(self):
        """PLAYER_HTML 应注入 _SHARED_JS_UTILS。"""
        assert "{_SHARED_JS_UTILS}" in PLAYER_HTML, "Player 未注入共享工具函数"

    def test_project_injects_shared_utils(self):
        """PROJECT_HTML 应注入 _SHARED_JS_UTILS。"""
        assert "{_SHARED_JS_UTILS}" in PROJECT_HTML, "Project 未注入共享工具函数"


class TestStage3InnerHTMLSanitization:
    """单元测试：验证关键 innerHTML 赋值已用 sanitizeHtml 包裹。"""

    def test_readme_content_sanitized(self):
        """README 内容（marked.parse 输出）应通过 sanitizeHtml 净化。"""
        assert "sanitizeHtml('<div class=\"md-content\">' + html + '</div>')" in PROJECT_HTML, \
            "README 内容未使用 sanitizeHtml 净化"

    def test_onboarding_content_sanitized(self):
        """入门指南内容（marked.parse 输出）应通过 sanitizeHtml 净化。"""
        assert "sanitizeHtml('<div class=\"md-content\">' + html + '</div>')" in PROJECT_HTML, \
            "入门指南内容未使用 sanitizeHtml 净化"

    def test_qa_answer_sanitized(self):
        """QA 回答（marked.parse 输出）应通过 sanitizeHtml 净化。"""
        assert "sanitizeHtml(marked.parse(answerText))" in PROJECT_HTML, \
            "QA 回答未使用 sanitizeHtml 净化"

    def test_file_tree_sidebar_sanitized(self):
        """文件目录侧栏 HTML 应通过 sanitizeHtml 净化。"""
        assert "sanitizeHtml(html" in PROJECT_HTML, \
            "文件目录侧栏未使用 sanitizeHtml 净化"

    def test_community_insights_sanitized(self):
        """社区洞察内容应通过 sanitizeHtml 净化。"""
        assert "sanitizeHtml(html)" in PROJECT_HTML, \
            "社区洞察内容未使用 sanitizeHtml 净化"

    def test_markdown_fix_sanitized(self):
        """Markdown 修复渲染结果应通过 sanitizeHtml 净化。"""
        assert "mdContent.innerHTML = sanitizeHtml(html)" in PROJECT_HTML, \
            "Markdown 修复渲染未使用 sanitizeHtml 净化"


class TestStage3ErrorEscaping:
    """单元测试：验证 API 错误消息已用 escapeHtml 转义。"""

    def test_readme_error_escaped(self):
        """README API 错误消息应使用 escapeHtml 转义。"""
        assert "escapeHtml(data.error)" in PROJECT_HTML, "README 错误消息未转义"

    def test_file_tree_error_escaped(self):
        """文件目录 API 错误消息应使用 escapeHtml 转义。"""
        # ftSidebar 的错误处理
        ft_error_count = PROJECT_HTML.count("escapeHtml(data.error)")
        assert ft_error_count >= 2, "文件目录错误消息未完全转义"

    def test_file_viewer_error_escaped(self):
        """文件查看器错误消息应使用 escapeHtml 转义。"""
        assert "escapeHtml(e.message)" in PROJECT_HTML, "文件查看器错误消息未转义"

    def test_network_errors_escaped(self):
        """网络错误消息应使用 escapeHtml 转义。"""
        assert "escapeHtml(e.message)" in PROJECT_HTML, "网络错误消息未转义"

    def test_no_raw_replace_lt_pattern(self):
        """不应存在手动 .replace(/</g,'&lt;') 模式（escapeHtml 函数定义除外）。"""
        for line in PROJECT_HTML.split("\n"):
            stripped = line.strip()
            # 排除 escapeHtml 函数定义行
            if "function escapeHtml" in stripped or "function obEscapeHtml" in stripped:
                continue
            if "return String(s)" in stripped or "return s.replace" in stripped:
                continue
            assert ".replace(/</" not in stripped, f"仍使用手动转义: {stripped}"


class TestStage3RenderingIntegrity:
    """集成测试：验证 DOMPurify 集成后模板仍能正确渲染。"""

    def test_dashboard_renders_with_dompurify(self):
        """仪表盘模板渲染后应包含 DOMPurify。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        html = render_dashboard(output_dir)
        assert "dompurify" in html.lower()
        assert "sanitizeHtml" in html

    def test_player_renders_with_dompurify(self):
        """播放器模板渲染后应包含 DOMPurify。"""
        html = render_player()
        assert "dompurify" in html.lower()
        assert "sanitizeHtml" in html

    def test_project_renders_with_dompurify(self):
        """项目模板渲染后应包含 DOMPurify。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        projects = list(output_dir.iterdir())
        md_files = [p for p in projects if p.suffix == ".md"]
        if not md_files:
            pytest.skip("无可用项目数据")
        name = md_files[0].stem
        html = render_project(output_dir, "output_demo", name)
        assert "dompurify" in html.lower() or "未找到" in html


class TestStage3SystemIntegration:
    """系统测试：验证 DOMPurify 集成不影响系统功能。"""

    def test_server_imports_with_dompurify(self):
        """引入 DOMPurify 后服务器模块应仍能正常导入。"""
        from gh_trending_audio.web.server import create_server

        assert create_server is not None

    def test_no_format_conflicts_with_dompurify(self):
        """DOMPurify 的花括号不应与 str.format() 冲突。"""
        try:
            render_player()
        except (ValueError, KeyError) as e:
            pytest.fail(f"Player 模板因 DOMPurify 格式化失败: {e}")

        output_dir = Path(__file__).parent.parent / "output_demo"
        if output_dir.exists():
            try:
                render_dashboard(output_dir)
            except (ValueError, KeyError) as e:
                pytest.fail(f"Dashboard 模板因 DOMPurify 格式化失败: {e}")


# ══════════════════════════════════════════════════════════════════
# Stage 4: Notyf + clipboard.js + hotkeys-js — 替换自定义实现
# ══════════════════════════════════════════════════════════════════


class TestStage4NotyfCDN:
    """单元测试：验证 Notyf CDN 已添加到所有模板。"""

    def test_notyf_css_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 Notyf CSS。"""
        assert "notyf.min.css" in DASHBOARD_HTML, "Dashboard 缺少 Notyf CSS"

    def test_notyf_js_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 Notyf JS。"""
        assert "notyf.min.js" in DASHBOARD_HTML, "Dashboard 缺少 Notyf JS"

    def test_notyf_css_cdn_in_player(self):
        """PLAYER_HTML 应包含 Notyf CSS。"""
        assert "notyf.min.css" in PLAYER_HTML, "Player 缺少 Notyf CSS"

    def test_notyf_js_cdn_in_player(self):
        """PLAYER_HTML 应包含 Notyf JS。"""
        assert "notyf.min.js" in PLAYER_HTML, "Player 缺少 Notyf JS"

    def test_notyf_css_cdn_in_project(self):
        """PROJECT_HTML 应包含 Notyf CSS。"""
        assert "notyf.min.css" in PROJECT_HTML, "Project 缺少 Notyf CSS"

    def test_notyf_js_cdn_in_project(self):
        """PROJECT_HTML 应包含 Notyf JS。"""
        assert "notyf.min.js" in PROJECT_HTML, "Project 缺少 Notyf JS"


class TestStage4NotyfInitialization:
    """单元测试：验证 Notyf 在所有模板中正确初始化。"""

    def test_dashboard_initializes_notyf(self):
        """DASHBOARD_HTML 应初始化 Notyf 实例。"""
        assert "new Notyf" in DASHBOARD_HTML, "Dashboard 未初始化 Notyf"
        assert "var notyf" in DASHBOARD_HTML, "Dashboard 未创建 notyf 变量"

    def test_player_initializes_notyf(self):
        """PLAYER_HTML 应初始化 Notyf 实例。"""
        assert "new Notyf" in PLAYER_HTML, "Player 未初始化 Notyf"
        assert "var notyf" in PLAYER_HTML, "Player 未创建 notyf 变量"

    def test_project_initializes_notyf(self):
        """PROJECT_HTML 应初始化 Notyf 实例。"""
        assert "new Notyf" in PROJECT_HTML, "Project 未初始化 Notyf"
        assert "var notyf" in PROJECT_HTML, "Project 未创建 notyf 变量"

    def test_dashboard_notyf_has_duration(self):
        """Dashboard Notyf 应配置 duration。"""
        assert "duration: 2500" in DASHBOARD_HTML, "Dashboard Notyf 缺少 duration 配置"

    def test_no_swal_toast_mode_in_dashboard(self):
        """Dashboard 不应再使用 SweetAlert2 toast 模式（已由 Notyf 替代）。"""
        assert "toast: true" not in DASHBOARD_HTML, "Dashboard 仍使用 SweetAlert2 toast 模式"


class TestStage4ClipboardJS:
    """单元测试：验证 clipboard.js CDN 已添加。"""

    def test_clipboard_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 clipboard.js CDN。"""
        assert "clipboard@2" in DASHBOARD_HTML, "Dashboard 缺少 clipboard.js CDN"

    def test_clipboard_cdn_in_project(self):
        """PROJECT_HTML 应包含 clipboard.js CDN。"""
        assert "clipboard@2" in PROJECT_HTML, "Project 缺少 clipboard.js CDN"

    def test_project_fallback_uses_clipboardjs(self):
        """PROJECT_HTML fallbackCopy 应优先使用 ClipboardJS.copy。"""
        assert "ClipboardJS.copy" in PROJECT_HTML, "Project fallbackCopy 未使用 ClipboardJS"

    def test_no_custom_toast_element_in_project(self):
        """PROJECT_HTML 不应再包含自定义 toast 元素。"""
        assert 'id="toast"' not in PROJECT_HTML, "Project 仍包含自定义 toast 元素"

    def test_no_copy_toast_css_in_project(self):
        """PROJECT_HTML 不应再包含 .copy-toast CSS。"""
        assert ".copy-toast" not in PROJECT_HTML, "Project 仍包含 .copy-toast CSS"

    def test_no_copy_toast_css_in_dashboard(self):
        """DASHBOARD_HTML 不应再包含 .copy-toast CSS。"""
        assert ".copy-toast" not in DASHBOARD_HTML, "Dashboard 仍包含 .copy-toast CSS"


class TestStage4HotkeysJS:
    """单元测试：验证 hotkeys-js CDN 已添加并使用。"""

    def test_hotkeys_cdn_in_dashboard(self):
        """DASHBOARD_HTML 应包含 hotkeys-js CDN。"""
        assert "hotkeys-js@3" in DASHBOARD_HTML, "Dashboard 缺少 hotkeys-js CDN"

    def test_hotkeys_cdn_in_player(self):
        """PLAYER_HTML 应包含 hotkeys-js CDN。"""
        assert "hotkeys-js@3" in PLAYER_HTML, "Player 缺少 hotkeys-js CDN"

    def test_player_uses_hotkeys(self):
        """PLAYER_HTML 应使用 hotkeys() 函数注册快捷键。"""
        assert "hotkeys('space'" in PLAYER_HTML, "Player 未用 hotkeys 注册 Space 键"
        assert "hotkeys('right'" in PLAYER_HTML, "Player 未用 hotkeys 注册 Right 键"
        assert "hotkeys('left'" in PLAYER_HTML, "Player 未用 hotkeys 注册 Left 键"
        assert "hotkeys('n'" in PLAYER_HTML, "Player 未用 hotkeys 注册 N 键"
        assert "hotkeys('p'" in PLAYER_HTML, "Player 未用 hotkeys 注册 P 键"

    def test_dashboard_uses_hotkeys(self):
        """DASHBOARD_HTML 应使用 hotkeys() 函数注册 Esc 键。"""
        assert "hotkeys('escape'" in DASHBOARD_HTML, "Dashboard 未用 hotkeys 注册 Esc 键"

    def test_player_hotkeys_has_fallback(self):
        """PLAYER_HTML 应有 hotkeys-js 加载失败的降级策略。"""
        assert "addEventListener('keydown'" in PLAYER_HTML, "Player 缺少 keydown 降级策略"

    def test_dashboard_hotkeys_has_fallback(self):
        """DASHBOARD_HTML 应有 hotkeys-js 加载失败的降级策略。"""
        assert "addEventListener('keydown'" in DASHBOARD_HTML, "Dashboard 缺少 keydown 降级策略"


class TestStage4RenderingIntegrity:
    """集成测试：验证 Stage 4 工具集成后模板仍能正确渲染。"""

    def test_dashboard_renders_with_notyf(self):
        """仪表盘模板渲染后应包含 Notyf。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        html = render_dashboard(output_dir)
        assert "notyf" in html.lower()
        assert "new Notyf" in html

    def test_player_renders_with_hotkeys(self):
        """播放器模板渲染后应包含 hotkeys-js。"""
        html = render_player()
        assert "hotkeys" in html.lower()
        assert "notyf" in html.lower()

    def test_project_renders_with_clipboard(self):
        """项目模板渲染后应包含 clipboard.js。"""
        output_dir = Path(__file__).parent.parent / "output_demo"
        if not output_dir.exists():
            pytest.skip("output_demo 目录不存在")
        projects = list(output_dir.iterdir())
        md_files = [p for p in projects if p.suffix == ".md"]
        if not md_files:
            pytest.skip("无可用项目数据")
        name = md_files[0].stem
        html = render_project(output_dir, "output_demo", name)
        assert "clipboard" in html.lower() or "未找到" in html
        assert "notyf" in html.lower() or "未找到" in html


class TestStage4SystemIntegration:
    """系统测试：验证 Stage 4 工具集成不影响系统功能。"""

    def test_server_imports_with_stage4_tools(self):
        """引入 Stage 4 工具后服务器模块应仍能正常导入。"""
        from gh_trending_audio.web.server import create_server

        assert create_server is not None

    def test_no_format_conflicts_with_stage4(self):
        """Stage 4 工具的花括号不应与 str.format() 冲突。"""
        try:
            render_player()
        except (ValueError, KeyError) as e:
            pytest.fail(f"Player 模板因 Stage 4 工具格式化失败: {e}")

        output_dir = Path(__file__).parent.parent / "output_demo"
        if output_dir.exists():
            try:
                render_dashboard(output_dir)
            except (ValueError, KeyError) as e:
                pytest.fail(f"Dashboard 模板因 Stage 4 工具格式化失败: {e}")


class TestStage5BugFixes:
    """Stage 5 bug 修复验证：确认 WaveSurfer v7 API 和进度条更新修复。"""

    def test_no_deprecated_getTime_calls(self):
        """确认代码中不存在已废弃的 wavesurfer.getTime() 调用。"""
        assert "wavesurfer.getTime()" not in PLAYER_HTML, \
            "仍存在已废弃的 getTime() 调用，应替换为 getCurrentTime()"

    def test_getCurrentTime_used_in_updateProgress(self):
        """updateProgress 函数应使用 getCurrentTime()。"""
        assert "var seek = wavesurfer.getCurrentTime()" in PLAYER_HTML, \
            "updateProgress 未使用 getCurrentTime()"

    def test_getCurrentTime_used_in_hotkeys(self):
        """hotkeys-js 快捷键应使用 getCurrentTime() 进行快进/快退。"""
        assert "wavesurfer.setTime(wavesurfer.getCurrentTime() + 10)" in PLAYER_HTML, \
            "hotkeys 右箭头未使用 getCurrentTime()"
        assert "wavesurfer.setTime(wavesurfer.getCurrentTime() - 10)" in PLAYER_HTML, \
            "hotkeys 左箭头未使用 getCurrentTime()"

    def test_getCurrentTime_used_in_pagehide(self):
        """pagehide 事件应使用 getCurrentTime() 保存会话。"""
        assert "wavesurfer.getCurrentTime()," in PLAYER_HTML, \
            "pagehide 未使用 getCurrentTime()"

    def test_requestAnimationFrame_in_play_event(self):
        """play 事件处理器应包含 requestAnimationFrame(updateProgress) 以重启进度条更新。"""
        # 找到 play 事件处理器中的 requestAnimationFrame
        assert "wavesurfer.on('play'" in PLAYER_HTML, "缺少 play 事件监听"
        # 确认 play 事件中有 requestAnimationFrame
        play_event_idx = PLAYER_HTML.index("wavesurfer.on('play'")
        play_event_block = PLAYER_HTML[play_event_idx:play_event_idx + 500]
        assert "requestAnimationFrame(updateProgress)" in play_event_block, \
            "play 事件处理器中缺少 requestAnimationFrame(updateProgress)，进度条不会在手动播放时更新"


class TestStage5Features:
    """Stage 5 新功能验证：CountUp.js, SortableJS, ECharts 集成。"""

    def test_countup_cdn_loaded(self):
        """Dashboard 应加载 CountUp.js CDN。"""
        assert "countup.js@" in DASHBOARD_HTML.lower() or "countUp" in DASHBOARD_HTML, \
            "缺少 CountUp.js CDN"

    def test_countup_stat_ids_exist(self):
        """统计卡片数字应有 id 用于 CountUp 动画。"""
        assert 'id="stat-projects"' in DASHBOARD_HTML, "缺少 stat-projects id"
        assert 'id="stat-audio"' in DASHBOARD_HTML, "缺少 stat-audio id"

    def test_sortable_cdn_loaded(self):
        """Dashboard 应加载 SortableJS CDN。"""
        assert "sortablejs" in DASHBOARD_HTML.lower() or "Sortable" in DASHBOARD_HTML, \
            "缺少 SortableJS CDN"

    def test_echarts_cdn_loaded(self):
        """Dashboard 应加载 ECharts CDN。"""
        assert "echarts" in DASHBOARD_HTML.lower(), \
            "缺少 ECharts CDN"

    def test_charts_container_exists(self):
        """Dashboard 应包含图表容器。"""
        assert 'id="langChart"' in DASHBOARD_HTML, "缺少 langChart 容器"
        assert 'id="starsChart"' in DASHBOARD_HTML, "缺少 starsChart 容器"
        assert 'id="durationChart"' in DASHBOARD_HTML, "缺少 durationChart 容器"
        assert 'id="chartsSection"' in DASHBOARD_HTML, "缺少 chartsSection 容器"

    def test_echarts_init_code_exists(self):
        """Dashboard 应包含 ECharts 初始化代码。"""
        assert "echarts.init" in DASHBOARD_HTML, "缺少 ECharts 初始化代码"

    def test_countup_initialization_code_exists(self):
        """Dashboard 应包含 CountUp.js 初始化代码。"""
        assert "countUp.CountUp" in DASHBOARD_HTML or "new CountUp" in DASHBOARD_HTML, \
            "缺少 CountUp.js 初始化代码"

    def test_sortable_initialization_code_exists(self):
        """Dashboard 应包含 SortableJS 初始化代码。"""
        assert "Sortable.create" in DASHBOARD_HTML, "缺少 SortableJS 初始化代码"

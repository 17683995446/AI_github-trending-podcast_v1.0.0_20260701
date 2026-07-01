"""HTTP request handler for the web dashboard.

``DashboardHandler`` retains every method that needs access to ``self`` (the
HTTP request/response cycle). Pure helpers (data scanning, markdown parsing,
GitHub API access, code search) live in :mod:`gh_trending_audio.web.utils`.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from .templates import DASHBOARD_HTML, PLAYER_HTML, PROJECT_HTML
from .utils import (
    _CodeSearchUnavailable,
    build_repo_from_md,
    get_project_detail,
    github_api_get,
    github_code_search,
    local_code_search,
    markdown_to_html,
    normalize_repo_slug,
    scan_projects,
)

# 项目根目录（等价于原 web_dashboard.py 中 BASE_DIR = Path(__file__).parent.resolve()，
# 即 web_dashboard.py 所在的项目根目录，output_* 子目录位于其下）
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
OUTPUT_DIR = BASE_DIR  # 输出目录默认在项目根下

# GitHub 仓库文件树/文件内容缓存（避免重复请求 GitHub API，借鉴 CodeFlow/Greptile）
_FILETREE_CACHE: dict[str, dict] = {}
_FILE_CONTENT_CACHE: dict[str, dict] = {}


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format, *args):
        """静默日志（用 rich 代替）"""
        pass

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 路由
        if path == "/" or path == "/dashboard":
            self._serve_dashboard()
        elif path == "/player":
            self._serve_player_page()
        elif path == "/api/projects":
            self._serve_api_projects()
        elif path.startswith("/api/project/"):
            # 格式: /api/project/{dir}/{name}
            remaining = urllib.parse.unquote(path.replace("/api/project/", ""))
            parts = remaining.split("/", 1)
            if len(parts) == 2:
                self._serve_api_project(parts[0], parts[1])
            else:
                self._serve_api_project("", parts[0])
        elif path.startswith("/project/"):
            # 格式: /project/{dir}/{name}
            remaining = urllib.parse.unquote(path.replace("/project/", ""))
            parts = remaining.split("/", 1)
            if len(parts) == 2:
                self._serve_project_page(parts[0], parts[1])
            else:
                self._serve_project_page("", parts[0])
        elif path.startswith("/r/"):
            # 快捷 URL 跳转（借鉴 Zread.ai 地址栏替换域名的快捷方式）：
            #   /r/owner/repo   或   /r/owner_repo
            self._handle_quick_route(parsed)
        elif path.startswith("/file/"):
            filepath = urllib.parse.unquote(path.replace("/file/", ""))
            self._serve_file(filepath)
        elif path == "/api/stats":
            self._serve_api_stats()
        elif path == "/api/run":
            self._serve_api_run(urllib.parse.parse_qs(parsed.query))
        elif path == "/api/status":
            self._serve_api_status()
        elif path == "/api/filetree":
            self._serve_api_filetree(urllib.parse.parse_qs(parsed.query))
        elif path == "/api/file":
            self._serve_api_file(urllib.parse.parse_qs(parsed.query))
        elif path == "/api/community":
            self._serve_api_community(urllib.parse.parse_qs(parsed.query))
        elif path == "/api/readme":
            self._serve_api_readme(urllib.parse.parse_qs(parsed.query))
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        """处理 POST 请求"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                params = {}
            self._start_pipeline(params)
        elif path == "/api/compare":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                params = {}
            self._start_comparison(params)
        elif path == "/api/ask":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                params = {}
            self._handle_ask(params)
        elif path == "/api/search-code":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                params = {}
            self._handle_search_code(params)
        elif path == "/api/onboarding":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                params = json.loads(body) if body else {}
            except json.JSONDecodeError:
                params = {}
            self._handle_onboarding(params)
        elif path.startswith("/api/delete/"):
            """删除项目（POST 方式，兼容性更好）"""
            remaining = urllib.parse.unquote(path.replace("/api/delete/", ""))
            parts = remaining.split("/", 1)
            if len(parts) == 2:
                self._delete_project(parts[0], parts[1])
            else:
                self._delete_project("", parts[0])
        else:
            self._send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        """处理 DELETE 请求"""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/project/"):
            remaining = urllib.parse.unquote(path.replace("/api/project/", ""))
            parts = remaining.split("/", 1)
            if len(parts) == 2:
                self._delete_project(parts[0], parts[1])
            else:
                self._delete_project("", parts[0])
        else:
            self._send_json(404, {"error": "Not found"})

    def _delete_project(self, dir_name: str, proj_name: str):
        """删除项目的所有文件（md、script、mp3）"""
        import shutil as _shutil

        if not dir_name:
            # 找到项目所在目录
            projects = scan_projects(OUTPUT_DIR)
            for p in projects:
                if p["name"] == proj_name:
                    dir_name = p["dir"]
                    break

        if not dir_name:
            self._send_json(404, {"error": "项目未找到"})
            return

        proj_dir = OUTPUT_DIR / dir_name
        if not proj_dir.exists() or not proj_dir.is_dir():
            self._send_json(404, {"error": "目录不存在"})
            return

        deleted = []
        for suffix in [".md", "_script.txt", ".mp3"]:
            filepath = proj_dir / f"{proj_name}{suffix}"
            if filepath.exists():
                filepath.unlink()
                deleted.append(filepath.name)

        # 清理分段临时文件
        for f in proj_dir.iterdir():
            if f.name.startswith(proj_name) and f.name.endswith(".mp3") and "_seg" in f.name:
                f.unlink()
                deleted.append(f.name)

        # 如果目录空了，删除目录
        remaining = list(proj_dir.iterdir())
        if not remaining:
            _shutil.rmtree(proj_dir)

        self._send_json(200, {"deleted": deleted, "project": proj_name})

    # ------------------------------------------------------------------
    # 页面
    # ------------------------------------------------------------------

    def _serve_dashboard(self):
        """主仪表盘页面"""
        html = self._render_dashboard_html()
        self._send_html(html)

    def _serve_player_page(self):
        """音乐播放器页面"""
        self._send_html(PLAYER_HTML.format())

    def _serve_project_page(self, dir_name: str, name: str):
        """单个项目详情页"""
        html = self._render_project_html(dir_name, name)
        self._send_html(html)

    def _handle_quick_route(self, parsed):
        """快捷 URL 跳转（借鉴 Zread.ai「在地址栏替换域名即可访问」的快捷方式）。

        支持两种写法：
          /r/owner/repo   —— GitHub 风格 slug
          /r/owner_repo   —— 下划线风格（与本地项目名一致）

        - 已存在该项目：302 跳转到 /project/{dir}/{name}（详情页）
        - 不存在：302 跳转到 /?auto_generate=owner/repo，前端检测参数后自动触发生成
        """
        raw = urllib.parse.unquote(parsed.path[len("/r/"):]).strip().strip("/")
        if not raw:
            self._send_redirect("/")
            return

        # 解析 owner / repo
        if "/" in raw:
            segs = [s for s in raw.split("/") if s]
            if len(segs) >= 2:
                owner, repo = segs[0], segs[1]
                proj_name = "{}_{}".format(owner, repo)
                slug = "{}/{}".format(owner, repo)
            else:
                proj_name = segs[0]
                slug = segs[0]
        else:
            proj_name = raw
            # 尝试还原 owner/repo（取第一个下划线作为分隔）
            if "_" in raw:
                owner, _, repo = raw.partition("_")
                slug = "{}/{}".format(owner, repo) if repo else raw
            else:
                slug = raw

        project = self._find_project_by_name(proj_name)
        if project:
            target = "/project/{}/{}".format(
                urllib.parse.quote(project["dir"], safe=""),
                urllib.parse.quote(project["name"], safe=""),
            )
        else:
            target = "/?auto_generate={}".format(urllib.parse.quote(slug, safe="/"))
        self._send_redirect(target)

    def _find_project_by_name(self, name: str) -> dict | None:
        """按项目名（owner_repo）快速查找已存在的项目。

        直接遍历 output_* 目录检查 {name}.md 是否存在，不扫描完整元数据，
        避免 _scan_projects 中 ffprobe 的开销，保证 /r/ 跳转足够快。
        多个目录含同一项目时，按 .md 修改时间取最新的一份。
        """
        if not name:
            return None
        try:
            out_dirs = [d for d in OUTPUT_DIR.iterdir()
                        if d.is_dir() and d.name.startswith("output")]
        except Exception:
            return None

        def _mtime(path):
            try:
                return path.stat().st_mtime
            except Exception:
                return 0

        best = None  # (mtime, dir, stem)
        # 精确匹配 {name}.md
        for d in out_dirs:
            f = d / "{}.md".format(name)
            if f.exists():
                m = _mtime(f)
                if best is None or m > best[0]:
                    best = (m, d, name)
        if best:
            return {"dir": best[1].name, "name": best[2]}

        # 忽略大小写兜底
        low = name.lower()
        for d in out_dirs:
            try:
                for f in d.iterdir():
                    if f.suffix == ".md" and f.stem.lower() == low:
                        m = _mtime(f)
                        if best is None or m > best[0]:
                            best = (m, d, f.stem)
            except Exception:
                continue
        if best:
            return {"dir": best[1].name, "name": best[2]}
        return None

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def _serve_api_projects(self):
        """返回所有项目列表（JSON）"""
        projects = scan_projects(OUTPUT_DIR)
        self._send_json(200, {"projects": projects, "total": len(projects)})

    def _serve_api_project(self, dir_name: str, proj_name: str):
        """返回单个项目详情（JSON）"""
        project = get_project_detail(OUTPUT_DIR, dir_name, proj_name)
        if project:
            self._send_json(200, project)
        else:
            self._send_json(404, {"error": "Project not found"})

    def _serve_api_stats(self):
        """返回统计数据"""
        projects = scan_projects(OUTPUT_DIR)
        total_md = sum(1 for p in projects if p.get("has_md"))
        total_script = sum(1 for p in projects if p.get("has_script"))
        total_audio = sum(1 for p in projects if p.get("has_audio"))
        total_size = sum(p.get("total_size", 0) for p in projects)

        self._send_json(200, {
            "total_projects": len(projects),
            "total_markdown": total_md,
            "total_scripts": total_script,
            "total_audio": total_audio,
            "total_size_kb": round(total_size / 1024, 1),
        })

    def _serve_api_run(self, params):
        """GET 方式触发任务（兼容）"""
        self._start_pipeline(params)

    def _serve_api_status(self):
        """返回任务状态"""
        self._send_json(200, {
            "running": getattr(self.server, "pipeline_running", False),
            "last_result": getattr(self.server, "last_result", None),
            "last_error": getattr(self.server, "last_error", None),
        })

    def _start_pipeline(self, params: dict):
        """启动后台流水线任务"""
        if getattr(self.server, "pipeline_running", False):
            self._send_json(409, {"error": "已有任务在运行中，请等待完成"})
            return

        # 在后台线程中运行
        def run_task():
            self.server.pipeline_running = True
            self.server.last_error = None
            try:
                from gh_trending_audio.github_fetcher import GitHubFetcher
                from gh_trending_audio.document_generator import DocumentGenerator
                from gh_trending_audio.tts_engine import TTSEngine

                days = int(params.get("days", 7))
                limit = int(params.get("limit", 3))
                language = params.get("language") or None
                min_stars = int(params.get("min_stars", 50))
                topic = params.get("topic") or None
                lang = params.get("lang", "zh")
                use_llm = params.get("use_llm", True)  # 默认启用 LLM
                style = params.get("style", "dialogue")
                token = params.get("token") or None
                repo_url = params.get("repo_url") or None

                output_dir = params.get("output", f"output_{int(time.time())}")
                output_path = OUTPUT_DIR / output_dir
                output_path.mkdir(parents=True, exist_ok=True)

                # Step 1: 获取项目
                from gh_trending_audio.config import GITHUB_TOKEN as DEFAULT_TOKEN
                fetcher = GitHubFetcher(token=token or DEFAULT_TOKEN)
                if repo_url:
                    # 单仓库模式：直接处理用户指定的仓库（忽略趋势参数，跳过去重）
                    repos = [fetcher.fetch_single_repo(repo_url)]
                else:
                    repos = fetcher.fetch_trending(
                        days=days, limit=limit, language=language,
                        min_stars=min_stars, topic=topic,
                    )

                doc_count = 0
                audio_count = 0
                skipped = 0

                for repo in repos:
                    safe_name = repo.full_name.replace("/", "_")
                    md_filename = f"{safe_name}.md"

                    # 去重：检查是否已在任何 output_* 目录中存在
                    # （单仓库模式跳过，允许用户重新生成）
                    if not repo_url:
                        already = False
                        for d in OUTPUT_DIR.iterdir():
                            if d.is_dir() and d.name.startswith("output"):
                                if (d / md_filename).exists():
                                    already = True
                                    break
                        if already:
                            skipped += 1
                            continue

                    fetcher.enrich_with_readme(repo)
                    if use_llm:
                        fetcher.enrich_with_details(repo)
                    gen = DocumentGenerator(language=lang, use_llm=use_llm, style=style)
                    doc = gen.generate(repo)
                    md_path = output_path / f"{safe_name}.md"
                    script_path = output_path / f"{safe_name}_script.txt"
                    doc.save(str(md_path), str(script_path))
                    doc_count += 1

                    # 尝试合成音频
                    audio_path = output_path / f"{safe_name}.mp3"
                    try:
                        tts = TTSEngine(language=lang, style=style)
                        tts.text_to_speech(doc.audio_script, str(audio_path))
                        audio_count += 1
                    except Exception:
                        pass

                self.server.last_result = {
                    "output_dir": output_dir,
                    "doc_count": doc_count,
                    "audio_count": audio_count,
                    "skipped": skipped,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            except Exception as e:
                self.server.last_error = str(e)
            finally:
                self.server.pipeline_running = False

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        self._send_json(202, {
            "status": "started",
            "message": "任务已启动，请轮询 /api/status 查看进度",
        })

    def _start_comparison(self, params: dict):
        """启动多仓库对比任务（借鉴 Zread.ai 的多仓库对比能力）

        接收 {"projects": [{"dir": "...", "name": "..."}, ...]}，
        读取每个项目的 Markdown 文档作为分析上下文，
        调用 LLMEnhancer.generate_comparison 生成对比文档和脚本，
        保存到 output_comparison/ 目录并合成 TTS 音频。
        """
        if getattr(self.server, "pipeline_running", False):
            self._send_json(409, {"error": "已有任务在运行中，请等待完成"})
            return

        projects = params.get("projects") or []
        if not isinstance(projects, list) or len(projects) < 2:
            self._send_json(400, {"error": "对比至少需要选择 2 个项目"})
            return
        if len(projects) > 3:
            projects = projects[:3]

        # 预校验：所有项目文档必须存在
        for p in projects:
            pdir = OUTPUT_DIR / p.get("dir", "")
            pname = p.get("name", "")
            if not (pdir / f"{pname}.md").exists():
                self._send_json(404, {"error": f"项目文档不存在: {pname}"})
                return

        style = params.get("style", "dialogue")
        lang = params.get("lang", "zh")

        def run_task():
            self.server.pipeline_running = True
            self.server.last_error = None
            try:
                from gh_trending_audio.llm_enhancer import LLMEnhancer
                from gh_trending_audio.github_fetcher import RepoInfo
                from gh_trending_audio.tts_engine import TTSEngine

                enhancer = LLMEnhancer(language=lang, style=style)

                repos: list = []
                analyses: list[str] = []
                for p in projects:
                    pdir = OUTPUT_DIR / p["dir"]
                    pname = p["name"]
                    md_path = pdir / f"{pname}.md"
                    md_text = md_path.read_text(encoding="utf-8", errors="replace")
                    repo = build_repo_from_md(pname, md_text)
                    repos.append(repo)
                    # 读取 Markdown 文档作为分析上下文（截断防止 token 超限）
                    analyses.append(md_text[:4000])

                # 生成对比文档和脚本
                markdown, audio_script = enhancer.generate_comparison(repos, analyses)

                # 保存到 output_comparison/ 目录
                comp_dir = OUTPUT_DIR / "output_comparison"
                comp_dir.mkdir(parents=True, exist_ok=True)
                base_name = "compare_" + "_vs_".join(r.name for r in repos)
                md_path = comp_dir / f"{base_name}.md"
                script_path = comp_dir / f"{base_name}_script.txt"
                md_path.write_text(markdown, encoding="utf-8")
                script_path.write_text(audio_script, encoding="utf-8")

                # 合成 TTS 音频
                audio_ok = False
                audio_path = comp_dir / f"{base_name}.mp3"
                try:
                    tts = TTSEngine(language=lang, style=style)
                    tts.text_to_speech(audio_script, str(audio_path))
                    audio_ok = True
                except Exception:
                    pass

                self.server.last_result = {
                    "type": "comparison",
                    "output_dir": "output_comparison",
                    "name": base_name,
                    "project_url": f"/project/output_comparison/{base_name}",
                    "doc_count": 1,
                    "audio_count": 1 if audio_ok else 0,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            except Exception as e:
                self.server.last_error = str(e)
            finally:
                self.server.pipeline_running = False

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()

        self._send_json(202, {
            "status": "started",
            "message": "对比任务已启动，请轮询 /api/status 查看进度",
        })

    def _handle_ask(self, params: dict):
        """处理项目问答：基于项目文档调用 LLM 回答用户问题（DeepWiki 式交互）"""
        import urllib.request
        import urllib.error

        question = (params.get("question") or "").strip()
        dir_name = params.get("dir") or ""
        proj_name = params.get("project") or ""

        if not question:
            self._send_json(400, {"error": "问题不能为空"})
            return
        if not proj_name:
            self._send_json(400, {"error": "项目名不能为空"})
            return

        # 定位项目目录（未指定目录时扫描所有输出目录）
        proj_dir = OUTPUT_DIR / dir_name if dir_name else None
        if proj_dir is None or not proj_dir.exists():
            for p in scan_projects(OUTPUT_DIR):
                if p["name"] == proj_name:
                    proj_dir = OUTPUT_DIR / p["dir"]
                    dir_name = p["dir"]
                    break
        if proj_dir is None or not proj_dir.exists():
            self._send_json(404, {"error": "项目目录不存在"})
            return

        md_path = proj_dir / f"{proj_name}.md"
        script_path = proj_dir / f"{proj_name}_script.txt"
        if not md_path.exists():
            self._send_json(404, {"error": "项目文档不存在"})
            return

        # 读取项目文档和脚本作为上下文
        context_parts = []
        try:
            md_text = md_path.read_text(encoding="utf-8", errors="replace")
            context_parts.append("【项目文档】\n" + md_text[:6000])
        except Exception as e:
            self._send_json(500, {"error": f"读取文档失败: {e}"})
            return

        if script_path.exists():
            try:
                script_text = script_path.read_text(encoding="utf-8", errors="replace")
                context_parts.append("【对话脚本】\n" + script_text[:3000])
            except Exception:
                pass

        context = "\n\n".join(context_parts)

        # 调用硅基流动 LLM API（OpenAI 兼容接口）
        try:
            from gh_trending_audio.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

            if not LLM_API_KEY:
                self._send_json(500, {"error": "LLM API Key 未配置，请在 config.py 中设置 LLM_API_KEY"})
                return

            system_prompt = "你是项目技术助手，基于以下项目文档回答用户问题。用中文回答，简洁专业。"
            user_prompt = f"项目上下文：\n{context}\n\n用户问题：{question}"

            payload = json.dumps({
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 1500,
            }, ensure_ascii=False).encode("utf-8")

            url = LLM_BASE_URL.rstrip("/") + "/chat/completions"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            answer = result["choices"][0]["message"]["content"].strip()
            self._send_json(200, {"answer": answer})
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            self._send_json(502, {"error": f"LLM API 请求失败 ({e.code}): {err_body[:200]}"})
        except Exception as e:
            self._send_json(500, {"error": f"调用 LLM 失败: {e}"})

    def _handle_onboarding(self, params: dict):
        """生成受众定制的新手入门指南（借鉴 Zread.ai 受众定制化入门指南）

        读取项目 Markdown 文档作为上下文，调用 LLM 为指定受众
        （新手 / 开发者 / 架构师）生成 Markdown 格式的入门指南。
        """
        dir_name = params.get("dir") or ""
        proj_name = params.get("project") or ""
        audience = (params.get("audience") or "beginner").strip()

        if not proj_name:
            self._send_json(400, {"error": "项目名不能为空"})
            return

        valid_audiences = {"beginner", "developer", "architect"}
        if audience not in valid_audiences:
            self._send_json(
                400, {"error": "audience 必须是 beginner / developer / architect 之一"}
            )
            return

        # 定位项目目录（未指定目录时扫描所有输出目录）
        proj_dir = OUTPUT_DIR / dir_name if dir_name else None
        if proj_dir is None or not proj_dir.exists():
            for p in scan_projects(OUTPUT_DIR):
                if p["name"] == proj_name:
                    proj_dir = OUTPUT_DIR / p["dir"]
                    dir_name = p["dir"]
                    break
        if proj_dir is None or not proj_dir.exists():
            self._send_json(404, {"error": "项目目录不存在"})
            return

        md_path = proj_dir / f"{proj_name}.md"
        if not md_path.exists():
            self._send_json(404, {"error": "项目文档不存在，无法生成入门指南"})
            return

        # 读取项目文档作为上下文
        try:
            md_text = md_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self._send_json(500, {"error": f"读取文档失败: {e}"})
            return

        # 从项目名 + Markdown 构建 RepoInfo（复用对比分析的构建逻辑）
        repo_info = build_repo_from_md(proj_name, md_text)

        # 调用 LLMEnhancer 生成受众定制入门指南
        try:
            from gh_trending_audio.llm_enhancer import LLMEnhancer

            enhancer = LLMEnhancer()
            guide = enhancer.generate_onboarding(repo_info, md_text, audience)
            self._send_json(200, {"guide": guide})
        except ValueError as e:
            self._send_json(500, {"error": f"LLM 配置错误：{e}"})
        except ImportError as e:
            self._send_json(
                500, {"error": f"缺少依赖（请安装 openai 库：pip install openai）：{e}"}
            )
        except Exception as e:
            self._send_json(502, {"error": f"生成入门指南失败：{e}"})

    # ------------------------------------------------------------------
    # GitHub 仓库文件树浏览（借鉴 CodeFlow / Greptile 代码浏览能力）
    # ------------------------------------------------------------------

    def _serve_api_readme(self, params):
        """GET /api/readme?repo=owner/repo —— 返回仓库 README 原文

        调用 GitHub API 获取 README，支持多种文件名（README.md, README.rst 等）。
        结果缓存。
        """
        repo = (params.get("repo", [""])[0] or "").strip()
        if not repo or "/" not in repo:
            self._send_json(400, {"error": "缺少 repo 参数（格式：owner/repo）"})
            return

        cache_key = f"readme:{repo}"
        if cache_key in _FILE_CONTENT_CACHE:
            self._send_json(200, _FILE_CONTENT_CACHE[cache_key])
            return

        # GitHub API: GET /repos/{owner}/{repo}/readme 返回 base64 编码的 README
        url = f"https://api.github.com/repos/{repo}/readme"
        status, data = github_api_get(url)
        if status != 200 or not isinstance(data, dict):
            err = data if isinstance(data, str) else "未知错误"
            self._send_json(502, {"error": f"获取 README 失败 ({status}): {err[:200]}"})
            return

        import base64
        content_b64 = data.get("content", "")
        encoding = data.get("encoding", "base64")
        readme_path = data.get("path", "README.md")
        html_url = data.get("html_url", "")

        if encoding == "base64":
            try:
                readme_text = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                readme_text = ""
        else:
            readme_text = content_b64

        # 限制大小（200KB）
        if len(readme_text) > 204800:
            readme_text = readme_text[:204800] + "\n\n... (README 已截断，完整内容请访问 GitHub)"

        result = {
            "repo": repo,
            "path": readme_path,
            "content": readme_text,
            "html_url": html_url,
            "size": len(readme_text),
        }
        _FILE_CONTENT_CACHE[cache_key] = result
        self._send_json(200, result)

    def _serve_api_filetree(self, params):
        """GET /api/filetree?repo=owner/repo —— 返回仓库递归文件树

        调用 GitHub API：
          1. GET /repos/{owner}/{repo} 获取默认分支
          2. GET /repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1
        结果缓存，避免重复请求。
        """
        repo = (params.get("repo", [""])[0] or "").strip()
        if not repo or "/" not in repo:
            self._send_json(400, {"error": "缺少 repo 参数（格式：owner/repo）"})
            return

        cache_key = repo
        if cache_key in _FILETREE_CACHE:
            self._send_json(200, _FILETREE_CACHE[cache_key])
            return

        # 1. 获取默认分支
        status, repo_info = github_api_get(
            f"https://api.github.com/repos/{repo}"
        )
        if status != 200 or not isinstance(repo_info, dict):
            err = repo_info if isinstance(repo_info, str) else "未知错误"
            self._send_json(502, {"error": f"获取仓库信息失败 ({status}): {err[:200]}"})
            return
        default_branch = repo_info.get("default_branch") or "main"

        # 2. 获取递归文件树
        status, tree_data = github_api_get(
            f"https://api.github.com/repos/{repo}/git/trees/{default_branch}?recursive=1"
        )
        if status != 200 or not isinstance(tree_data, dict):
            err = tree_data if isinstance(tree_data, str) else "未知错误"
            self._send_json(502, {"error": f"获取文件树失败 ({status}): {err[:200]}"})
            return

        result = {
            "repo": repo,
            "default_branch": default_branch,
            "tree": tree_data.get("tree", []),
            "truncated": tree_data.get("truncated", False),
        }
        _FILETREE_CACHE[cache_key] = result
        self._send_json(200, result)

    def _serve_api_file(self, params):
        """GET /api/file?repo=owner/repo&path=src/main.py —— 返回文件内容

        调用 GitHub API GET /repos/{owner}/{repo}/contents/{path}，
        将 base64 内容解码后返回；限制 100KB 以内；结果缓存。
        """
        import base64

        repo = (params.get("repo", [""])[0] or "").strip()
        file_path = (params.get("path", [""])[0] or "").strip()
        if not repo or "/" not in repo:
            self._send_json(400, {"error": "缺少 repo 参数（格式：owner/repo）"})
            return
        if not file_path:
            self._send_json(400, {"error": "缺少 path 参数"})
            return

        cache_key = f"{repo}:{file_path}"
        if cache_key in _FILE_CONTENT_CACHE:
            self._send_json(200, _FILE_CONTENT_CACHE[cache_key])
            return

        encoded_path = urllib.parse.quote(file_path, safe="/")
        url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"
        status, data = github_api_get(url)
        if status != 200 or not isinstance(data, dict):
            err = data if isinstance(data, str) else "未知错误"
            self._send_json(502, {"error": f"获取文件内容失败 ({status}): {err[:200]}"})
            return

        size = data.get("size", 0)
        MAX_FILE_SIZE = 100 * 1024  # 100KB
        if size > MAX_FILE_SIZE:
            self._send_json(413, {"error": f"文件过大（{size} 字节），限制 100KB 以内"})
            return

        content_b64 = data.get("content", "") or ""
        encoding = data.get("encoding", "base64")
        try:
            if encoding == "base64":
                content = base64.b64decode(content_b64).decode(
                    "utf-8", errors="replace"
                )
            else:
                content = content_b64
        except Exception as e:
            self._send_json(500, {"error": f"解码文件失败: {e}"})
            return

        result = {
            "path": file_path,
            "size": size,
            "content": content,
            "encoding": "utf-8",
        }
        _FILE_CONTENT_CACHE[cache_key] = result
        self._send_json(200, result)

    # ------------------------------------------------------------------
    # 社区洞察（借鉴 Zread.ai 的社区讨论摘要能力）
    # ------------------------------------------------------------------

    def _serve_api_community(self, params):
        """GET /api/community?repo=owner/repo —— 社区洞察

        并行调用以下 GitHub API，汇总仓库的社区活跃度信息：
          1. GET /repos/{owner}/{repo}/issues?state=open&per_page=10&sort=comments
             → 热门 issues（按评论数排序，过滤掉 PR）
          2. GET /repos/{owner}/{repo}/pulls?state=open&per_page=5&sort=updated
             → 活跃 PRs
          3. GET /repos/{owner}/{repo}/contributors?per_page=5
             → 核心贡献者
          4. GET /repos/{owner}/{repo}/releases?per_page=3
             → 最新版本
          5. GET /repos/{owner}/{repo}
             → 基本信息（stars/forks/open_issues/topics/created_at/pushed_at）

        使用 config.py 中的 GITHUB_TOKEN（若有）提高配额（由 github_api_get 统一注入）。
        错误处理：某个 API 失败时，对应字段返回空数组/空对象，不影响其他字段。
        """
        repo = (params.get("repo", [""])[0] or "").strip()
        if not repo or "/" not in repo:
            self._send_json(400, {"error": "缺少 repo 参数（格式：owner/repo）"})
            return

        base = f"https://api.github.com/repos/{repo}"

        results: dict = {
            "repo_info": {},
            "hot_issues": [],
            "active_prs": [],
            "contributors": [],
            "releases": [],
        }

        def fetch_issues():
            status, data = github_api_get(
                f"{base}/issues?state=open&per_page=10&sort=comments"
            )
            if status == 200 and isinstance(data, list):
                items = []
                for it in data:
                    # GitHub issues 端点会同时返回 PR，过滤掉纯 PR（避免与 active_prs 重复）
                    if it.get("pull_request"):
                        continue
                    labels = [lb.get("name", "") for lb in (it.get("labels") or [])]
                    items.append({
                        "number": it.get("number"),
                        "title": it.get("title", ""),
                        "comments": it.get("comments", 0),
                        "url": it.get("html_url", ""),
                        "labels": labels,
                    })
                results["hot_issues"] = items

        def fetch_prs():
            status, data = github_api_get(
                f"{base}/pulls?state=open&per_page=5&sort=updated"
            )
            if status == 200 and isinstance(data, list):
                items = []
                for pr in data:
                    user = (pr.get("user") or {}).get("login", "")
                    items.append({
                        "number": pr.get("number"),
                        "title": pr.get("title", ""),
                        "user": user,
                        "url": pr.get("html_url", ""),
                    })
                results["active_prs"] = items

        def fetch_contributors():
            status, data = github_api_get(
                f"{base}/contributors?per_page=5"
            )
            if status == 200 and isinstance(data, list):
                items = []
                for c in data:
                    items.append({
                        "login": c.get("login", ""),
                        "contributions": c.get("contributions", 0),
                        "avatar_url": c.get("avatar_url", ""),
                    })
                results["contributors"] = items

        def fetch_releases():
            status, data = github_api_get(
                f"{base}/releases?per_page=3"
            )
            if status == 200 and isinstance(data, list):
                items = []
                for r in data:
                    items.append({
                        "tag": r.get("tag_name", ""),
                        "name": r.get("name", ""),
                        "published_at": r.get("published_at", ""),
                        "url": r.get("html_url", ""),
                    })
                results["releases"] = items

        def fetch_repo_info():
            status, data = github_api_get(base)
            if status == 200 and isinstance(data, dict):
                results["repo_info"] = {
                    "stars": data.get("stargazers_count", 0),
                    "forks": data.get("forks_count", 0),
                    "open_issues": data.get("open_issues_count", 0),
                    "topics": data.get("topics", []) or [],
                    "created_at": data.get("created_at", ""),
                    "pushed_at": data.get("pushed_at", ""),
                }

        # 并行请求以加速（每个线程写入不同 key，互不冲突）
        threads = [
            threading.Thread(target=fetch_issues),
            threading.Thread(target=fetch_prs),
            threading.Thread(target=fetch_contributors),
            threading.Thread(target=fetch_releases),
            threading.Thread(target=fetch_repo_info),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=25)

        self._send_json(200, results)

    # ------------------------------------------------------------------
    # 语义代码搜索（借鉴 Greptile 的自然语言代码搜索能力）
    # ------------------------------------------------------------------

    def _handle_search_code(self, params: dict):
        """POST /api/search-code —— 自然语言/代码模式搜索项目源码。

        优先调用 GitHub Code Search API（需要 Token），不可用时回退到
        Repomix 拉取代码 + 本地正则搜索函数/类/import 定义。

        入参：{"repo": "owner/repo", "query": "...", "language": "python"}
        返回：{"results": [...], "total": N, "source": "github"|"local", "elapsed_ms": ...}
        """
        start = time.time()
        repo_input = (params.get("repo") or params.get("project") or "").strip()
        # 注意：query 不做 strip()，保留尾部空格等有意义字符
        # （如快捷标签 "def " 需匹配 "def " 而非 "define"）；仅用于判空
        query = params.get("query") or ""
        language = (params.get("language") or "").strip()

        if not query.strip():
            self._send_json(400, {"error": "搜索词不能为空"})
            return

        # 兼容 owner_repo 与 owner/repo 两种形式，统一成 owner/repo
        repo = normalize_repo_slug(repo_input)
        if not repo or "/" not in repo:
            self._send_json(
                400,
                {"error": "无法解析仓库名称，请提供 owner/repo 或 owner_repo 形式的项目名"},
            )
            return

        # 优先 GitHub Code Search API（需要 Token）
        from gh_trending_audio.config import GITHUB_TOKEN as DEFAULT_TOKEN
        token = (params.get("token") or DEFAULT_TOKEN or "").strip()

        source = "github"
        fallback_reason = ""
        results: list[dict] = []
        total = 0
        try:
            results, total = github_code_search(repo, query, language, token)
        except _CodeSearchUnavailable as e:
            # 无 Token / 超出配额 / 网络错误 → 回退本地搜索
            fallback_reason = str(e)
            source = "local"
            results, total = local_code_search(repo, query, language)
        except Exception as e:
            self._send_json(500, {"error": f"代码搜索失败: {e}"})
            return

        elapsed_ms = int((time.time() - start) * 1000)

        message = ""
        if source == "local" and total == 0:
            if not fallback_reason:
                fallback_reason = "GitHub Code Search API 不可用"
            message = (
                "本地回退搜索未返回结果。可能原因：未安装 repomix、仓库不可访问，"
                "或关键词未匹配。（回退原因：" + fallback_reason + "）"
            )

        self._send_json(
            200,
            {
                "results": results,
                "total": total,
                "source": source,
                "query": query,
                "elapsed_ms": elapsed_ms,
                "fallback_reason": fallback_reason,
                "message": message,
            },
        )

    # ------------------------------------------------------------------
    # 文件服务
    # ------------------------------------------------------------------

    def _serve_file(self, filepath: str):
        """提供文件下载/预览"""
        # 安全检查：防止路径穿越
        safe_path = filepath.replace("..", "").replace("\\", "/")
        full_path = OUTPUT_DIR / safe_path

        if not full_path.exists() or not full_path.is_file():
            self._send_json(404, {"error": "File not found"})
            return

        ext = full_path.suffix.lower()
        content_type = {
            ".mp3": "audio/mpeg",
            ".txt": "text/plain; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")

        with open(full_path, "rb") as f:
            data = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f"inline; filename=\"{full_path.name}\"")
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------
    # HTML 渲染
    # ------------------------------------------------------------------

    def _render_dashboard_html(self) -> str:
        """渲染仪表盘 HTML"""
        projects = scan_projects(OUTPUT_DIR)
        stats = {
            "total_projects": len(projects),
            "total_audio": sum(1 for p in projects if p["has_audio"]),
            "total_md": len(projects),
        }

        # 构建项目卡片 JSON（前端 JS 渲染，支持搜索/筛选/排序）
        import json as _json
        projects_json = _json.dumps(projects, ensure_ascii=False, default=str)

        return DASHBOARD_HTML.format(
            total_projects=stats["total_projects"],
            total_audio=stats["total_audio"],
            total_md=stats["total_md"],
            projects_json=projects_json,
        )

    def _render_project_html(self, dir_name: str, name: str) -> str:
        """渲染项目详情页"""
        detail = get_project_detail(OUTPUT_DIR, dir_name, name)
        if not detail:
            return "<h1>项目未找到</h1>"

        # Markdown 渲染
        md_html = markdown_to_html(detail["md_content"])
        # 放在 <script type="text/plain"> 中，只需转义 </script> 序列
        md_raw = detail["md_content"].replace("</script", "<\\/script") if detail.get("md_content") else ""

        # 音频播放器（含倍速控制）
        audio_player = ""
        download_audio_btn = ""
        if detail["has_audio"]:
            audio_path = detail["audio_path"]
            audio_player = f"""
                <div class="audio-player">
                    <h3>🔊 音频播放
                        <span class="section-actions">
                            <select class="speed-select" onchange="changeDetailSpeed(this)">
                                <option value="1.0">1.0x</option>
                                <option value="1.25">1.25x</option>
                                <option value="1.5">1.5x</option>
                                <option value="2.0">2.0x</option>
                            </select>
                        </span>
                    </h3>
                    <audio id="detailAudio" controls style="width:100%; max-width:600px;">
                        <source src="/file/{audio_path}" type="audio/mpeg">
                    </audio>
                </div>
            """
            download_audio_btn = f'<a class="btn btn-secondary" href="/file/{audio_path}" download>⬇ 下载音频</a>'
        else:
            audio_player = '<div class="audio-player"><p>⚠️ 此项目暂无音频文件</p></div>'

        # 下载按钮
        download_md_btn = f'<a class="btn btn-secondary" href="/file/{detail["md_path"]}" download>⬇ 下载文档</a>'

        # 脚本区域
        script_content = detail.get("script_content", "")
        script_raw = script_content.replace("</script", "<\\/script") if script_content else ""
        script_display = ""
        download_script_btn = ""
        if script_content:
            escaped = script_content.replace("<", "&lt;").replace(">", "&gt;")
            script_path = detail.get("script_path", "")
            script_display = f"""
                <div class="script-section">
                    <h3>📋 双人对话脚本
                        <span class="section-actions">
                            <button class="mini-btn" onclick="copyText('script')">📋 复制脚本</button>
                        </span>
                    </h3>
                    <pre class="script-text">{escaped}</pre>
                </div>
            """
            if script_path:
                download_script_btn = f'<a class="btn btn-secondary" href="/file/{script_path}" download>⬇ 下载脚本</a>'

        # 从 name（owner_repo 格式，如 deepseek-ai_DeepSpec）解析 GitHub owner/repo
        # 对比项目（compare_开头）不是单一仓库，不传 repo
        if name.startswith("compare_"):
            repo_full = ""  # 对比项目没有单一 GitHub 仓库
        else:
            repo_full = name.replace("_", "/", 1) if "_" in name else name

        return PROJECT_HTML.format(
            name=detail["name"],
            audio_player=audio_player,
            md_html=md_html,
            script_display=script_display,
            download_md_btn=download_md_btn,
            download_audio_btn=download_audio_btn,
            download_script_btn=download_script_btn,
            script_raw=script_raw,
            md_raw=md_raw,
            qa_dir=dir_name,
            qa_project=name,
            repo_full=repo_full,
            proj_language=detail.get("language", "") or "",
        )

    # ------------------------------------------------------------------
    # HTTP 辅助
    # ------------------------------------------------------------------

    def _send_redirect(self, location: str, status: int = 302):
        """发送 HTTP 重定向（用于 /r/ 快捷跳转）"""
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _send_html(self, html: str, status: int = 200):
        data = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

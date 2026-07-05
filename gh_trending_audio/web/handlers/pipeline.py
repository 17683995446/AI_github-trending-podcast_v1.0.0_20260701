"""流水线任务 API 处理器。

包含后台流水线启动、多仓库对比、项目问答、新手入门指南等端点。
"""

from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from ._common import (
    send_json, scan_projects, build_repo_from_md, logger,
    TTSError,
)

__all__ = [
    "start_pipeline",
    "start_comparison",
    "handle_ask",
    "handle_onboarding",
]


def start_pipeline(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """启动后台流水线任务。"""
    if getattr(handler.server, "pipeline_running", False):
        send_json(handler, 409, {"error": "已有任务在运行中，请等待完成"})
        return

    def run_task() -> None:
        handler.server.pipeline_running = True
        handler.server.last_error = None
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
            use_llm = params.get("use_llm", True)
            style = params.get("style", "dialogue")
            token = params.get("token") or None
            repo_url = params.get("repo_url") or None

            output_dirname = params.get("output", f"output_{int(time.time())}")
            output_path = output_dir / output_dirname
            output_path.mkdir(parents=True, exist_ok=True)

            from gh_trending_audio.config import GITHUB_TOKEN as DEFAULT_TOKEN
            fetcher = GitHubFetcher(token=token or DEFAULT_TOKEN)
            if repo_url:
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

                if not repo_url:
                    already = False
                    for d in output_dir.iterdir():
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

                audio_path = output_path / f"{safe_name}.mp3"
                try:
                    tts = TTSEngine(language=lang, style=style)
                    tts.text_to_speech(doc.audio_script, str(audio_path))
                    audio_count += 1
                except (TTSError, OSError):
                    logger.warning("音频合成失败", exc_info=True)
                    pass

            handler.server.last_result = {
                "output_dir": output_dirname,
                "doc_count": doc_count,
                "audio_count": audio_count,
                "skipped": skipped,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error("流水线执行失败: %s", e, exc_info=True)
            handler.server.last_error = str(e)
        finally:
            handler.server.pipeline_running = False

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()

    send_json(handler, 202, {
        "status": "started",
        "message": "任务已启动，请轮询 /api/status 查看进度",
    })


def start_comparison(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """启动多仓库对比任务。"""
    if getattr(handler.server, "pipeline_running", False):
        send_json(handler, 409, {"error": "已有任务在运行中，请等待完成"})
        return

    projects = params.get("projects") or []
    if not isinstance(projects, list) or len(projects) < 2:
        send_json(handler, 400, {"error": "对比至少需要选择 2 个项目"})
        return
    if len(projects) > 3:
        projects = projects[:3]

    for p in projects:
        pdir = output_dir / p.get("dir", "")
        pname = p.get("name", "")
        if not (pdir / f"{pname}.md").exists():
            send_json(handler, 404, {"error": f"项目文档不存在: {pname}"})
            return

    style = params.get("style", "dialogue")
    lang = params.get("lang", "zh")

    def run_task() -> None:
        handler.server.pipeline_running = True
        handler.server.last_error = None
        try:
            from gh_trending_audio.llm_enhancer import LLMEnhancer
            from gh_trending_audio.tts_engine import TTSEngine

            enhancer = LLMEnhancer(language=lang, style=style)

            repos: list = []
            analyses: list[str] = []
            for p in projects:
                pdir = output_dir / p["dir"]
                pname = p["name"]
                md_path = pdir / f"{pname}.md"
                md_text = md_path.read_text(encoding="utf-8", errors="replace")
                repo = build_repo_from_md(pname, md_text)
                repos.append(repo)
                analyses.append(md_text[:4000])

            markdown, audio_script = enhancer.generate_comparison(repos, analyses)

            comp_dir = output_dir / "output_comparison"
            comp_dir.mkdir(parents=True, exist_ok=True)
            base_name = "compare_" + "_vs_".join(r.name for r in repos)
            md_path = comp_dir / f"{base_name}.md"
            script_path = comp_dir / f"{base_name}_script.txt"
            md_path.write_text(markdown, encoding="utf-8")
            script_path.write_text(audio_script, encoding="utf-8")

            audio_ok = False
            audio_path = comp_dir / f"{base_name}.mp3"
            try:
                tts = TTSEngine(language=lang, style=style)
                tts.text_to_speech(audio_script, str(audio_path))
                audio_ok = True
            except (TTSError, OSError):
                logger.warning("音频合成失败", exc_info=True)
                pass

            handler.server.last_result = {
                "type": "comparison",
                "output_dir": "output_comparison",
                "name": base_name,
                "project_url": f"/project/output_comparison/{base_name}",
                "doc_count": 1,
                "audio_count": 1 if audio_ok else 0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logger.error("流水线执行失败: %s", e, exc_info=True)
            handler.server.last_error = str(e)
        finally:
            handler.server.pipeline_running = False

    thread = threading.Thread(target=run_task, daemon=True)
    thread.start()

    send_json(handler, 202, {
        "status": "started",
        "message": "对比任务已启动，请轮询 /api/status 查看进度",
    })


def handle_ask(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """处理项目问答：基于项目文档调用 LLM 回答用户问题。"""
    question = (params.get("question") or "").strip()
    dir_name = params.get("dir") or ""
    proj_name = params.get("project") or ""

    if not question:
        send_json(handler, 400, {"error": "问题不能为空"})
        return
    if not proj_name:
        send_json(handler, 400, {"error": "项目名不能为空"})
        return

    proj_dir = output_dir / dir_name if dir_name else None
    if proj_dir is None or not proj_dir.exists():
        for p in scan_projects(output_dir):
            if p["name"] == proj_name:
                proj_dir = output_dir / p["dir"]
                dir_name = p["dir"]
                break
    if proj_dir is None or not proj_dir.exists():
        send_json(handler, 404, {"error": "项目目录不存在"})
        return

    md_path = proj_dir / f"{proj_name}.md"
    script_path = proj_dir / f"{proj_name}_script.txt"
    if not md_path.exists():
        send_json(handler, 404, {"error": "项目文档不存在"})
        return

    context_parts = []
    try:
        md_text = md_path.read_text(encoding="utf-8", errors="replace")
        context_parts.append("【项目文档】\n" + md_text[:6000])
    except (OSError, UnicodeDecodeError) as e:
        send_json(handler, 500, {"error": f"读取文档失败: {e}"})
        return

    if script_path.exists():
        try:
            script_text = script_path.read_text(encoding="utf-8", errors="replace")
            context_parts.append("【对话脚本】\n" + script_text[:3000])
        except (OSError, UnicodeDecodeError):
            logger.debug("脚本读取失败", exc_info=True)
            pass

    context = "\n\n".join(context_parts)

    try:
        # 阶段4: 通过注册表获取 LLM 后端
        from gh_trending_audio.registry import get_auto_llm_backend

        backend = get_auto_llm_backend()
        if backend is None:
            send_json(handler, 500, {"error": "LLM API Key 未配置，请在 .env 文件中设置 LLM_API_KEY"})
            return

        client = backend.get_client()
        system_prompt = "你是项目技术助手，基于以下项目文档回答用户问题。用中文回答，简洁专业。"
        user_prompt = f"项目上下文：\n{context}\n\n用户问题：{question}"

        response = client.chat.completions.create(
            model=backend.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        answer = response.choices[0].message.content.strip()
        send_json(handler, 200, {"answer": answer})
    except ImportError:
        send_json(handler, 500, {"error": "openai 库未安装，请运行 pip install openai"})
    except Exception as e:
        err_msg = str(e)[:300]
        send_json(handler, 500, {"error": f"调用 LLM 失败: {err_msg}"})


def handle_onboarding(handler: BaseHTTPRequestHandler, output_dir: Path, params: dict) -> None:
    """生成受众定制的新手入门指南。"""
    dir_name = params.get("dir") or ""
    proj_name = params.get("project") or ""
    audience = (params.get("audience") or "beginner").strip()

    if not proj_name:
        send_json(handler, 400, {"error": "项目名不能为空"})
        return

    valid_audiences = {"beginner", "developer", "architect"}
    if audience not in valid_audiences:
        send_json(handler, 400, {"error": "audience 必须是 beginner / developer / architect 之一"})
        return

    proj_dir = output_dir / dir_name if dir_name else None
    if proj_dir is None or not proj_dir.exists():
        for p in scan_projects(output_dir):
            if p["name"] == proj_name:
                proj_dir = output_dir / p["dir"]
                dir_name = p["dir"]
                break
    if proj_dir is None or not proj_dir.exists():
        send_json(handler, 404, {"error": "项目目录不存在"})
        return

    md_path = proj_dir / f"{proj_name}.md"
    if not md_path.exists():
        send_json(handler, 404, {"error": "项目文档不存在，无法生成入门指南"})
        return

    try:
        md_text = md_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as e:
        send_json(handler, 500, {"error": f"读取文档失败: {e}"})
        return

    repo_info = build_repo_from_md(proj_name, md_text)

    try:
        from gh_trending_audio.llm_enhancer import LLMEnhancer

        enhancer = LLMEnhancer()
        guide = enhancer.generate_onboarding(repo_info, md_text, audience)
        send_json(handler, 200, {"guide": guide})
    except ValueError as e:
        send_json(handler, 500, {"error": f"LLM 配置错误：{e}"})
    except ImportError as e:
        send_json(handler, 500, {"error": f"缺少依赖（请安装 openai 库：pip install openai）：{e}"})
    except Exception as e:
        logger.warning("入门指南生成失败", exc_info=True)
        send_json(handler, 502, {"error": f"生成入门指南失败: {e}"})

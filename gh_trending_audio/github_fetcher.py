"""
github_fetcher.py —— 从 GitHub 获取最新高价值项目

数据源：GitHub 官方 Search API
  - 无 Token：每小时 10 次搜索请求（足够日常使用）
  - 有 Token：每小时 30 次搜索请求 + 5000 次普通请求
  - 搜索条件：最近 N 天内创建，按 star 数降序

不重复造轮子：直接使用 GitHub 官方 REST API，无需第三方爬虫。
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from rich.console import Console

console = Console()

GITHUB_API = "https://api.github.com"


@dataclass
class RepoInfo:
    """一个 GitHub 仓库的结构化信息"""

    full_name: str          # owner/repo
    name: str
    owner: str
    description: str
    url: str                # html_url
    homepage: str           # 项目主页
    language: str
    stars: int
    forks: int
    open_issues: int
    watchers: int
    topics: list[str] = field(default_factory=list)
    created_at: str = ""
    pushed_at: str = ""
    license_name: str = ""
    readme_text: str = ""   # 抓取后填充
    # ── 增强数据（enrich_with_details 填充）──
    file_tree: str = ""         # 仓库目录结构摘要
    key_files: str = ""         # 关键文件内容（setup.py/pyproject.toml 等）
    recent_releases: str = ""   # 最近发布的版本信息
    recent_issues: str = ""      # 最近热门 issues
    languages_breakdown: str = "" # 代码语言占比
    contributors_count: int = 0  # 贡献者数量
    commits_count: int = 0       # 最近提交数

    @property
    def short_name(self) -> str:
        return self.name

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "topics": self.topics,
            "license": self.license_name,
            "readme_preview": self.readme_text[:500] if self.readme_text else "",
        }


class GitHubFetcher:
    """封装 GitHub Search API + README 获取"""

    def __init__(self, token: Optional[str] = None):
        """
        Args:
            token: GitHub Personal Access Token（可选）。
                   无 token 也能用，只是速率限制更严。
                   也可从环境变量 GITHUB_TOKEN 读取。
        """
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.session = requests.Session()
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    # GitHub Search API 限制：每页最多 100 条，总共最多 1000 条
    MAX_PER_PAGE = 100
    MAX_TOTAL_RESULTS = 1000

    def fetch_trending(
        self,
        days: int = 7,
        limit: int = 5,
        language: Optional[str] = None,
        min_stars: int = 50,
        topic: Optional[str] = None,
    ) -> list[RepoInfo]:
        """
        获取最近 N 天内 star 数最高的项目（支持分页，突破单页 30 条限制）。

        Args:
            days:        查看最近多少天内创建的项目（默认 7 天）
            limit:       返回前多少个项目（默认 5，最大 1000）
            language:    按编程语言过滤，例如 "Python"（可选）
            min_stars:   最低 star 数阈值（默认 50，过滤噪音）
            topic:       按 topic 过滤，例如 "ai" / "llm"（可选）

        Returns:
            RepoInfo 列表，按 star 降序

        分页策略：
            - 每页最多 100 条（GitHub API 上限）
            - 自动翻页直到达到 limit 或无更多结果
            - GitHub Search API 总结果上限 1000 条
        """
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        # 构建 GitHub Search 查询字符串
        query_parts = [f"created:>{since_date}", f"stars:>={min_stars}"]
        if language:
            query_parts.append(f"language:{language}")
        if topic:
            query_parts.append(f"topic:{topic}")
        query = " ".join(query_parts)

        # limit 上限保护
        limit = min(limit, self.MAX_TOTAL_RESULTS)
        console.print(f"[dim]搜索条件: {query} | 目标获取: {limit} 个[/dim]")

        results: list[RepoInfo] = []
        page = 1
        total_count = 0
        per_page = min(self.MAX_PER_PAGE, limit)

        while len(results) < limit:
            remaining = limit - len(results)
            current_per_page = min(per_page, remaining)

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": current_per_page,
                "page": page,
            }

            resp = self.session.get(
                f"{GITHUB_API}/search/repositories", params=params, timeout=30
            )
            self._check_rate_limit(resp)
            resp.raise_for_status()

            data = resp.json()
            total_count = data.get("total_count", 0)
            items = data.get("items", [])

            if not items:
                break

            for item in items:
                if len(results) >= limit:
                    break
                results.append(self._parse_repo(item))

            page += 1
            # GitHub Search API 最多翻 10 页（1000 条）
            if page > 10:
                break

        console.print(
            f"[green]✓ 找到 {total_count} 个项目，已获取 {len(results)} 个"
            + (f"（分 {page - 1} 页）" if page > 2 else "")
            + "[/green]"
        )
        return results

    def fetch_trending_iter(
        self,
        days: int = 7,
        limit: int = 5,
        language: Optional[str] = None,
        min_stars: int = 50,
        topic: Optional[str] = None,
    ):
        """
        生成器模式：逐个返回项目，适合串行流水线。

        优势：
            - 不需要等所有项目都获取完才开始处理
            - 内存占用低（不缓存全部结果）
            - 可以边获取边生成文档和音频

        Yields:
            RepoInfo 对象（逐个返回）
        """
        since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

        query_parts = [f"created:>{since_date}", f"stars:>={min_stars}"]
        if language:
            query_parts.append(f"language:{language}")
        if topic:
            query_parts.append(f"topic:{topic}")
        query = " ".join(query_parts)

        limit = min(limit, self.MAX_TOTAL_RESULTS)
        console.print(f"[dim]搜索条件: {query} | 串行模式，目标: {limit} 个[/dim]")

        yielded = 0
        page = 1
        total_count = 0
        per_page = min(self.MAX_PER_PAGE, limit)

        while yielded < limit:
            remaining = limit - yielded
            current_per_page = min(per_page, remaining)

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": current_per_page,
                "page": page,
            }

            resp = self.session.get(
                f"{GITHUB_API}/search/repositories", params=params, timeout=30
            )
            self._check_rate_limit(resp)
            resp.raise_for_status()

            data = resp.json()
            total_count = data.get("total_count", 0)
            items = data.get("items", [])

            if not items:
                break

            for item in items:
                if yielded >= limit:
                    break
                repo = self._parse_repo(item)
                console.print(
                    f"[green]✓[/green] [{yielded + 1}/{limit}] {repo.full_name} "
                    f"(⭐{repo.stars:,})"
                )
                yielded += 1
                yield repo

            page += 1
            if page > 10:
                break

        console.print(f"[dim]共找到 {total_count} 个项目，已获取 {yielded} 个[/dim]")

    def fetch_single_repo(self, repo_url: str) -> RepoInfo:
        """
        从 GitHub URL 获取单个仓库信息。

        借鉴 Podcastfy 的多源输入能力，支持用户粘贴任意 GitHub 仓库 URL
        直接处理单个项目，而不必依赖趋势搜索。

        支持的 URL 格式：
            - https://github.com/owner/repo
            - https://github.com/owner/repo.git
            - https://github.com/owner/repo/tree/main
            - git@github.com:owner/repo.git
            - owner/repo

        Args:
            repo_url: GitHub 仓库 URL

        Returns:
            RepoInfo 对象

        Raises:
            ValueError: URL 无法解析出 owner/repo，或仓库不存在/无权访问
        """
        owner, repo = self._parse_repo_url(repo_url)
        if not owner or not repo:
            raise ValueError(f"无法从 URL 解析出 owner/repo: {repo_url}")

        console.print(f"[dim]获取仓库: {owner}/{repo}[/dim]")
        resp = self.session.get(f"{GITHUB_API}/repos/{owner}/{repo}", timeout=30)
        self._check_rate_limit(resp)
        if resp.status_code == 404:
            raise ValueError(f"仓库不存在或无权访问: {owner}/{repo}")
        resp.raise_for_status()

        repo_info = self._parse_repo(resp.json())
        console.print(
            f"[green]✓[/green] {repo_info.full_name} (⭐{repo_info.stars:,})"
        )
        return repo_info

    def enrich_with_readme(self, repo: RepoInfo, max_chars: int = 4000) -> str:
        """
        获取仓库的 README 内容并提取纯文本。

        Args:
            repo:      RepoInfo 对象
            max_chars: 最多保留多少字符（避免太长）

        Returns:
            README 纯文本
        """
        # 优先取 README
        try:
            resp = self.session.get(
                f"{GITHUB_API}/repos/{repo.full_name}/readme", timeout=20
            )
            self._check_rate_limit(resp)
            if resp.status_code == 200:
                data = resp.json()
                content_b64 = data.get("content", "")
                encoding = data.get("encoding", "base64")
                if encoding == "base64":
                    raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                else:
                    raw = content_b64
                repo.readme_text = self._markdown_to_text(raw)[:max_chars]
                return repo.readme_text
        except Exception as e:
            console.print(f"[yellow]⚠ 获取 README 失败 ({repo.full_name}): {e}[/yellow]")

        # 退化方案：用 description
        repo.readme_text = repo.description or "（无 README）"
        return repo.readme_text

    def enrich_with_details(self, repo: RepoInfo):
        """
        获取仓库的深度信息，为 LLM 提供更丰富的上下文。

        使用 Repomix 开源工具（MIT License）将整个仓库打包为 AI 友好的压缩文本：
          - 完整目录结构
          - 核心源码文件的函数签名、类定义、import 关系（Tree-sitter 压缩）
          - 配置文件内容

        同时补充 GitHub API 获取的社区信息：
          - 最近 release
          - 热门 issues
          - 语言占比
          - 贡献者数量
        """
        parts = []

        # 1. Repomix: 完整代码架构（压缩模式）
        codebase = self._fetch_codebase_via_repomix(repo)
        if codebase:
            repo.file_tree = codebase  # 复用 file_tree 字段存储完整代码分析
            parts.append(f"【代码架构分析（Repomix 压缩）】\n{codebase}")

        # 2. 最近 releases
        releases = self._fetch_releases(repo)
        if releases:
            repo.recent_releases = releases
            parts.append(f"【最近发布】\n{releases}")

        # 3. 热门 issues
        issues = self._fetch_hot_issues(repo)
        if issues:
            repo.recent_issues = issues
            parts.append(f"【热门问题反馈】\n{issues}")

        # 4. 语言占比
        langs = self._fetch_languages(repo)
        if langs:
            repo.languages_breakdown = langs
            parts.append(f"【代码语言占比】\n{langs}")

        # 5. 贡献者数量
        contributors = self._fetch_contributors_count(repo)
        if contributors:
            repo.contributors_count = contributors
            parts.append(f"贡献者数量: {contributors}")

        if parts:
            console.print(f"  [dim]已获取深度信息（{len(parts)} 项）[/dim]")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Repomix 代码架构分析
    # ------------------------------------------------------------------

    def _fetch_codebase_via_repomix(self, repo: RepoInfo) -> str:
        """
        使用 Repomix 将远程仓库打包为 AI 友好的压缩文本。

        --compress 模式使用 Tree-sitter 只保留 imports、classes、函数签名，
        去掉实现细节，适合让 LLM 理解项目架构。

        输出限制在 12000 字符以内，避免 token 超限。
        """
        import subprocess
        import shutil as _shutil

        if not _shutil.which("repomix"):
            console.print("  [yellow]⚠ repomix 未安装，跳过代码架构分析[/yellow]")
            return ""

        try:
            cmd = [
                "repomix",
                "--remote", f"https://github.com/{repo.full_name}",
                "--compress",
                "--style", "xml",
                "--stdout",
                "--include",
                "README.md,*.py,**/__init__.py,**/config.py,**/modeling.py,"
                "**/evaluator.py,**/parser.py,**/trainer.py,**/dataset.py,"
                "**/loss.py,**/common.py,setup.py,pyproject.toml,"
                "requirements.txt,package.json,Cargo.toml,go.mod",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                console.print(f"  [yellow]⚠ repomix 失败: {result.stderr[:100]}[/yellow]")
                return ""

            output = result.stdout

            # 提取目录结构部分（最有价值）
            tree_start = output.find("<directory_structure>")
            tree_end = output.find("</directory_structure>")
            tree_section = ""
            if tree_start != -1 and tree_end != -1:
                tree_section = output[tree_start:tree_end + len("</directory_structure>")]

            # 提取文件内容部分，限制总量
            files_start = output.find("<files>")
            files_section = ""
            if files_start != -1:
                # 截取前 10000 字符的文件内容
                files_section = output[files_start:files_start + 10000]

            # 组合输出
            combined = tree_section + "\n\n" + files_section if tree_section else files_section[:10000]

            if not combined.strip():
                return ""

            console.print(f"  [dim]repomix 生成 {len(combined)} 字符的代码架构[/dim]")
            return combined[:12000]  # 硬限制 12000 字符

        except subprocess.TimeoutExpired:
            console.print("  [yellow]⚠ repomix 超时（120s），跳过[/yellow]")
            return ""
        except Exception as e:
            console.print(f"  [yellow]⚠ repomix 异常: {e}[/yellow]")
            return ""

    # ------------------------------------------------------------------
    # 深度信息获取的内部方法
    # ------------------------------------------------------------------

    def _fetch_file_tree(self, repo: RepoInfo) -> str:
        """获取仓库目录结构（前 2 层）"""
        try:
            resp = self.session.get(
                f"{GITHUB_API}/repos/{repo.full_name}/git/trees/main?recursive=1",
                timeout=15,
            )
            if resp.status_code != 200:
                resp = self.session.get(
                    f"{GITHUB_API}/repos/{repo.full_name}/git/trees/master?recursive=1",
                    timeout=15,
                )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            tree = data.get("tree", [])
            # 只取前 2 层路径，去重
            seen = set()
            lines = []
            for item in tree[:200]:
                path = item.get("path", "")
                parts = path.split("/")
                if len(parts) <= 2:
                    short = "/".join(parts[:2])
                    if short not in seen:
                        seen.add(short)
                        t = item.get("type", "blob")
                        prefix = "📁 " if t == "tree" else "📄 "
                        lines.append(f"{prefix}{short}")
            return "\n".join(lines[:50])
        except Exception:
            return ""

    def _fetch_key_files(self, repo: RepoInfo) -> str:
        """获取关键配置文件内容"""
        candidates = [
            "pyproject.toml", "setup.py", "setup.cfg",
            "package.json", "Cargo.toml", "go.mod",
            "requirements.txt", "Dockerfile",
        ]
        results = []
        for fname in candidates:
            try:
                resp = self.session.get(
                    f"{GITHUB_API}/repos/{repo.full_name}/contents/{fname}",
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content_b64 = data.get("content", "")
                    if content_b64:
                        raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                        # 只取前 30 行
                        lines = raw.split("\n")[:30]
                        results.append(f"--- {fname} ---\n" + "\n".join(lines))
                        break  # 找到第一个就够
            except Exception:
                continue
        return "\n\n".join(results)

    def _fetch_releases(self, repo: RepoInfo) -> str:
        """获取最近 3 个 release"""
        try:
            resp = self.session.get(
                f"{GITHUB_API}/repos/{repo.full_name}/releases?per_page=3",
                timeout=10,
            )
            if resp.status_code != 200:
                return ""
            releases = resp.json()
            lines = []
            for r in releases[:3]:
                tag = r.get("tag_name", "")
                name = r.get("name", "")
                date = (r.get("published_at") or "")[:10]
                body = (r.get("body") or "")[:300]
                lines.append(f"版本 {tag} ({date}): {name}\n{body}")
            return "\n\n".join(lines)
        except Exception:
            return ""

    def _fetch_hot_issues(self, repo: RepoInfo) -> str:
        """获取最近 5 个热门 issues"""
        try:
            resp = self.session.get(
                f"{GITHUB_API}/search/issues?q=repo:{repo.full_name}+is:issue+sort:reactions&per_page=5",
                timeout=10,
            )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            issues = data.get("items", [])
            lines = []
            for iss in issues[:5]:
                title = iss.get("title", "")
                reactions = iss.get("reactions", {}).get("total", 0)
                state = "已关闭" if iss.get("state") == "closed" else "开放中"
                lines.append(f"[{state}] {title} (👍{reactions})")
            return "\n".join(lines)
        except Exception:
            return ""

    def _fetch_languages(self, repo: RepoInfo) -> str:
        """获取代码语言占比"""
        try:
            resp = self.session.get(
                f"{GITHUB_API}/repos/{repo.full_name}/languages", timeout=10
            )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            if not data:
                return ""
            total = sum(data.values())
            lines = []
            for lang, bytes_count in sorted(data.items(), key=lambda x: -x[1])[:5]:
                pct = round(bytes_count / total * 100, 1)
                lines.append(f"{lang}: {pct}%")
            return "\n".join(lines)
        except Exception:
            return ""

    def _fetch_contributors_count(self, repo: RepoInfo) -> int:
        """获取贡献者数量"""
        try:
            resp = self.session.get(
                f"{GITHUB_API}/repos/{repo.full_name}/contributors?per_page=1&anon=true",
                timeout=10,
            )
            if resp.status_code != 200:
                return 0
            # GitHub 通过 Link header 返回分页信息
            link = resp.headers.get("Link", "")
            if "last" in link:
                # 提取最后一页的页码
                import re
                match = re.search(r"page=(\d+)>; rel=\"last\"", link)
                if match:
                    return int(match.group(1))
            # 没有分页说明只有 1 页
            return len(resp.json())
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _parse_repo(self, item: dict) -> RepoInfo:
        """从 GitHub API 返回的 JSON 解析出 RepoInfo"""
        license_info = item.get("license") or {}
        return RepoInfo(
            full_name=item["full_name"],
            name=item["name"],
            owner=item["owner"]["login"],
            description=item.get("description") or "",
            url=item["html_url"],
            homepage=item.get("homepage") or "",
            language=item.get("language") or "Unknown",
            stars=item["stargazers_count"],
            forks=item["forks_count"],
            open_issues=item.get("open_issues_count", 0),
            watchers=item.get("watchers_count", 0),
            topics=item.get("topics", []),
            created_at=item.get("created_at", ""),
            pushed_at=item.get("pushed_at", ""),
            license_name=license_info.get("name", "Unknown"),
        )

    @staticmethod
    def _parse_repo_url(repo_url: str) -> tuple[str, str]:
        """
        从 GitHub URL 中提取 owner 和 repo。

        支持的格式：
            - https://github.com/owner/repo
            - https://github.com/owner/repo.git
            - https://github.com/owner/repo/tree/main
            - http://github.com/owner/repo
            - git@github.com:owner/repo.git
            - github.com/owner/repo
            - owner/repo
        """
        repo_url = (repo_url or "").strip()
        if not repo_url:
            return "", ""

        # 1) 含 github.com 的 URL（HTTP/HTTPS/SSH 均可）
        m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?(?:/|$)", repo_url)
        if m:
            return m.group(1), m.group(2)

        # 2) owner/repo 简写（无 scheme、无 host）
        m = re.match(r"^([^/\s]+)/([^/\s]+?)(?:\.git)?$", repo_url)
        if m:
            return m.group(1), m.group(2)

        return "", ""

    @staticmethod
    def _markdown_to_text(md: str) -> str:
        """简单将 Markdown 转为可读纯文本（去除标记符号）"""
        try:
            import markdown as md_lib
            from bs4 import BeautifulSoup

            html = md_lib.markdown(md, extensions=["fenced_code", "tables"])
            soup = BeautifulSoup(html, "html.parser")
            # 移除代码块
            for tag in soup.find_all(["code", "pre"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # 折叠多余空行
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)
        except Exception:
            # 如果依赖未安装，做最简单的清理
            import re
            text = re.sub(r"```[\s\S]*?```", "", md)      # 代码块
            text = re.sub(r"`([^`]+)`", r"\1", text)       # 行内代码
            text = re.sub(r"^#+\s*", "", text, flags=re.M)  # 标题
            text = re.sub(r"!\[.*?\]\(.*?\)", "", text)     # 图片
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # 链接
            text = re.sub(r"[*_>|]", "", text)              # 格式符号
            return text.strip()

    @staticmethod
    def _check_rate_limit(resp: requests.Response):
        """检查 GitHub API 速率限制，给出友好提示"""
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) <= 1:
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
            if reset_ts:
                reset_time = datetime.fromtimestamp(reset_ts, tz=timezone.utc)
                console.print(
                    f"[yellow]⚠ GitHub API 配额即将用尽，重置时间: "
                    f"{reset_time.strftime('%H:%M:%S UTC')}[/yellow]"
                )
            console.print("[dim]提示：设置 GITHUB_TOKEN 环境变量可提高配额[/dim]")

    # ------------------------------------------------------------------
    # 辅助：获取当前用户/仓库等
    # ------------------------------------------------------------------

    def get_repo_detail(self, owner: str, repo: str) -> Optional[RepoInfo]:
        """获取单个仓库的详细信息（按需使用）"""
        try:
            resp = self.session.get(f"{GITHUB_API}/repos/{owner}/{repo}", timeout=20)
            resp.raise_for_status()
            return self._parse_repo(resp.json())
        except Exception as e:
            console.print(f"[red]✗ 获取仓库信息失败: {e}[/red]")
            return None

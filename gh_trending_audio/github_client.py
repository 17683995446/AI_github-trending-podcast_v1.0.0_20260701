"""github_client.py —— PyGithub 封装层

用 PyGithub 替换手写 REST URL 拼接 + base64 解码 + 分页管理。
当 PyGithub 不可用时，退化到 requests 直调模式。

设计原则（第一性原理）：
- 统一入口：所有 GitHub 数据获取都通过此模块
- 类型安全：返回 dataclass 或 TypedDict，而非裸 dict
- 自动重试：PyGithub 内置速率限制处理
- 缓存无关：本模块只负责数据获取，缓存由调用方管理
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """文件树节点。"""
    path: str
    type: str  # "blob" | "tree"
    size: int = 0


@dataclass
class RepoSummary:
    """仓库基本信息。"""
    full_name: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    license_name: str = ""
    topics: list[str] = field(default_factory=list)
    default_branch: str = "main"
    html_url: str = ""


@dataclass
class CommunityData:
    """社区洞察数据。"""
    open_issues: list[dict] = field(default_factory=list)
    open_pulls: list[dict] = field(default_factory=list)
    contributors: list[dict] = field(default_factory=list)
    releases: list[dict] = field(default_factory=list)
    repo_info: dict = field(default_factory=dict)


class GitHubClient:
    """GitHub API 客户端，优先使用 PyGithub，退化到 requests。"""

    def __init__(self, token: str = ""):
        self._token = token
        self._pygithub_repo_cache: dict = {}
        try:
            from github import Github
            if token:
                try:
                    from github import Auth
                    self._gh = Github(auth=Auth.Token(token))
                except ImportError:
                    self._gh = Github(token)
            else:
                self._gh = Github()
            self._use_pygithub = True
            logger.debug("PyGithub 初始化成功")
        except ImportError:
            self._use_pygithub = False
            import requests
            self._session = requests.Session()
            if token:
                self._session.headers.update({"Authorization": f"token {token}"})
            self._session.headers.update({"Accept": "application/vnd.github+json"})
            logger.debug("PyGithub 不可用，退化到 requests 模式")

    @property
    def uses_pygithub(self) -> bool:
        return self._use_pygithub

    def _get_repo(self, repo_full: str):
        """获取 PyGithub Repository 对象（带缓存）。"""
        if repo_full not in self._pygithub_repo_cache:
            self._pygithub_repo_cache[repo_full] = self._gh.get_repo(repo_full)
        return self._pygithub_repo_cache[repo_full]

    # ── 仓库基本信息 ──────────────────────────────────────────

    def get_repo_info(self, repo_full: str) -> RepoSummary:
        """获取仓库基本信息。"""
        if self._use_pygithub:
            repo = self._get_repo(repo_full)
            license_name = ""
            if repo.license:
                license_name = repo.license.name or ""
            return RepoSummary(
                full_name=repo.full_name,
                description=repo.description or "",
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                language=repo.language or "",
                license_name=license_name,
                topics=list(repo.topics) if repo.topics else [],
                default_branch=repo.default_branch,
                html_url=repo.html_url,
            )
        else:
            resp = self._session.get(
                f"https://api.github.com/repos/{repo_full}", timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            lic = data.get("license") or {}
            return RepoSummary(
                full_name=data.get("full_name", repo_full),
                description=data.get("description", "") or "",
                stars=data.get("stargazers_count", 0),
                forks=data.get("forks_count", 0),
                language=data.get("language", "") or "",
                license_name=lic.get("name", "") if lic else "",
                topics=data.get("topics", []),
                default_branch=data.get("default_branch", "main"),
                html_url=data.get("html_url", ""),
            )

    # ── README 获取 ───────────────────────────────────────────

    def get_readme(self, repo_full: str) -> tuple[str, str, str]:
        """获取 README 内容。

        Returns:
            (readme_text, readme_path, html_url)
        """
        if self._use_pygithub:
            repo = self._get_repo(repo_full)
            readme = repo.get_readme()
            content = base64.b64decode(readme.content).decode("utf-8", errors="replace")
            return content, readme.path, readme.html_url
        else:
            resp = self._session.get(
                f"https://api.github.com/repos/{repo_full}/readme", timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            return content, data.get("path", "README.md"), data.get("html_url", "")

    # ── 文件树 ────────────────────────────────────────────────

    def get_file_tree(self, repo_full: str) -> tuple[list[FileInfo], bool]:
        """获取递归文件树。

        Returns:
            (file_list, truncated)
        """
        if self._use_pygithub:
            repo = self._get_repo(repo_full)
            tree = repo.get_git_tree(repo.default_branch, recursive=True)
            files = [
                FileInfo(path=el.path, type=el.type, size=el.size or 0)
                for el in tree.tree
            ]
            return files, tree.truncated if hasattr(tree, "truncated") else False
        else:
            # 先获取默认分支
            repo_info = self.get_repo_info(repo_full)
            resp = self._session.get(
                f"https://api.github.com/repos/{repo_full}/git/trees/{repo_info.default_branch}?recursive=1",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            files = [
                FileInfo(
                    path=el.get("path", ""),
                    type=el.get("type", "blob"),
                    size=el.get("size", 0),
                )
                for el in data.get("tree", [])
            ]
            return files, data.get("truncated", False)

    # ── 单文件内容 ────────────────────────────────────────────

    def get_file_content(self, repo_full: str, file_path: str, max_size: int = 102400) -> str:
        """获取单个文件内容（限制大小）。"""
        if self._use_pygithub:
            repo = self._get_repo(repo_full)
            content_file = repo.get_contents(file_path)
            if content_file.content:
                text = base64.b64decode(content_file.content).decode("utf-8", errors="replace")
            elif content_file.encoding == "base64":
                text = base64.b64decode(content_file.content or "").decode("utf-8", errors="replace")
            else:
                text = content_file.content or ""
            if len(text) > max_size:
                text = text[:max_size] + f"\n\n... (文件已截断，完整内容请访问 GitHub)"
            return text
        else:
            resp = self._session.get(
                f"https://api.github.com/repos/{repo_full}/contents/{file_path}",
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
            if len(content) > max_size:
                content = content[:max_size] + f"\n\n... (文件已截断，完整内容请访问 GitHub)"
            return content

    # ── 社区洞察 ──────────────────────────────────────────────

    def get_community_data(
        self, repo_full: str, max_items: int = 5
    ) -> CommunityData:
        """获取社区洞察数据（issues, PRs, contributors, releases）。"""
        if self._use_pygithub:
            repo = self._get_repo(repo_full)
            data = CommunityData()
            data.repo_info = {
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "watchers": repo.watchers_count,
                "language": repo.language or "",
            }
            # 热门 Issues
            try:
                issues = repo.get_issues(state="open", sort="comments", direction="desc")
                for i, issue in enumerate(issues):
                    if i >= max_items:
                        break
                    if issue.pull_request:  # 跳过 PR
                        continue
                    data.open_issues.append({
                        "title": issue.title,
                        "number": issue.number,
                        "html_url": issue.html_url,
                        "comments": issue.comments,
                        "created_at": issue.created_at.isoformat() if issue.created_at else "",
                    })
            except Exception as e:
                logger.warning(f"获取 Issues 失败: {e}")

            # 活跃 PRs
            try:
                pulls = repo.get_pulls(state="open", sort="created", direction="desc")
                for i, pr in enumerate(pulls):
                    if i >= max_items:
                        break
                    data.open_pulls.append({
                        "title": pr.title,
                        "number": pr.number,
                        "html_url": pr.html_url,
                        "user": pr.user.login if pr.user else "",
                        "created_at": pr.created_at.isoformat() if pr.created_at else "",
                    })
            except Exception as e:
                logger.warning(f"获取 PRs 失败: {e}")

            # 贡献者
            try:
                contributors = repo.get_contributors()
                for i, c in enumerate(contributors):
                    if i >= max_items:
                        break
                    data.contributors.append({
                        "login": c.login,
                        "contributions": c.contributions,
                        "html_url": c.html_url,
                        "avatar_url": c.avatar_url or "",
                    })
            except Exception as e:
                logger.warning(f"获取贡献者失败: {e}")

            # 最新版本
            try:
                releases = repo.get_releases()
                for i, r in enumerate(releases):
                    if i >= max_items:
                        break
                    data.releases.append({
                        "tag": r.tag_name,
                        "name": r.title or r.tag_name,
                        "html_url": r.html_url,
                        "published_at": r.published_at.isoformat() if r.published_at else "",
                        "draft": r.draft,
                        "prerelease": r.prerelease,
                    })
            except Exception as e:
                logger.warning(f"获取 Releases 失败: {e}")

            return data
        else:
            # requests 退化模式
            data = CommunityData()
            endpoints = {
                "issues": f"https://api.github.com/repos/{repo_full}/issues?state=open&sort=comments&direction=desc&per_page={max_items}",
                "pulls": f"https://api.github.com/repos/{repo_full}/pulls?state=open&sort=created&direction=desc&per_page={max_items}",
                "contributors": f"https://api.github.com/repos/{repo_full}/contributors?per_page={max_items}",
                "releases": f"https://api.github.com/repos/{repo_full}/releases?per_page={max_items}",
                "repo_info": f"https://api.github.com/repos/{repo_full}",
            }
            results = {}
            import threading
            threads = []
            for key, url in endpoints.items():
                def fetch(k=key, u=url):
                    try:
                        r = self._session.get(u, timeout=15)
                        if r.status_code == 200:
                            results[k] = r.json()
                        else:
                            results[k] = []
                    except Exception:
                        results[k] = []
                t = threading.Thread(target=fetch)
                threads.append(t)
                t.start()
            for t in threads:
                t.join(timeout=20)

            data.open_issues = [
                {"title": i.get("title", ""), "number": i.get("number", 0),
                 "html_url": i.get("html_url", ""), "comments": i.get("comments", 0),
                 "created_at": i.get("created_at", "")}
                for i in results.get("issues", [])
                if not i.get("pull_request")  # 过滤 PR
            ][:max_items]
            data.open_pulls = [
                {"title": p.get("title", ""), "number": p.get("number", 0),
                 "html_url": p.get("html_url", ""), "user": (p.get("user") or {}).get("login", ""),
                 "created_at": p.get("created_at", "")}
                for p in results.get("pulls", [])
            ][:max_items]
            data.contributors = [
                {"login": c.get("login", ""), "contributions": c.get("contributions", 0),
                 "html_url": c.get("html_url", ""), "avatar_url": c.get("avatar_url", "")}
                for c in results.get("contributors", [])
            ][:max_items]
            data.releases = [
                {"tag": r.get("tag_name", ""), "name": r.get("name", "") or r.get("tag_name", ""),
                 "html_url": r.get("html_url", ""), "published_at": r.get("published_at", ""),
                 "draft": r.get("draft", False), "prerelease": r.get("prerelease", False)}
                for r in results.get("releases", [])
            ][:max_items]
            ri = results.get("repo_info", {})
            data.repo_info = {
                "stars": ri.get("stargazers_count", 0),
                "forks": ri.get("forks_count", 0),
                "open_issues": ri.get("open_issues_count", 0),
                "watchers": ri.get("watchers_count", 0),
                "language": ri.get("language", "") or "",
            }
            return data


# ── 模块级单例 ──────────────────────────────────────────────

_client: Optional[GitHubClient] = None


def get_github_client() -> GitHubClient:
    """获取全局 GitHubClient 单例。"""
    global _client
    if _client is None:
        from gh_trending_audio.config import GITHUB_TOKEN
        _client = GitHubClient(token=GITHUB_TOKEN or "")
    return _client

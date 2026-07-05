"""自定义异常层次（阶段1: 秩序化）。

将散落的裸 ``except Exception`` 替换为具体异常类型，实现：
  - 错误可分类、可过滤、可差异化处理
  - 日志可按异常级别记录
  - 调用方可按异常类型做精确回退

层次结构::

    GhTrendingError                    # 所有自定义异常的基类
    ├── ConfigError                    # 配置缺失或无效
    ├── GitHubAPIError                 # GitHub API 调用失败
    │   ├── GitHubRateLimitError       #   速率限制 (403/429)
    │   └── GitHubNotFoundError        #   仓库不存在 (404)
    ├── TTSError                       # TTS 语音合成失败
    ├── LLMError                       # LLM 调用失败
    ├── DocumentGenerationError        # 文档生成失败
    ├── PipelineError                  # 流水线编排失败
    ├── FileOperationError             # 文件读写失败
    ├── NetworkError                   # 网络请求失败
    └── CodeSearchError                # 代码搜索不可用
"""

from __future__ import annotations


class GhTrendingError(Exception):
    """所有 GitHub Trending Audio 自定义异常的基类。"""


# ── 配置 ──────────────────────────────────────────────────────────────

class ConfigError(GhTrendingError):
    """配置缺失或无效（API Key、环境变量等）。"""


# ── GitHub ────────────────────────────────────────────────────────────

class GitHubAPIError(GhTrendingError):
    """GitHub API 调用失败的通用异常。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubRateLimitError(GitHubAPIError):
    """GitHub API 速率限制（403/429）。"""


class GitHubNotFoundError(GitHubAPIError):
    """GitHub 仓库不存在（404）。"""


# ── TTS ──────────────────────────────────────────────────────────────

class TTSError(GhTrendingError):
    """TTS 语音合成失败。"""


# ── LLM ──────────────────────────────────────────────────────────────

class LLMError(GhTrendingError):
    """LLM 调用失败（API 错误、结构化输出解析失败等）。"""


# ── 文档 ──────────────────────────────────────────────────────────────

class DocumentGenerationError(GhTrendingError):
    """文档生成失败（模板渲染、Jinja2 错误等）。"""


# ── 流水线 ────────────────────────────────────────────────────────────

class PipelineError(GhTrendingError):
    """流水线编排失败（步骤间依赖、状态不一致等）。"""


# ── 文件 ──────────────────────────────────────────────────────────────

class FileOperationError(GhTrendingError):
    """文件读写操作失败。"""


# ── 网络 ──────────────────────────────────────────────────────────────

class NetworkError(GhTrendingError):
    """网络请求失败（连接超时、DNS 解析等）。"""


# ── 代码搜索 ──────────────────────────────────────────────────────────

class CodeSearchError(GhTrendingError):
    """代码搜索不可用或执行失败。"""

"""全局常量定义（阶段2: 消除魔法数字）。

将散落在各模块中的硬编码常量集中管理，包括：
  - GitHub API URL 和超时
  - TTS 引擎超时
  - 内容截断长度
  - 缓存参数
  - 本地后端检测超时

所有常量使用 ``UPPER_SNAKE_CASE`` 命名，按领域分组。
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
# GitHub API
# ═══════════════════════════════════════════════════════════════════

#: GitHub REST API 基础 URL
GITHUB_API_URL: str = "https://api.github.com"

#: GitHub 搜索 API 超时（秒）— 列表搜索较慢
GITHUB_SEARCH_TIMEOUT: int = 30

#: GitHub 单仓库 API 超时（秒）— 仓库详情/README
GITHUB_REPO_TIMEOUT: int = 20

#: GitHub 轻量 API 超时（秒）— 语言/贡献者等附属信息
GITHUB_LIGHT_TIMEOUT: int = 10

#: GitHub 代码搜索超时（秒）
GITHUB_CODE_SEARCH_TIMEOUT: int = 20

#: GitHub 文件树获取超时（秒）
GITHUB_TREE_TIMEOUT: int = 30

#: GitHub 旧客户端（github_client.py）单仓库超时（秒）
GITHUB_CLIENT_REPO_TIMEOUT: int = 15

#: GitHub 社区洞察并发获取超时（秒）
GITHUB_INSIGHTS_TIMEOUT: int = 20

# ═══════════════════════════════════════════════════════════════════
# TTS 语音合成
# ═══════════════════════════════════════════════════════════════════

#: TTS 合成超时（秒）— 主引擎
TTS_SYNTHESIS_TIMEOUT: int = 120

#: TTS 合成超时（秒）— 辅助/回退引擎
TTS_FALLBACK_TIMEOUT: int = 60

#: Piper TTS 合成超时（秒）
PIPER_TTS_TIMEOUT: int = 120

#: Piper TTS 模型下载超时（秒）
PIPER_DOWNLOAD_TIMEOUT: int = 60

# ═══════════════════════════════════════════════════════════════════
# 本地后端检测
# ═══════════════════════════════════════════════════════════════════

#: Ollama 快速探测超时（秒）— 用于判断是否在线
LOCAL_BACKEND_QUICK_TIMEOUT: int = 2

#: Ollama 完整检测超时（秒）— 用于获取模型列表
LOCAL_BACKEND_FULL_TIMEOUT: int = 5

# ═══════════════════════════════════════════════════════════════════
# 内容截断长度
# ═══════════════════════════════════════════════════════════════════

#: README 内容截断长度（字节）— 防止超大 README 撑爆 LLM 上下文
README_MAX_BYTES: int = 200 * 1024  # 200 KB

#: Markdown 元数据解析截断长度（字符）
MD_META_PARSE_LIMIT: int = 2000

#: LLM 脚本生成最大长度（字符）
LLM_SCRIPT_MAX_LENGTH: int = 4000

#: 文档生成模板模式最大描述长度（字符）
DOC_TEMPLATE_DESC_LIMIT: int = 1500

#: GitHub 文件内容预览截断长度（字符）
FILE_PREVIEW_LIMIT: int = 600

#: GitHub README 预览截断长度（字符）
README_PREVIEW_LIMIT: int = 1000

#: LLM 增强器对话片段最大长度
LLM_DIALOGUE_MAX_LENGTH: int = 300

#: LLM 增强器上下文摘要最大长度
LLM_CONTEXT_MAX_LENGTH: int = 200

#: 搜索建议最大返回数
SEARCH_SUGGESTION_LIMIT: int = 120

#: 错误消息截断长度
ERROR_MESSAGE_TRUNCATE: int = 300

# ═══════════════════════════════════════════════════════════════════
# 代码智能 / 搜索
# ═══════════════════════════════════════════════════════════════════

#: ripgrep 执行超时（秒）
RIPGREP_TIMEOUT: int = 30

#: 代码搜索（本地）执行超时（秒）
CODE_SEARCH_TIMEOUT: int = 90

#: ffprobe 音频时长检测超时（秒）
FFPROBE_TIMEOUT: int = 5

#: wkhtmltopdf PDF 生成超时（秒）
PDF_EXPORT_TIMEOUT: int = 5

# ═══════════════════════════════════════════════════════════════════
# Web 缓存参数
# ═══════════════════════════════════════════════════════════════════

#: API 响应缓存最大条目数
API_CACHE_MAXSIZE: int = 50

#: API 响应缓存 TTL（秒）— 30 分钟
API_CACHE_TTL: int = 1800

#: 静态资源缓存最大条目数
STATIC_CACHE_MAXSIZE: int = 200

#: 静态资源缓存 TTL（秒）— 10 分钟
STATIC_CACHE_TTL: int = 600

#: 静态文件 Cache-Control max-age（秒）— 1 天
STATIC_CACHE_MAX_AGE: int = 86400

#: 社区洞察最大返回条目数
COMMUNITY_INSIGHTS_MAX_ITEMS: int = 10

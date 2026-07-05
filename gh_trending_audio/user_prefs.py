"""用户偏好与收藏系统（阶段15-16: 持久化用户设置 + 项目收藏）。

使用 localStorage 持久化用户偏好（主题、语速、音量等），
以及收藏的项目列表。提供服务端 API 用于偏好同步。

核心功能：
    - ``get_preferences_schema()`` → 偏好字段定义
    - ``merge_preferences()`` → 合并默认值和用户设置
    - ``DEFAULT_PREFERENCES`` → 默认偏好值

设计原则：
    - 第一性原理：用户偏好属于用户，应跨会话保留
    - 前端优先：localStorage 即时响应，API 可选同步
    - 零依赖：纯数据结构
"""

from __future__ import annotations

import json
from typing import Any

# 默认偏好值
DEFAULT_PREFERENCES: dict[str, Any] = {
    "theme": "dark",
    "playback_rate": 1.0,
    "volume": 1.0,
    "output_language": "zh",
    "podcast_style": "dialogue",
    "auto_play_next": False,
    "sort_order": "newest",
    "filter_language": "all",
    "favorites": [],  # 收藏的项目名列表
    "recent_projects": [],  # 最近访问的项目
    "last_visited": None,  # 最后访问时间
}

# 偏好字段定义（用于前端渲染设置表单）
PREFERENCES_SCHEMA: list[dict[str, Any]] = [
    {"key": "theme", "label": "主题", "type": "select",
     "options": [("dark", "暗色"), ("light", "亮色"), ("midnight", "午夜"), ("nord", "Nord")],
     "category": "外观"},
    {"key": "playback_rate", "label": "默认播放速度", "type": "range",
     "min": 0.5, "max": 2.0, "step": 0.25, "category": "播放器"},
    {"key": "volume", "label": "默认音量", "type": "range",
     "min": 0.0, "max": 1.0, "step": 0.1, "category": "播放器"},
    {"key": "output_language", "label": "输出语言", "type": "select",
     "options": [("zh", "中文"), ("en", "English")], "category": "生成"},
    {"key": "podcast_style", "label": "播客风格", "type": "select",
     "options": [("dialogue", "双人对话"), ("debate", "辩论"), ("interview", "采访"),
                 ("news", "新闻播报"), ("story", "故事")], "category": "生成"},
    {"key": "auto_play_next", "label": "自动播放下一个", "type": "boolean", "category": "播放器"},
    {"key": "sort_order", "label": "默认排序", "type": "select",
     "options": [("newest", "最新创建"), ("stars", "星标最多"), ("name", "名称"), ("duration", "时长最长")],
     "category": "项目列表"},
    {"key": "filter_language", "label": "默认语言筛选", "type": "select",
     "options": [("all", "全部语言"), ("python", "Python"), ("rust", "Rust"), ("go", "Go"),
                 ("javascript", "JavaScript"), ("typescript", "TypeScript")], "category": "项目列表"},
]


def get_preferences_schema() -> list[dict[str, Any]]:
    """返回偏好字段定义。"""
    return PREFERENCES_SCHEMA


def merge_preferences(user_prefs: dict[str, Any]) -> dict[str, Any]:
    """合并默认值和用户设置。

    Args:
        user_prefs: 用户提供的偏好（可能不完整）

    Returns:
        合并后的完整偏好字典
    """
    merged = DEFAULT_PREFERENCES.copy()
    for key, value in user_prefs.items():
        if key in merged:
            merged[key] = value
    return merged


def toggle_favorite(favorites: list[str], project_name: str) -> list[str]:
    """切换项目收藏状态。

    Args:
        favorites: 当前收藏列表
        project_name: 项目名

    Returns:
        更新后的收藏列表
    """
    if project_name in favorites:
        return [f for f in favorites if f != project_name]
    else:
        return favorites + [project_name]


def add_recent_project(recent: list[str], project_name: str, max_items: int = 10) -> list[str]:
    """添加最近访问的项目。

    Args:
        recent: 当前最近访问列表
        project_name: 项目名
        max_items: 最大保留数量

    Returns:
        更新后的最近访问列表
    """
    # 移除已存在项
    recent = [r for r in recent if r != project_name]
    # 添加到头部
    recent.insert(0, project_name)
    # 限制数量
    return recent[:max_items]

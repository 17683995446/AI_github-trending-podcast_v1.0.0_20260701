"""播客风格定义（Phase 5: 委托给 registry 模块）。

原手写字典 STYLES 已迁移至 ``registry.py`` 的注册机制。
本模块保留 ``STYLES`` 字典和 ``get_style`` 函数以兼容现有调用方，
但内部委托给 registry 模块。

新增风格只需在 registry.py 中用 ``@register_style("name")`` 注册。
"""

from __future__ import annotations

from .registry import PodcastStyle as _RegistryPodcastStyle
from .registry import SpeakerRole as _RegistrySpeakerRole
from .registry import get_all_styles, get_style as _registry_get_style


# 兼容旧接口：保持 SpeakerRole / PodcastStyle 可从本模块导入
SpeakerRole = _RegistrySpeakerRole
PodcastStyle = _RegistryPodcastStyle


# DEPRECATED: 此函数无调用方，计划在后续版本中移除。
def _convert_to_legacy(style: _RegistryPodcastStyle) -> _RegistryPodcastStyle:
    """兼容转换：registry 的 PodcastStyle 直接可用。"""
    return style


# ── STYLES 字典（兼容旧接口，委托给 registry）──
STYLES: dict[str, _RegistryPodcastStyle] = get_all_styles()


def get_style(style: str) -> _RegistryPodcastStyle:
    """按名称获取风格定义，未知风格回退到 dialogue。

    Args:
        style: 风格标识符（如 "dialogue"、"debate"）

    Returns:
        PodcastStyle 实例
    """
    result = _registry_get_style(style)
    if result is None:
        return _registry_get_style("dialogue")  # type: ignore[return-value]
    return result

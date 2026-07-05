"""项目对比引擎（阶段14: 并排特性对比表 + 差异高亮）。

对多个项目进行多维度对比，生成结构化的对比表格，
支持差异高亮和雷达图数据导出。

核心功能：
    - ``compare_projects()`` → 生成多项目对比数据
    - ``generate_comparison_table()`` → HTML 对比表格
    - ``generate_radar_data()`` → ECharts 雷达图数据

设计原则：
    - 第一性原理：对比 = 同维度数据并排 + 差异标记
    - 零依赖：纯 Python 数据处理
    - 结构化输出：HTML 表格 + JSON 数据 + 雷达图
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_config import get_logger
from .project_scanner import get_project_detail, scan_projects

logger = get_logger(__name__)


@dataclass
class ComparisonMetric:
    """对比维度。"""
    key: str
    label: str
    values: dict[str, Any]  # project_name -> value
    is_highlighted: bool = False  # 是否有差异


def _extract_metrics_from_md(md_content: str) -> dict[str, Any]:
    """从 Markdown 内容提取可对比的指标。"""
    metrics: dict[str, Any] = {}

    # 提取表格中的指标
    table_pattern = re.compile(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|")
    for match in table_pattern.finditer(md_content):
        key = match.group(1).strip()
        val = match.group(2).strip()
        if key and val and key not in ("---", "描述", "项目", "特性"):
            metrics[key] = val

    # 提取标题
    title_match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    if title_match:
        metrics["项目名称"] = title_match.group(1).strip()

    # 提取星标数
    stars_match = re.search(r"(\d[\d,]*)\s*星", md_content)
    if stars_match:
        metrics["星标数"] = int(stars_match.group(1).replace(",", ""))

    # 提取编程语言
    lang_match = re.search(r"编程语言\s*[|：:]\s*(\w+)", md_content, re.IGNORECASE)
    if lang_match:
        metrics["编程语言"] = lang_match.group(1)

    # 提取协议
    license_match = re.search(r"协议\s*[|：:]\s*(\S+)", md_content, re.IGNORECASE)
    if license_match:
        metrics["开源协议"] = license_match.group(1)

    # 提取代码行数（如有）
    lines_match = re.search(r"(\d[\d,]*)\s*行", md_content)
    if lines_match:
        metrics["代码行数"] = int(lines_match.group(1).replace(",", ""))

    return metrics


def compare_projects(
    output_dir: Path,
    project_names: list[str],
    dir_name: str = "",
) -> dict[str, Any]:
    """对比多个项目。

    Args:
        output_dir: 输出根目录
        project_names: 要对比的项目名列表（至少2个）
        dir_name: 项目所在目录（空则自动搜索）

    Returns:
        对比数据字典，含指标、项目信息、差异标记
    """
    if len(project_names) < 2:
        return {"error": "至少需要2个项目进行对比"}

    projects_data: list[dict[str, Any]] = []

    for name in project_names:
        if dir_name:
            detail = get_project_detail(output_dir, dir_name, name)
        else:
            # 自动搜索目录
            detail = None
            for p in scan_projects(output_dir):
                if p.get("name") == name:
                    detail = get_project_detail(output_dir, p["dir"], name)
                    break

        if not detail:
            projects_data.append({"name": name, "error": "项目未找到"})
            continue

        md_content = detail.get("md_content", "")
        extracted = _extract_metrics_from_md(md_content)

        projects_data.append({
            "name": name,
            "stars": detail.get("stars", 0),
            "forks": detail.get("forks", 0),
            "language": detail.get("language", extracted.get("编程语言", "")),
            "license": detail.get("license", extracted.get("开源协议", "")),
            "audio_duration": detail.get("audio_duration", 0),
            "audio_size": detail.get("audio_size", 0),
            "md_size": detail.get("md_size", 0),
            "has_audio": detail.get("has_audio", False),
            "description": detail.get("description", ""),
            "extracted_metrics": extracted,
            "path": f"/project/{detail.get('dir', '')}/{name}",
        })

    # 构建对比维度
    metrics = _build_comparison_metrics(projects_data)

    return {
        "projects": projects_data,
        "metrics": [m.__dict__ for m in metrics],
        "project_count": len(projects_data),
    }


def _build_comparison_metrics(projects: list[dict]) -> list[ComparisonMetric]:
    """构建对比维度列表。"""
    metrics: list[ComparisonMetric] = []

    # 基础维度
    basic_dims = [
        ("stars", "GitHub 星标"),
        ("forks", "Fork 数"),
        ("language", "编程语言"),
        ("license", "开源协议"),
        ("audio_duration", "音频时长(秒)"),
        ("audio_size", "音频大小(bytes)"),
        ("md_size", "文档大小(bytes)"),
    ]

    for key, label in basic_dims:
        values = {}
        for p in projects:
            values[p["name"]] = p.get(key, "")
        # 检查是否有差异
        non_empty = [v for v in values.values() if v != "" and v != 0]
        is_diff = len(set(str(v) for v in non_empty)) > 1 if len(non_empty) > 1 else False
        metrics.append(ComparisonMetric(key=key, label=label, values=values, is_highlighted=is_diff))

    # 从提取的指标中添加额外维度
    all_extracted_keys: set[str] = set()
    for p in projects:
        all_extracted_keys.update(p.get("extracted_metrics", {}).keys())

    for ext_key in sorted(all_extracted_keys):
        if ext_key in ("项目名称",):
            continue
        values = {}
        for p in projects:
            values[p["name"]] = p.get("extracted_metrics", {}).get(ext_key, "")
        non_empty = [v for v in values.values() if v]
        is_diff = len(set(str(v) for v in non_empty)) > 1 if len(non_empty) > 1 else False
        metrics.append(ComparisonMetric(key=ext_key, label=ext_key, values=values, is_highlighted=is_diff))

    return metrics


def generate_comparison_table(comparison_data: dict[str, Any]) -> str:
    """生成 HTML 对比表格。

    Args:
        comparison_data: compare_projects() 返回的数据

    Returns:
        HTML 表格字符串
    """
    if "error" in comparison_data:
        return f'<div class="error">{comparison_data["error"]}</div>'

    projects = comparison_data.get("projects", [])
    metrics = comparison_data.get("metrics", [])

    if not projects or not metrics:
        return '<div class="empty">无对比数据</div>'

    # 表头
    header_cells = ["<th>对比维度</th>"]
    for p in projects:
        name = p["name"]
        path = p.get("path", "#")
        header_cells.append(f'<th><a href="{path}" style="color:inherit;text-decoration:none;">{name}</a></th>')

    rows = [f"<tr>{''.join(header_cells)}</tr>"]

    # 数据行
    for m in metrics:
        label = m["label"]
        values = m["values"]
        is_highlighted = m.get("is_highlighted", False)

        cells = [f"<td><strong>{label}</strong></td>"]
        for p in projects:
            val = values.get(p["name"], "")
            # 格式化数值
            if isinstance(val, (int, float)) and val > 0:
                if m["key"] == "stars" or m["key"] == "forks":
                    display = f"{val:,}"
                elif m["key"] == "audio_duration":
                    mins = int(val // 60)
                    secs = int(val % 60)
                    display = f"{mins}:{secs:02d}"
                elif m["key"] in ("audio_size", "md_size"):
                    display = f"{val / 1024:.1f} KB"
                else:
                    display = str(val)
            elif val == "" or val == 0:
                display = '<span style="color:var(--text-dim);">—</span>'
            else:
                display = str(val)

            cell_class = ' class="diff"' if is_highlighted else ""
            cells.append(f"<td{cell_class}>{display}</td>")

        rows.append(f"<tr>{''.join(cells)}</tr>")

    return (
        '<table class="comparison-table" style="width:100%;border-collapse:collapse;font-size:13px;">'
        f'{"".join(rows)}'
        '</table>'
    )


def generate_radar_data(comparison_data: dict[str, Any]) -> dict[str, Any]:
    """生成 ECharts 雷达图数据。

    Args:
        comparison_data: compare_projects() 返回的数据

    Returns:
        ECharts radar 配置字典
    """
    projects = comparison_data.get("projects", [])
    if not projects:
        return {}

    # 雷达图维度（归一化到 0-100）
    indicators = [
        {"name": "星标", "max": 100},
        {"name": "文档", "max": 100},
        {"name": "音频", "max": 100},
        {"name": "Fork", "max": 100},
    ]

    # 找最大值用于归一化
    max_stars = max((p.get("stars", 0) for p in projects), default=1) or 1
    max_forks = max((p.get("forks", 0) for p in projects), default=1) or 1
    max_md = max((p.get("md_size", 0) for p in projects), default=1) or 1
    max_audio = max((p.get("audio_size", 0) for p in projects), default=1) or 1

    series_data = []
    for p in projects:
        values = [
            round(p.get("stars", 0) / max_stars * 100, 1),
            round(p.get("md_size", 0) / max_md * 100, 1),
            round(p.get("audio_size", 0) / max_audio * 100, 1),
            round(p.get("forks", 0) / max_forks * 100, 1),
        ]
        series_data.append({"name": p["name"], "value": values})

    return {
        "indicator": indicators,
        "series": series_data,
    }

"""Web dashboard package.

模块结构（阶段5 重构后）::

    web/
    ├── server.py          应用工厂 ``create_server()``
    ├── handler.py         HTTP 请求入口
    ├── routes.py          路由注册表 + ``set_output_dir()``
    ├── http_utils.py      HTTP 响应工具
    ├── renderer.py        Jinja2 + 模板渲染
    ├── templates.py       HTML 模板常量
    ├── api_handlers.py    API 端点处理函数
    ├── utils.py           兼容层（重新导出以下三个模块）
    ├── markdown_utils.py  Markdown 解析与转换
    ├── project_scanner.py 项目扫描与详情
    └── code_search.py     兼容垫片（逻辑已上移到 gh_trending_audio.code_search）
"""

from __future__ import annotations

"""Web dashboard server entry point (Phase 6: 应用工厂模式).

提供 ``create_server()`` 应用工厂函数，方便测试和嵌入。
保留 ``main()`` 命令行入口以兼容现有用法。
"""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from ..logging_config import get_logger
from .handler import DashboardHandler

logger = get_logger(__name__)


def create_server(host: str = "0.0.0.0", port: int = 8000) -> ThreadingHTTPServer:
    """创建 Web 服务器实例（应用工厂模式）。

    Args:
        host: 绑定地址
        port: 端口号

    Returns:
        配置好的 ThreadingHTTPServer 实例，已初始化流水线状态属性
    """
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    server.daemon_threads = True
    server.pipeline_running = False  # type: ignore[attr-defined]
    server.last_result = None  # type: ignore[attr-defined]
    server.last_error = None  # type: ignore[attr-defined]
    return server


def main() -> None:
    """命令行入口：启动 Web 仪表盘服务器。"""
    parser = argparse.ArgumentParser(description="GitHub Trending Audio Web 仪表盘")
    parser.add_argument("--port", type=int, default=8000, help="端口号（默认 8000）")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址")
    args = parser.parse_args()

    server = create_server(host=args.host, port=args.port)

    logger.info("═══ GitHub Trending Audio 仪表盘 ═══")
    logger.info("访问地址: http://localhost:%s", args.port)
    logger.debug("按 Ctrl+C 停止")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.warning("已停止")
        server.server_close()


if __name__ == "__main__":
    main()

"""Web dashboard server entry point."""

import argparse
from http.server import ThreadingHTTPServer

from rich.console import Console

from .handler import DashboardHandler

console = Console()


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending Audio Web 仪表盘")
    parser.add_argument("--port", type=int, default=8000, help="端口号（默认 8000）")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    server.daemon_threads = True
    server.pipeline_running = False
    server.last_result = None
    server.last_error = None

    console.print(f"\n[bold green]═══ GitHub Trending Audio 仪表盘 ═══[/bold green]")
    console.print(f"[cyan]访问地址: http://localhost:{args.port}[/cyan]")
    console.print(f"[dim]按 Ctrl+C 停止[/dim]\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]已停止[/yellow]")
        server.server_close()


if __name__ == "__main__":
    main()

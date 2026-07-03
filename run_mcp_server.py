import argparse
import os
import sys
from pathlib import Path

# 切换到项目根目录
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass


def run_stdio():
    """运行 stdio 传输模式。"""
    from mcp_server.server import mcp
    import anyio
    print("启动 MCP Server (stdio 模式)...", file=sys.stderr)
    anyio.run(mcp.run_stdio_async)


def run_sse(host: str, port: int):
    """运行 SSE 传输模式。"""
    from mcp_server.server import mcp
    import uvicorn

    print(f"启动 MCP Server (SSE 模式) @ http://{host}:{port}", file=sys.stderr)
    print(f"端点: /sse (SSE) 和 /messages (POST)", file=sys.stderr)

    mcp.settings.host = host
    mcp.settings.port = port
    uvicorn.run(mcp.sse_app(), host=host, port=port)


def main():
    parser = argparse.ArgumentParser(description="Ziki MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输模式: stdio (本地) 或 sse (HTTP，用于微信/飞书)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_SERVER_HOST", "0.0.0.0"),
        help="SSE 模式监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_SERVER_PORT", "8000")),
        help="SSE 模式监听端口 (默认: 8000)"
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        run_stdio()
    else:
        run_sse(args.host, args.port)


if __name__ == "__main__":
    main()

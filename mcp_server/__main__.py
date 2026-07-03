"""入口点：python -m mcp_server"""

from __future__ import annotations

import sys

from mcp_server.server import mcp


def main() -> None:
    """启动 Ziki MCP Server（stdio 传输）。"""
    try:
        import anyio
        anyio.run(mcp.run_stdio_async)
    except ImportError:
        print("需要 anyio 包，请执行: pip install anyio", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

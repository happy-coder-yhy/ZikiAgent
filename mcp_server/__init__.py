"""Ziki MCP Server — 暴露 Zata 平台工具给 MCP 客户端。"""

from mcp_server.server import create_app, mcp

__all__ = ["create_app", "mcp"]

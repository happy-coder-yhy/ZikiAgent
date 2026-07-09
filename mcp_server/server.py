"""Ziki MCP Server — FastMCP 应用创建与工具注册。

通过 MCP 协议向 LLM 暴露 Zata 平台工具，让模型能够：
1. 查询平台配置信息（项目、场景标签等）
2. 管理项目（查询列表、创建项目）
3. 创建场景采集任务

各工具按模块拆分在 mcp_server/admin/ 包下。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 加载 .env 文件
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    # 从项目根目录加载 .env
    _project_root = Path(__file__).parent.parent
    _env_file = _project_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv 未安装，使用系统环境变量

# ---------------------------------------------------------------------------
# 检查 MCP SDK 是否可用
# ---------------------------------------------------------------------------
_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP

    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 导入 Zata API 调用器
# ---------------------------------------------------------------------------
from ApiCaller.modules.api_caller import (
    APICallerConfig,
    ZataAPICaller,
)


# ---------------------------------------------------------------------------
# 凭证与调用器初始化
# ---------------------------------------------------------------------------

def _build_caller() -> ZataAPICaller:
    """从环境变量构建并认证 ZataAPICaller。"""
    base_url = os.environ.get("ZATA_BASE_URL")
    username = os.environ.get("ZATA_USERNAME")
    password = os.environ.get("ZATA_PASSWORD")
    organization = os.environ.get("ZATA_ORGANIZATION", "agent")

    if not base_url:
        print("FATAL: 环境变量 ZATA_BASE_URL 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    if not username:
        print("FATAL: 环境变量 ZATA_USERNAME 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("FATAL: 环境变量 ZATA_PASSWORD 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)

    config = APICallerConfig(base_url=base_url)
    caller = ZataAPICaller(config)
    caller.login(
        username=username,
        password=password,
        organization=organization,
    )
    return caller


# ---------------------------------------------------------------------------
# FastMCP 应用工厂
# ---------------------------------------------------------------------------

def create_app(caller: Optional[ZataAPICaller] = None) -> "FastMCP":
    """创建 FastMCP 实例并注册所有工具。

    Args:
        caller: 可选，已经认证的 ZataAPICaller。为 None 时从环境变量创建。

    Returns:
        FastMCP: 配置好的 MCP 应用实例。
    """
    if not _MCP_AVAILABLE:
        raise ImportError(
            "MCP server 需要 'mcp' 包。\n"
            f"安装命令: {sys.executable} -m pip install 'mcp'"
        )

    if caller is None:
        caller = _build_caller()

    mcp = FastMCP("ziki-platform")

    # -------------------------------------------------------------------
    # 注册各模块工具
    # -------------------------------------------------------------------
    from mcp_server.admin.platform_config import register_tools as register_platform_config
    from mcp_server.admin.scene_task import register_tools as register_scene_task
    from mcp_server.admin.project import register_tools as register_project
    from mcp_server.admin.task_work import register_tools as register_task_work
    from mcp_server.admin.scene_task_job import register_tools as register_scene_task_job
    from mcp_server.admin.device import register_tools as register_device

    register_platform_config(mcp, caller)
    register_scene_task(mcp, caller)
    register_project(mcp, caller)
    register_task_work(mcp, caller)
    register_scene_task_job(mcp, caller)
    register_device(mcp, caller)

    return mcp


# 模块级单例（供 __main__.py 和外部导入使用）
mcp = create_app()

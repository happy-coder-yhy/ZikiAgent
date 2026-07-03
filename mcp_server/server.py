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

    mcp = FastMCP(
        "ziki-platform",
        instructions=(
            "Ziki 数据采集平台工具。请严格按照以下流程操作：\n\n"
            "【项目管理】\n"
            "- 当用户询问有哪些项目时，调用 get_projects 查询项目列表。\n"
            "- 当用户要求创建新项目时：\n"
            "  1. 项目名称（name）为必填字段，用户未提供时必须先向用户询问。\n"
            "  2. 项目描述（description）为选填字段，用户未提供时也先询问一下，"
            "若用户明确表示不需要描述则跳过。\n"
            "  3. 询问完必填和选填信息后，调用 create_project 创建项目。\n\n"
            "【场景采集任务】\n"
            "1. 创建任务前，先调用 get_platform_config 获取可用的项目、场景、设备类型等参考信息。\n"
            "2. 调用 create_scene_task 创建场景采集任务，该工具有以下必填字段：\n"
            "   - project_id / scene_id / title（基本字段）\n"
            "   - task_type（任务类型：短程 / 长程，通过 get_platform_config 返回的 task_type_options 查看可用的类型及其ID）\n"
            "   - task_purpose_id（任务用途ID：通过 get_platform_config 返回的 task_purposes 列表查看用途名称及对应ID）\n"
            "   - difficulty（难度：简单 / 普通 / 困难）\n"
            "   - device_type_id（设备类型ID：通过 get_platform_config 返回的 device_types 列表查看）\n"
            "3. 重要：当用户指令缺少上述必填字段的值时，你必须主动逐一向用户询问缺失的字段值，"
            "直至所有必填字段信息完整，再调用 create_scene_task 创建任务。\n"
            "   例如用户只说\"创建场景任务\"而不提供任何细节，你需要逐一询问：项目、场景、"
            "任务标题、任务类型（短程/长程）、任务用途、难度、设备类型。\n"
        ),
    )

    # -------------------------------------------------------------------
    # 注册各模块工具
    # -------------------------------------------------------------------
    from mcp_server.admin.platform_config import register_tools as register_platform_config
    from mcp_server.admin.scene_task import register_tools as register_scene_task
    from mcp_server.admin.project import register_tools as register_project

    register_platform_config(mcp, caller)
    register_scene_task(mcp, caller)
    register_project(mcp, caller)

    return mcp


# 模块级单例（供 __main__.py 和外部导入使用）
mcp = create_app()

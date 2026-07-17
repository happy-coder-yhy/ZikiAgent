"""Ziki MCP Server — FastMCP 应用创建与工具注册。

通过 MCP 协议向 LLM 暴露 Zata 平台工具，让模型能够：
1. 查询平台配置信息（项目、场景标签等）
2. 管理项目（查询列表、创建项目）
3. 创建场景采集任务

各工具按模块拆分在 mcp_server/admin/ 包下。
"""

from __future__ import annotations

import contextvars
import functools
import json
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
# 用户上下文 — contextvars，由 core.py 在调用 agent 前设置
# ---------------------------------------------------------------------------

_current_user_ctx: contextvars.ContextVar[tuple[str, str]] = contextvars.ContextVar(
    "mcp_current_user", default=("", ""),
)


def set_user_context(user_id: str, session_id: str) -> None:
    """Set the current user context for MCP write-tool confirmation checks."""
    _current_user_ctx.set((user_id, session_id))


def _is_write_tool_name(name: str) -> bool:
    """Check if a tool name is a write operation (imports from ziki_agent lazily)."""
    try:
        from ziki_agent.roles import is_write_tool
        return is_write_tool(name)
    except Exception:
        return False  # safe fallback: don't block if module unavailable


def _wrap_write_tool(fn, tool_name: str):
    """Wrap a write-tool function so it requires a confirmed pending action.

    When a write tool is called WITHOUT a confirmed pending action for the
    current (user, session), the call is BLOCKED and a pending action is
    auto-created.  The model must present the confirmation to the user and
    wait for "确认" before retrying.
    """

    @functools.wraps(fn)
    def _guarded(*args, **kwargs):
        user_id, session_id = _current_user_ctx.get()
        if not user_id or not session_id:
            # No context — passthrough (shouldn't happen in normal operation)
            return fn(*args, **kwargs)

        try:
            from ziki_agent.confirmation import (
                list_pending_actions,
                create_pending_action,
                consume_action_once,
            )
        except Exception:
            return fn(*args, **kwargs)

        # Check for a confirmed action for this session
        pending = list_pending_actions(user_id, session_id)
        confirmed = [a for a in pending if a["status"] == "confirmed"]

        if confirmed:
            # Consume the first confirmed action and execute
            consume_action_once(confirmed[0]["action_id"])
            return fn(*args, **kwargs)

        # No confirmed action — auto-create one and BLOCK
        try:
            args_str = json.dumps(
                {"args": args, "kwargs": kwargs},
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            args_str = "{}"

        action_id = create_pending_action(
            user_id=user_id,
            session_id=session_id,
            role="",
            tool_name=tool_name,
            arguments_json=args_str,
        )

        return (
            "⛔ 写入操作已拦截 — 需要用户确认\n\n"
            f"操作 ID：{action_id}\n"
            f"工具名称：{tool_name}\n"
            f"调用参数：{args_str}\n\n"
            "请先向用户展示操作确认摘要（📋 操作确认表格），"
            "等待用户回复「确认」后，重新调用此工具。"
            "用户确认后此拦截将自动解除。"
        )

    return _guarded


# ---------------------------------------------------------------------------
# 凭证与调用器初始化
# ---------------------------------------------------------------------------

def _build_caller(access_token: Optional[str] = None) -> ZataAPICaller:
    """从环境变量构建并认证 ZataAPICaller。

    认证优先级：
    1. 参数 access_token 或环境变量 ZATA_ACCESS_TOKEN — 直接注入 token，跳过登录
    2. 环境变量 ZATA_USERNAME + ZATA_PASSWORD — 调用 login() 获取 token
    """
    base_url = os.environ.get("ZATA_BASE_URL")

    if not base_url:
        print("FATAL: 环境变量 ZATA_BASE_URL 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)

    config = APICallerConfig(base_url=base_url)
    caller = ZataAPICaller(config)

    # --- 认证方式一：直接使用 access_token（优先），生产环境中删去从环境变量中获取token的代码 ---
    token = access_token or os.environ.get("ZATA_ACCESS_TOKEN")
    if token:
        caller.set_access_token(access_token=token)
        print("[auth] 使用 access_token 认证", file=sys.stderr)
        return caller

    # --- 认证方式二：用户名密码登录（兼容），生产环境中删去---
    username = os.environ.get("ZATA_USERNAME")
    password = os.environ.get("ZATA_PASSWORD")
    organization = os.environ.get("ZATA_ORGANIZATION", "agent")

    if not username:
        print("FATAL: 环境变量 ZATA_USERNAME 或 ZATA_ACCESS_TOKEN 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("FATAL: 环境变量 ZATA_PASSWORD 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)

    print("[auth] 使用用户名密码登录", file=sys.stderr)
    caller.login(
        username=username,
        password=password,
        organization=organization,
    )
    return caller


# ---------------------------------------------------------------------------
# FastMCP 应用工厂
# ---------------------------------------------------------------------------

def create_app(
    caller: Optional[ZataAPICaller] = None,
    access_token: Optional[str] = None,
    tool_allowlist: Optional[set] = None,
) -> "FastMCP":
    """创建 FastMCP 实例并注册所有工具。

    Args:
        caller: 可选，已经认证的 ZataAPICaller。为 None 时从环境变量创建。
        access_token: 可选，直接传入 access_token（优先于环境变量）。
        tool_allowlist: 可选，工具名集合。提供时仅注册白名单内的工具，
            用于按角色限制工具可见性（admin/collector）。
            为 None 时注册全部 28 个 legacy 工具（向后兼容）。

    Returns:
        FastMCP: 配置好的 MCP 应用实例。
    """
    if not _MCP_AVAILABLE:
        raise ImportError(
            "MCP server 需要 'mcp' 包。\n"
            f"安装命令: {sys.executable} -m pip install 'mcp'"
        )

    if caller is None:
        caller = _build_caller(access_token=access_token)

    mcp = FastMCP("ziki-platform")

    # -------------------------------------------------------------------
    # 注册各模块工具（按白名单过滤）
    # -------------------------------------------------------------------
    from mcp_server.admin.platform_config import register_tools as register_platform_config
    from mcp_server.admin.scene_task import register_tools as register_scene_task
    from mcp_server.admin.project import register_tools as register_project
    from mcp_server.admin.task_work import register_tools as register_task_work
    from mcp_server.admin.scene_task_job import register_tools as register_scene_task_job
    from mcp_server.admin.device import register_tools as register_device
    from mcp_server.collector.task_job import register_tools as register_collector_task_job
    from mcp_server.collector.device import register_tools as register_collector_device

    registrations = [
        register_platform_config,
        register_scene_task,
        register_project,
        register_task_work,
        register_scene_task_job,
        register_device,
        register_collector_task_job,
        register_collector_device,
    ]

    if tool_allowlist is not None:
        # Role-scoped mode: wrap mcp.tool to filter registrations
        _original_tool = mcp.tool

        def _filtered_tool(*args, **kwargs):
            """Decorator that only registers the tool if its name is in the
            allowlist.  Preserves the original FastMCP tool() signature.
            Write tools are additionally wrapped with a confirmation guard."""
            name_from_kwargs = kwargs.get("name")

            # Case 1: @mcp.tool  — function passed directly (no parens)
            if len(args) == 1 and callable(args[0]) and not kwargs:
                func = args[0]
                fn_name = name_from_kwargs or getattr(func, "__name__", None)
                if isinstance(fn_name, str) and fn_name not in tool_allowlist:
                    return func  # skip
                if isinstance(fn_name, str) and _is_write_tool_name(fn_name):
                    func = _wrap_write_tool(func, fn_name)
                return _original_tool(func)

            # Case 2: @mcp.tool() or @mcp.tool(name="xxx")
            # The function name isn't known yet — intercept the decorator.
            real_decorator = _original_tool(*args, **kwargs)

            def _checking_decorator(fn):
                fn_name = name_from_kwargs or getattr(fn, "__name__", None)
                if isinstance(fn_name, str) and fn_name not in tool_allowlist:
                    return fn  # skip registration entirely
                if isinstance(fn_name, str) and _is_write_tool_name(fn_name):
                    fn = _wrap_write_tool(fn, fn_name)
                return real_decorator(fn)

            return _checking_decorator

        mcp.tool = _filtered_tool

        for register in registrations:
            register(mcp, caller)

        # Restore original tool() for safety
        mcp.tool = _original_tool
    else:
        # Legacy mode: register all 28 tools
        for register in registrations:
            register(mcp, caller)

    return mcp


# 模块级单例（供 __main__.py 和外部导入使用）
mcp = create_app()

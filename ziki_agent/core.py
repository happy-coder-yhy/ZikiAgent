"""Agent — Hermes AIAgent + in-process FastMCP (SSE on localhost).

Design:
  - FastMCP app (from mcp_server/server.py) runs in-process in a daemon thread
    via SSE on a random localhost port — no subprocess, direct Python calls
  - Hermes MCP connects via Streamable HTTP to localhost:<port>
  - Hermes AIAgent handles LLM reasoning + skills + memory
"""

from __future__ import annotations

import os
import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


# 写入工具命名模式 — 匹配这些前缀的视为写操作，需要确认
_WRITE_TOOL_PREFIXES = (
    "create_", "update_", "delete_", "bind_", "publish_",
    "change_", "claim_",
)


def _has_write_tools(tool_allowlist: frozenset[str]) -> bool:
    """检查白名单中是否包含写入工具。"""
    return any(t.startswith(_WRITE_TOOL_PREFIXES) for t in tool_allowlist)


def _build_system_prompt(role: str, tool_allowlist: frozenset[str]) -> str:
    """Construct a role-aware system prompt that tells the model exactly
    what it can and cannot do.

    The allowlist acts as a hard mechanism (tools literally aren't registered),
    but without the prompt the model doesn't know its boundaries — it will
    try to help by searching files or asking the user instead of refusing
    outright.  This prompt provides soft awareness so the model can:
      - politely explain *why* it can't fulfill a request
      - avoid wasting turns trying non-existent tools
    """

    tool_list = "\n".join(f"  - {t}" for t in sorted(tool_allowlist))
    can_write = _has_write_tools(tool_allowlist)

    # ---- 角色权限块 ----
    if role == "admin":
        role_block = f"""## 你的角色：管理员（只读）

你拥有以下只读查询工具，可以查询平台数据但不能创建或修改任何内容：
{tool_list}

**重要限制** — 你**没有**以下权限：
- ❌ 创建/修改/删除项目、任务、作业
- ❌ 创建场景任务、发布任务
- ❌ 绑定/解绑设备或采集器
- ❌ 任何写操作或修改操作

当用户要求你执行上述操作时，明确告知：
"抱歉，当前账号为只读权限，无法执行此操作。如需帮助，请联系管理员。"
不要尝试搜索文件或通过其他方式绕过 — 你的工具列表已经限定了你能做的事情。"""

    elif role == "collector":
        role_block = f"""## 你的角色：采集人员（只读）

你拥有以下只读查询工具，仅能查看与自己相关的采集任务和设备信息：
{tool_list}

**重要限制** — 你**没有**以下权限：
- ❌ 查看项目列表、平台配置
- ❌ 创建/管理任务、场景、作业
- ❌ 查看其他用户的任务或设备
- ❌ 任何管理操作

当用户要求你执行上述操作时，明确告知：
"抱歉，当前账号为采集人员权限，无法执行此操作。如需帮助，请联系管理员。"
不要尝试搜索文件或通过其他方式绕过 — 你的工具列表已经限定了你能做的事情。"""

    else:
        role_block = f"""## 你的角色：{role}
可用工具：
{tool_list}"""

    # ---- 写操作确认协议（仅当角色拥有写入工具时追加） ----
    confirmation_block = ""
    if can_write:
        confirmation_block = """
## 写操作确认协议（必须遵守）

你有权限执行写操作（创建、修改、删除、绑定等）。**每次调用写入工具前**，必须：

1. **收集参数** — 确保所有必填参数已从用户处获取，缺失的主动询问
2. **展示确认摘要** — 按以下格式展示即将执行的操作：

```
📋 **操作确认**

| 项目 | 内容 |
|------|------|
| 操作类型 | （如：创建场景任务） |
| ... | （列出所有关键参数） |

⚠️ 以上操作将提交到平台，确认执行？请回复 **"确认"** 继续。
```

3. **等待确认** — 用户必须明确回复 "确认" / "确认执行" / "yes" 后才能调用写入工具
4. **用户拒绝** — 如果用户回复 "取消" / "不" / "no" 或其他非确认内容，放弃操作

**注意**：
- 不要在用户确认前调用任何写入工具
- 只读查询（如 get_*、query_*、task_summary 等）无需确认，直接执行
- 如果用户在一次消息中已明确表达确认意图，可视为通过确认"""

    return f"""你叫 Ziki，是 Zata 数字采集平台的 AI 助手。

{role_block}
{confirmation_block}
## 通用规则
1. 使用提供的工具来查询平台数据，不要编造信息
2. 当用户意图不明确时，主动询问澄清
3. 以中文回复用户
4. 回答简洁明了，避免冗长
5. 你的可用工具是固定的 — 如果某个操作没有对应工具，说明你没有该权限，直接拒绝即可"""

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    response: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# In-process FastMCP runner
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_fastmcp_in_thread(tool_allowlist: set[str] | None = None) -> int:
    """Launch FastMCP SSE server in a daemon thread. Returns the port."""
    port = _find_free_port()
    logger.info("Starting FastMCP SSE on 127.0.0.1:%d", port)

    def _serve():
        from mcp_server.server import create_app, _build_caller
        import uvicorn

        caller = _build_caller()
        mcp = create_app(caller=caller, tool_allowlist=tool_allowlist)
        mcp.settings.host = "127.0.0.1"
        mcp.settings.port = port
        app = mcp.streamable_http_app()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    # Give the server a moment to boot
    time.sleep(1.5)
    return port


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class Agent:
    """Ziki Agent — Hermes AIAgent + in-process FastMCP tools.

    Args:
        role: "admin" or "collector". Controls which MCP tools are registered.
              Defaults to "admin" for backward compatibility.
    """

    def __init__(self, role: str = "admin") -> None:
        self._role = role

        # Resolve tool allowlist for this role
        from .roles import get_allowlist_for_role
        tool_allowlist = get_allowlist_for_role(role)

        # ---- 1. Start FastMCP in-process on a free port ----
        self._mcp_port = _start_fastmcp_in_thread(tool_allowlist=set(tool_allowlist))
        self._mcp_url = f"http://127.0.0.1:{self._mcp_port}/mcp"

        # ---- 2. Register MCP server with Hermes (via localhost HTTP) ----
        import tools.mcp_tool as _mcp
        _mcp.register_mcp_servers({
            "ziki": {
                "url": self._mcp_url,
                "enabled": True,
                "timeout": 120,
            },
        })
        logger.info("Hermes MCP connected to FastMCP at %s", self._mcp_url)

        # ---- 3. Provider & model ----
        provider = os.environ.get("ZIKI_PROVIDER")
        model = os.environ.get("ZIKI_LLM_MODEL")
        if not provider or not model:
            try:
                from hermes_cli.config import load_config
                cfg = load_config()
                provider = provider or cfg.get("model", {}).get("provider", "deepseek")
                model = model or cfg.get("model", {}).get("default", "deepseek-v4-flash")
            except Exception:
                pass
        provider = provider or "deepseek"
        model = model or "deepseek-v4-flash"

        # ---- 4. Create Hermes AIAgent ----
        from run_agent import AIAgent
        self._agent = AIAgent(
            provider=provider,
            model=model,
            quiet_mode=True,
            ephemeral_system_prompt=_build_system_prompt(role, tool_allowlist),
        )
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def run(
        self, session_id: str, user_message: str, user_id: str = "",
    ) -> AgentResult:
        """Execute one conversational turn.

        Args:
            session_id: conversation identifier.
            user_message: the user's latest message text.
            user_id: the authenticated user's UUID (from JWT). Used to
                     isolate sessions and tag persisted messages.
        """

        from . import memory
        history = memory.get_history(session_id, user_id=user_id)

        loop = asyncio.get_running_loop()
        try:
            raw_result = await loop.run_in_executor(
                self._executor,
                lambda: self._agent.run_conversation(
                    user_message=user_message,
                    conversation_history=history if history else None,
                ),
            )
        except Exception as e:
            logger.error("run_conversation failed: %s", e)
            error_msg = f"AI 服务暂时不可用: {e}"
            memory.add_message(session_id, "assistant", error_msg, user_id=user_id)
            return AgentResult(response=error_msg)

        final_response = raw_result.get("final_response", "") or ""
        all_messages = raw_result.get("messages", []) or []

        # Extract tool calls from Hermes messages (post-hoc)
        from .runs import extract_tool_calls_from_messages
        tool_calls = extract_tool_calls_from_messages(all_messages)

        memory.add_messages_batch(session_id, all_messages, user_id=user_id)

        return AgentResult(
            response=final_response,
            messages=all_messages,
            tool_calls=tool_calls,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
        if hasattr(self._agent, "close"):
            self._agent.close()

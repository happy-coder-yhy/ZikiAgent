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
import queue
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
        role_block = f"""## 你的角色：系统平台管理员

你是 Zata 数字采集平台的系统管理员，拥有全面的平台操作权限。

**设备管理**：
- 查询所有 EGO 设备的概要信息（在线/离线数量）和详细信息（具体配置、状态）
- 为 EGO 设备绑定或换绑作业
- 为 EGO 设备绑定或换绑采集员

**项目管理**：
- 查看平台上已有的项目列表
- 创建新项目

**任务与作业管理**：
- 查看已有的各类任务和作业的概要及详细情况
- 在场景任务内创建、修改、删除作业

**场景任务管理**：
- 创建场景任务
- 修改尚未发布的场景任务
- 发布场景任务

可用工具：
{tool_list}

对于查询类操作（概要、详情等），直接调用对应工具执行即可。
对于写入/修改类操作，务必遵循下方的写操作确认协议。"""

    elif role == "collector":
        role_block = f"""## 你的角色：数据采集员

你是 Zata 数字采集平台的数据采集人员，负责执行采集任务和操作个人设备。

**任务作业**：
- 查看当前与自己相关的所有任务作业及完成情况
- 领取已发布任务下的作业

**EGO 设备绑定**：
- 查看自己是否已被绑定到某个 EGO 设备
- 查询指定 EGO 设备的绑定情况（作业绑定、采集员绑定）
- 将指定 EGO 设备更换绑定为自己有采集权限的作业
- 将指定 EGO 设备更换绑定采集员为自己

可用工具：
{tool_list}

**你没有**以下权限：
- ❌ 查看平台全局项目列表、平台配置
- ❌ 创建/发布场景任务
- ❌ 查看其他用户的任务或设备
- ❌ 任何平台管理操作

当用户要求你执行上述管理操作时，明确告知：
"抱歉，当前账号为采集人员权限，无法执行此操作。如需帮助，请联系管理员。"

对于查询类操作，直接调用对应工具执行即可。
对于写入/绑定类操作，务必遵循下方的写操作确认协议。"""

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

        # ---- 5. Long-term memory manager (fire-and-forget every x turns) ----
        from .memory.long_term_memory import LongTermMemoryManager
        self._memory_manager = LongTermMemoryManager()

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

        # ---- Session isolation check ----
        if not memory.validate_session_owner(session_id, user_id):
            owner = memory.get_session_owner(session_id)
            return AgentResult(
                response=(
                    f"会话 {session_id} 不属于当前用户，无法访问。"
                    if owner else "会话访问验证失败。"
                ),
            )

        history = memory.get_history(session_id, user_id=user_id)

        # ---- Inject long-term memory into conversation context ----
        long_term = memory.get_long_term_memory(user_id, session_id)
        if long_term:
            history.insert(0, {
                "role": "system",
                "content": f"[用户长期记忆]\n{long_term}",
            })

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
            error_msg = "AI 服务暂时不可用，请稍后重试"
            memory.add_message(session_id, "assistant", error_msg, user_id=user_id)
            return AgentResult(response=error_msg)

        final_response = raw_result.get("final_response", "") or ""
        all_messages = raw_result.get("messages", []) or []

        # Extract tool calls from Hermes messages (post-hoc)
        from .runs import extract_tool_calls_from_messages
        tool_calls = extract_tool_calls_from_messages(all_messages)

        memory.add_messages_batch(session_id, all_messages, user_id=user_id)

        # ---- Trigger long-term memory update every x user turns ----
        user_msg_count = memory.count_user_messages(user_id, session_id)
        turn = 10
        if user_msg_count > 0 and user_msg_count % turn == 0:
            import sys
            print(
                f"[long-term-memory] Trigger fired: turn {user_msg_count} "
                f"for user={user_id} session={session_id}",
                file=sys.stderr, flush=True,
            )
            # Run in a separate daemon thread so it's truly fire-and-forget —
            # asyncio.create_task() can be unreliable in FastAPI when the
            # route handler returns immediately.
            import threading
            threading.Thread(
                target=lambda: asyncio.run(
                    self._memory_manager.update(user_id, session_id)
                ),
                daemon=True,
            ).start()

        return AgentResult(
            response=final_response,
            messages=all_messages,
            tool_calls=tool_calls,
        )

    async def run_stream(
        self, session_id: str, user_message: str, user_id: str = "",
    ):
        """Execute one conversational turn with streaming token output.

        Yields dicts:
            {"type": "token", "text": "..."}   — a text delta
            {"type": "done", "run_id": "...", "session_id": "...", "answer": "...", "tool_calls": [...]}
            {"type": "error", "message": "..."}

        The caller MUST iterate the generator to completion so that
        messages are persisted and long-term memory is updated.
        """
        from . import memory

        # ---- Session isolation check ----
        if not memory.validate_session_owner(session_id, user_id):
            yield {
                "type": "error",
                "message": f"会话 {session_id} 不属于当前用户，无法访问。",
            }
            return

        # ---- Pre-flight: same as run() ----
        history = memory.get_history(session_id, user_id=user_id)

        long_term = memory.get_long_term_memory(user_id, session_id)
        if long_term:
            history.insert(0, {
                "role": "system",
                "content": f"[用户长期记忆]\n{long_term}",
            })

        # ---- Thread-safe token bridge ----
        token_queue: queue.Queue = queue.Queue()
        result_holder: dict = {}

        def _stream_cb(delta_text: str) -> None:
            if delta_text:
                token_queue.put(("token", delta_text))

        def _run_blocking() -> None:
            try:
                result = self._agent.run_conversation(
                    user_message=user_message,
                    conversation_history=history if history else None,
                    stream_callback=_stream_cb,
                )
                result_holder["result"] = result
            except Exception as exc:
                logger.error("run_conversation (stream) failed: %s", exc)
                result_holder["error"] = str(exc)
            finally:
                token_queue.put(("done", None))

        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._executor, _run_blocking)

        # ---- Consume queue — yield tokens as they arrive ----
        while True:
            try:
                kind, payload = await loop.run_in_executor(
                    None,
                    lambda: token_queue.get(timeout=0.05),
                )
            except queue.Empty:
                continue

            if kind == "token":
                yield {"type": "token", "text": payload}
            elif kind == "done":
                break

        # Wait for the thread to fully finish
        await future

        # ---- Error handling ----
        error_msg = result_holder.get("error")
        if error_msg:
            logger.error("run_conversation (stream) failed: %s", error_msg)
            safe_msg = "AI 服务暂时不可用，请稍后重试"
            yield {
                "type": "error",
                "message": safe_msg,
            }
            memory.add_message(
                session_id, "assistant", safe_msg, user_id=user_id,
            )
            return

        raw_result = result_holder.get("result", {})
        final_response = raw_result.get("final_response", "") or ""
        all_messages = raw_result.get("messages", []) or []

        # ---- Extract tool calls ----
        from .runs import extract_tool_calls_from_messages
        tool_calls = extract_tool_calls_from_messages(all_messages)

        # ---- Persist messages ----
        memory.add_messages_batch(session_id, all_messages, user_id=user_id)

        # ---- Trigger long-term memory update every x user turns ----
        user_msg_count = memory.count_user_messages(user_id, session_id)
        turn = 10
        if user_msg_count > 0 and user_msg_count % turn == 0:
            import sys
            print(
                f"[long-term-memory] Trigger fired: turn {user_msg_count} "
                f"for user={user_id} session={session_id}",
                file=sys.stderr, flush=True,
            )
            threading.Thread(
                target=lambda: asyncio.run(
                    self._memory_manager.update(user_id, session_id)
                ),
                daemon=True,
            ).start()

        yield {
            "type": "done",
            "answer": final_response,
            "tool_calls": tool_calls,
        }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
        self._memory_manager.shutdown()
        if hasattr(self._agent, "close"):
            self._agent.close()

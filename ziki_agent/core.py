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

SYSTEM_PROMPT = """你叫 Ziki，是 Zata 数字采集平台的 AI 助手。

规则：
1. 使用提供的工具来查询平台数据，不要编造信息
2. 当用户意图不明确时，主动询问澄清
3. 以中文回复用户
4. 回答简洁明了，避免冗长"""

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    response: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# In-process FastMCP runner
# ---------------------------------------------------------------------------


def _find_free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_fastmcp_in_thread() -> int:
    """Launch FastMCP SSE server in a daemon thread. Returns the port."""
    port = _find_free_port()
    logger.info("Starting FastMCP SSE on 127.0.0.1:%d", port)

    def _serve():
        from mcp_server.server import create_app, _build_caller
        import uvicorn

        caller = _build_caller()
        mcp = create_app(caller=caller)
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
    """Ziki Agent — Hermes AIAgent + in-process FastMCP tools."""

    def __init__(self) -> None:
        # ---- 1. Start FastMCP in-process on a free port ----
        self._mcp_port = _start_fastmcp_in_thread()
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
            ephemeral_system_prompt=SYSTEM_PROMPT,
        )
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def run(self, session_id: str, user_message: str) -> AgentResult:
        """Execute one conversational turn."""

        from . import memory
        history = memory.get_history(session_id)

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
            memory.add_message(session_id, "assistant", error_msg)
            return AgentResult(response=error_msg)

        final_response = raw_result.get("final_response", "") or ""
        all_messages = raw_result.get("messages", []) or []

        memory.add_messages_batch(session_id, all_messages)

        return AgentResult(response=final_response, messages=all_messages)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
        if hasattr(self._agent, "close"):
            self._agent.close()

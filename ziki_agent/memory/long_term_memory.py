"""Long-term memory agent — extracts & persists important user info.

Uses a dedicated Hermes AIAgent (no MCP tools needed — text extraction only).
Triggered every x turns (configurable) per (user_id, session_id).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("long_term_memory")

_DB_PATH = Path(__file__).parent.parent / "conversations.db"

# ---------------------------------------------------------------------------
# System prompt for the memory-manager agent
# ---------------------------------------------------------------------------

MEMORY_MANAGER_SYSTEM_PROMPT = """你是记忆管理模块。

【规则】
请提取值得长期保存的信息，并更新 long_memory，要求：
- 不要记录ai说话者的信息，只记录user的信息
- 不要记录闲聊
- 不要编造内容
- 没有新信息则保持原样
- 合并重复信息
- 重点保留情绪与关系变化
- 总字符数不要超过5000
- 只输出 JSON，不要解释

【输出格式】
请提取值得长期保存的信息，并输出 JSON：
{
  "profile": "用户基本信息",
  "key_events": "...",
  "recent_state": "...",
  "memory_summary": "最终给模型看的完整记忆文本（<=3000字）"
}"""

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

import sqlite3


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


def _ensure_long_term_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memory (
            user_id     TEXT NOT NULL,
            session_id  TEXT NOT NULL,
            long_memory TEXT NOT NULL DEFAULT '',
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (user_id, session_id)
        )
    """)
    conn.commit()


def get_long_term_memory(user_id: str, session_id: str) -> str | None:
    """Return the stored long-term memory text, or None."""
    conn = _connect()
    _ensure_long_term_table(conn)
    row = conn.execute(
        "SELECT long_memory FROM long_term_memory WHERE user_id = ? AND session_id = ?",
        (user_id, session_id),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def upsert_long_term_memory(user_id: str, session_id: str, long_memory: str) -> None:
    """Insert or update the long-term memory for a user+session pair."""
    conn = _connect()
    _ensure_long_term_table(conn)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO long_term_memory (user_id, session_id, long_memory, updated_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, session_id) DO UPDATE SET "
        "  long_memory = excluded.long_memory, updated_at = excluded.updated_at",
        (user_id, session_id, long_memory, now),
    )
    conn.commit()
    conn.close()


def count_user_messages(user_id: str, session_id: str) -> int:
    """Count user-role messages in this session.  Used for the x-turn trigger."""
    conn = _connect()
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE user_id = ? AND session_id = ? AND role = 'user'",
        (user_id, session_id),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# LongTermMemoryManager
# ---------------------------------------------------------------------------


class LongTermMemoryManager:
    """Calls an LLM (via Hermes AIAgent) to extract long-term user memories.

    Created once per Agent (shared across sessions), with its own
    ThreadPoolExecutor for isolated async execution.
    """

    def __init__(self) -> None:
        # Resolve provider & model — same pattern as core.py Agent
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

        from run_agent import AIAgent
        self._agent = AIAgent(
            provider=provider,
            model=model,
            quiet_mode=True,
            ephemeral_system_prompt=MEMORY_MANAGER_SYSTEM_PROMPT,
        )
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def update(self, user_id: str, session_id: str) -> None:
        """Fetch recent messages, call LLM to extract long-term memory, persist.

        Fire-and-forget — does not raise to the caller.
        """
        turn = 10

        import sys
        try:
            # 1. Fetch the last N messages as context for the memory agent
            from .memory_management import get_history as get_short_history
            recent = get_short_history(session_id, user_id=user_id, limit=turn)
            print(
                f"[long-term-memory] Analysing {len(recent)} recent messages "
                f"for user={user_id} session={session_id}",
                file=sys.stderr, flush=True,
            )

            # 2. Build the user prompt: existing memory + recent conversation
            existing = get_long_term_memory(user_id, session_id) or ""
            user_prompt = self._build_user_prompt(recent, existing)

            # 3. Call the memory agent LLM
            loop = asyncio.get_running_loop()
            raw_result = await loop.run_in_executor(
                self._executor,
                lambda: self._agent.run_conversation(
                    user_message=user_prompt,
                    conversation_history=None,
                ),
            )

            final_response = raw_result.get("final_response", "") or ""
            if not final_response:
                print(
                    "[long-term-memory] LLM returned empty response",
                    file=sys.stderr, flush=True,
                )
                return

            # 4. Parse the JSON output and extract memory_summary
            memory_text = self._parse_response(final_response)
            if not memory_text:
                print(
                    "[long-term-memory] Failed to extract memory_summary from response",
                    file=sys.stderr, flush=True,
                )
                return

            # 5. Persist
            upsert_long_term_memory(user_id, session_id, memory_text)
            print(
                f"[long-term-memory] Updated: user={user_id} session={session_id} "
                f"({len(memory_text)} chars)",
                file=sys.stderr, flush=True,
            )
            logger.info(
                "Long-term memory updated for user=%s session=%s (%d chars)",
                user_id, session_id, len(memory_text),
            )

        except Exception:
            logger.exception(
                "Long-term memory update failed for user=%s session=%s",
                user_id, session_id,
            )
            import traceback
            print(
                f"[long-term-memory] EXCEPTION:\n{traceback.format_exc()}",
                file=sys.stderr, flush=True,
            )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
        if hasattr(self._agent, "close"):
            self._agent.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_prompt(
        messages: list[dict[str, Any]], existing_memory: str,
    ) -> str:
        """Format recent messages and existing memory for the memory agent."""
        lines: list[str] = []

        if existing_memory:
            lines.append("【当前 long_memory】")
            lines.append(existing_memory)
            lines.append("")

        lines.append("【最近对话】")
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Multi-modal content — extract text parts only
                text_parts = [
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                content = " ".join(text_parts)
            if content:
                lines.append(f"[{i}] {role}: {content}")

        lines.append("")
        lines.append("请根据以上对话，提取值得长期保存的信息并输出 JSON。")

        return "\n".join(lines)

    @staticmethod
    def _parse_response(raw: str) -> str:
        """Extract the memory_summary from the LLM's JSON response.

        Returns the memory_summary string, or the full raw text as fallback.
        """
        # Try to extract JSON from the response (may be wrapped in markdown)
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            end = text.find("\n")
            text = text[end + 1:] if end != -1 else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
            summary = data.get("memory_summary", "")
            if summary:
                return summary
        except json.JSONDecodeError:
            pass

        # Fallback: return the raw text (truncated to 5000 chars)
        return raw[:5000]

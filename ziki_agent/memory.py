"""Agent short-term memory — SQLite-backed conversation history per session.

Stores messages as JSON dicts in OpenAI/Hermes format. Each message is a
full dict that can be passed directly as conversation_history to Hermes.
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent / "conversations.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            msg_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id, id)")
    conn.commit()


def add_message(
    session_id: str,
    role: str,
    content: str = "",
    msg_json: dict | None = None,
) -> int:
    """Persist a single message.

    Args:
        session_id: conversation identifier.
        role: "user", "assistant", or "tool".
        content: plain-text content (for display / quick access).
        msg_json: the full message dict (OpenAI format). Stored as JSON
                  so it can be replayed verbatim as conversation_history.
    """
    conn = _connect()
    _ensure_table(conn)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO messages (session_id, role, content, msg_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, json.dumps(msg_json or {}, ensure_ascii=False), now),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def add_messages_batch(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist a batch of messages from Hermes result."""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        add_message(session_id, role, content, msg_json=msg)


def get_history(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return messages for *session_id* as a list of dicts ready for
    Hermes conversation_history.

    Reconstructs the full message dict from msg_json when available,
    falling back to {role, content} for older rows.
    """
    conn = _connect()
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT role, content, msg_json FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    conn.close()

    messages: list[dict[str, Any]] = []
    for role, content, msg_json_str in rows:
        try:
            full = json.loads(msg_json_str) if msg_json_str else {}
        except json.JSONDecodeError:
            full = {}
        # Use the stored full dict if it has meaningful content,
        # otherwise construct from role + content
        if full and full.get("role"):
            messages.append(full)
        elif content:
            messages.append({"role": role, "content": content})
    return messages


def clear_session(session_id: str) -> None:
    conn = _connect()
    _ensure_table(conn)
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def list_sessions() -> list[dict[str, Any]]:
    conn = _connect()
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT session_id, COUNT(*) as cnt, MAX(created_at) as last_msg "
        "FROM messages GROUP BY session_id ORDER BY last_msg DESC"
    ).fetchall()
    conn.close()
    return [{"session_id": r[0], "message_count": r[1], "last_message": r[2]} for r in rows]

"""Agent short-term memory — SQLite-backed conversation history per session.

Stores messages as JSON dicts in OpenAI/Hermes format. Each message is a
full dict that can be passed directly as conversation_history to Hermes.

Context window: only the most recent N messages are returned as conversation
history to keep the LLM prompt compact while older messages remain persisted
for future retrieval / auditing.

Multi-user: every message is tagged with a ``user_id`` extracted from the
JWT access_token. All queries are scoped to a specific user so sessions are
properly isolated.
"""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH = Path(__file__).parent.parent / "conversations.db"

# Size of the sliding context window — only the last N messages are included
# as conversation_history sent to the LLM.
CONTEXT_WINDOW_SIZE = 5


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


def _ensure_table(conn: sqlite3.Connection) -> None:
    """Create the messages table if it doesn't exist, and migrate older
    schemas that lack the user_id column."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            msg_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    # Migrate: add user_id column if this is an older database
    try:
        conn.execute("SELECT user_id FROM messages LIMIT 0")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE messages ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_session ON messages(user_id, session_id, id)"
    )
    conn.commit()


def add_message(
    session_id: str,
    role: str,
    content: str = "",
    msg_json: dict | None = None,
    user_id: str = "",
) -> int:
    """Persist a single message.

    Args:
        session_id: conversation identifier.
        role: "user", "assistant", or "tool".
        content: plain-text content (for display / quick access).
        msg_json: the full message dict (OpenAI format). Stored as JSON
                  so it can be replayed verbatim as conversation_history.
        user_id: the authenticated user who owns this message.
    """
    conn = _connect()
    _ensure_table(conn)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO messages (session_id, user_id, role, content, msg_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user_id, role, content,
         json.dumps(msg_json or {}, ensure_ascii=False), now),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def add_messages_batch(
    session_id: str, messages: list[dict[str, Any]], user_id: str = "",
) -> None:
    """Persist a batch of messages from Hermes result."""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content is None:
            content = ""
        elif not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        add_message(session_id, role, content, msg_json=msg, user_id=user_id)


def get_history(
    session_id: str, user_id: str = "", limit: int = CONTEXT_WINDOW_SIZE,
) -> list[dict[str, Any]]:
    """Return the most recent *limit* messages for *session_id* as a list
    of dicts ready for Hermes conversation_history.

    When *user_id* is provided, only messages belonging to that user are
    returned — this enforces session isolation between users.

    Uses a sliding context window: only the last N messages are returned
    (defaults to CONTEXT_WINDOW_SIZE). Older messages remain persisted in
    the database but are excluded from the LLM context.

    Reconstructs the full message dict from msg_json when available,
    falling back to {role, content} for older rows.
    """
    conn = _connect()
    _ensure_table(conn)
    # Fetch the most recent N rows (DESC), then reverse to chronological order
    rows = conn.execute(
        "SELECT role, content, msg_json FROM ("
        "  SELECT id, role, content, msg_json FROM messages"
        "  WHERE session_id = ? AND user_id = ?"
        "  ORDER BY id DESC LIMIT ?"
        ") ORDER BY id ASC",
        (session_id, user_id, limit),
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


def clear_session(session_id: str, user_id: str = "") -> None:
    """Delete all messages for a session.

    When *user_id* is provided, only deletes if the session contains
    messages belonging to that user (basic ownership check).
    """
    conn = _connect()
    _ensure_table(conn)
    if user_id:
        conn.execute(
            "DELETE FROM messages WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
    else:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def list_sessions(user_id: str = "") -> list[dict[str, Any]]:
    """Return all sessions, optionally filtered by *user_id*."""
    conn = _connect()
    _ensure_table(conn)
    if user_id:
        rows = conn.execute(
            "SELECT session_id, COUNT(*) as cnt, MAX(created_at) as last_msg "
            "FROM messages WHERE user_id = ? "
            "GROUP BY session_id ORDER BY last_msg DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT session_id, COUNT(*) as cnt, MAX(created_at) as last_msg "
            "FROM messages GROUP BY session_id ORDER BY last_msg DESC"
        ).fetchall()
    conn.close()
    return [
        {"session_id": r[0], "message_count": r[1], "last_message": r[2]}
        for r in rows
    ]


def session_belongs_to(session_id: str, user_id: str) -> bool:
    """Check whether *session_id* has any messages owned by *user_id*."""
    conn = _connect()
    _ensure_table(conn)
    row = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    conn.close()
    return (row[0] if row else 0) > 0

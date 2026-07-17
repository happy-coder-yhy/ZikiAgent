"""Agent run & tool-call persistence — SQLite-backed audit trail.

Tables:
  agent_runs         — one row per /chat request
  agent_tool_calls   — one row per MCP tool invocation within a run

Design:
  - Reuses the connection pattern from ziki_agent/memory.py.
  - Writes to the same database file (conversations.db) for simplicity.
  - Never stores tokens, raw platform responses, or exception messages.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent / "conversations.db"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _ensure_run_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            run_id          TEXT PRIMARY KEY,
            session_id      TEXT NOT NULL,
            user_id         TEXT NOT NULL DEFAULT '',
            role            TEXT NOT NULL DEFAULT 'admin',
            user_message    TEXT NOT NULL,
            idempotency_key TEXT,
            status          TEXT NOT NULL DEFAULT 'running',
            answer          TEXT,
            error_code      TEXT,
            started_at      TEXT NOT NULL,
            finished_at     TEXT,
            duration_ms     INTEGER,
            created_at      TEXT NOT NULL
        )
    """)
    # Migrate: add idempotency_key column if missing
    try:
        conn.execute("SELECT idempotency_key FROM agent_runs LIMIT 0")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE agent_runs ADD COLUMN idempotency_key TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_tool_calls (
            tool_call_id TEXT PRIMARY KEY,
            run_id       TEXT NOT NULL,
            tool_name    TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'running',
            started_at   TEXT NOT NULL,
            finished_at  TEXT,
            duration_ms  INTEGER,
            error_code   TEXT,
            created_at   TEXT NOT NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_session ON agent_runs(session_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_calls_run ON agent_tool_calls(run_id)"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Run CRUD
# ---------------------------------------------------------------------------


def create_run(
    session_id: str,
    user_message: str,
    *,
    user_id: str = "",
    role: str = "admin",
    idempotency_key: str = "",
) -> str:
    """Create a new agent run, returning its *run_id*.

    If *idempotency_key* is provided, it is stored for deduplication.
    """
    run_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    conn.execute(
        "INSERT INTO agent_runs (run_id, session_id, user_id, role, user_message,"
        " idempotency_key, status, started_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)",
        (run_id, session_id, user_id, role, user_message,
         idempotency_key or "", now, now),
    )
    conn.commit()
    conn.close()
    return run_id


def find_run_by_idempotency_key(
    user_id: str, session_id: str, idempotency_key: str,
) -> dict | None:
    """Find a completed or failed run by its idempotency key.

    Only returns runs that have finished (not 'running'), so the caller
    can safely return a cached result. Returns None if no match.
    """
    if not idempotency_key:
        return None
    conn = _connect()
    _ensure_run_tables(conn)
    row = conn.execute(
        "SELECT run_id, session_id, user_id, role, user_message,"
        " idempotency_key, status, answer, error_code,"
        " started_at, finished_at, duration_ms, created_at"
        " FROM agent_runs"
        " WHERE user_id = ? AND session_id = ? AND idempotency_key = ?"
        "   AND status IN ('completed', 'failed', 'cancelled')"
        " ORDER BY created_at DESC LIMIT 1",
        (user_id, session_id, idempotency_key),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "run_id": row[0], "session_id": row[1], "user_id": row[2],
        "role": row[3], "user_message": row[4], "idempotency_key": row[5],
        "status": row[6], "answer": row[7], "error_code": row[8],
        "started_at": row[9], "finished_at": row[10],
        "duration_ms": row[11], "created_at": row[12],
    }


def complete_run(run_id: str, answer: str) -> None:
    """Mark a run as completed and record timing."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    started = conn.execute(
        "SELECT started_at FROM agent_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    duration_ms = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started[0])
            duration_ms = int(
                (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            pass
    conn.execute(
        "UPDATE agent_runs SET status='completed', answer=?, finished_at=?,"
        " duration_ms=? WHERE run_id=?",
        (answer, now, duration_ms, run_id),
    )
    conn.commit()
    conn.close()


def fail_run(run_id: str, error_code: str) -> None:
    """Mark a run as failed — only stores a safe error code, never an
    exception message or stack trace."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    started = conn.execute(
        "SELECT started_at FROM agent_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    duration_ms = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started[0])
            duration_ms = int(
                (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            pass
    conn.execute(
        "UPDATE agent_runs SET status='failed', error_code=?, finished_at=?,"
        " duration_ms=? WHERE run_id=?",
        (error_code, now, duration_ms, run_id),
    )
    conn.commit()
    conn.close()


def cancel_run(run_id: str, reason: str = "user_cancelled") -> None:
    """Mark a run as cancelled by the user — distinct from failure.

    Uses status ``'cancelled'`` so the frontend can display "已停止"
    rather than treating it as an error.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    started = conn.execute(
        "SELECT started_at FROM agent_runs WHERE run_id = ?", (run_id,)
    ).fetchone()
    duration_ms = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started[0])
            duration_ms = int(
                (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            pass
    conn.execute(
        "UPDATE agent_runs SET status='cancelled', error_code=?, finished_at=?,"
        " duration_ms=? WHERE run_id=?",
        (reason, now, duration_ms, run_id),
    )
    conn.commit()
    conn.close()


def get_run(run_id: str) -> dict | None:
    """Return a run row as a dict, or None."""
    conn = _connect()
    _ensure_run_tables(conn)
    row = conn.execute(
        "SELECT run_id, session_id, user_id, role, user_message, status, answer,"
        " error_code, started_at, finished_at, duration_ms, created_at"
        " FROM agent_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "run_id": row[0],
        "session_id": row[1],
        "user_id": row[2],
        "role": row[3],
        "user_message": row[4],
        "status": row[5],
        "answer": row[6],
        "error_code": row[7],
        "started_at": row[8],
        "finished_at": row[9],
        "duration_ms": row[10],
        "created_at": row[11],
    }


def run_belongs_to(run_id: str, user_id: str) -> bool:
    """Check whether *run_id* was created by *user_id*."""
    conn = _connect()
    _ensure_run_tables(conn)
    row = conn.execute(
        "SELECT COUNT(*) FROM agent_runs WHERE run_id = ? AND user_id = ?",
        (run_id, user_id),
    ).fetchone()
    conn.close()
    return (row[0] if row else 0) > 0


def list_runs_by_session(session_id: str) -> list[dict]:
    """Return all runs for a session, newest first."""
    conn = _connect()
    _ensure_run_tables(conn)
    rows = conn.execute(
        "SELECT run_id, session_id, user_id, role, user_message, status, answer,"
        " error_code, started_at, finished_at, duration_ms, created_at"
        " FROM agent_runs WHERE session_id = ? ORDER BY created_at DESC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "run_id": r[0], "session_id": r[1], "user_id": r[2], "role": r[3],
            "user_message": r[4], "status": r[5], "answer": r[6],
            "error_code": r[7], "started_at": r[8], "finished_at": r[9],
            "duration_ms": r[10], "created_at": r[11],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# ToolCall CRUD
# ---------------------------------------------------------------------------


def start_tool_call(run_id: str, tool_name: str) -> str:
    """Record the start of a tool invocation. Returns *tool_call_id*."""
    call_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    conn.execute(
        "INSERT INTO agent_tool_calls (tool_call_id, run_id, tool_name, status,"
        " started_at, created_at)"
        " VALUES (?, ?, ?, 'running', ?, ?)",
        (call_id, run_id, tool_name, now, now),
    )
    conn.commit()
    conn.close()
    return call_id


def complete_tool_call(call_id: str) -> None:
    """Mark a tool call as successful."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    started = conn.execute(
        "SELECT started_at FROM agent_tool_calls WHERE tool_call_id = ?",
        (call_id,),
    ).fetchone()
    duration_ms = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started[0])
            duration_ms = int(
                (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            pass
    conn.execute(
        "UPDATE agent_tool_calls SET status='success', finished_at=?,"
        " duration_ms=? WHERE tool_call_id=?",
        (now, duration_ms, call_id),
    )
    conn.commit()
    conn.close()


def fail_tool_call(call_id: str, error_code: str = "tool_execution_failed") -> None:
    """Mark a tool call as failed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    started = conn.execute(
        "SELECT started_at FROM agent_tool_calls WHERE tool_call_id = ?",
        (call_id,),
    ).fetchone()
    duration_ms = None
    if started:
        try:
            start_dt = datetime.fromisoformat(started[0])
            duration_ms = int(
                (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            )
        except (ValueError, TypeError):
            pass
    conn.execute(
        "UPDATE agent_tool_calls SET status='failed', error_code=?, finished_at=?,"
        " duration_ms=? WHERE tool_call_id=?",
        (error_code, now, duration_ms, call_id),
    )
    conn.commit()
    conn.close()


def deny_tool_call(run_id: str, tool_name: str) -> str:
    """Record a denied tool call (role not authorised)."""
    call_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    conn.execute(
        "INSERT INTO agent_tool_calls (tool_call_id, run_id, tool_name, status,"
        " error_code, started_at, finished_at, duration_ms, created_at)"
        " VALUES (?, ?, ?, 'denied', 'tool_not_allowed_for_role', ?, ?, 0, ?)",
        (call_id, run_id, tool_name, now, now, now),
    )
    conn.commit()
    conn.close()
    return call_id


def list_tool_calls_by_run(run_id: str) -> list[dict]:
    """Return all tool calls for a run in chronological order."""
    conn = _connect()
    _ensure_run_tables(conn)
    rows = conn.execute(
        "SELECT tool_call_id, run_id, tool_name, status, error_code,"
        " started_at, finished_at, duration_ms, created_at"
        " FROM agent_tool_calls WHERE run_id = ? ORDER BY created_at ASC",
        (run_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "tool_call_id": r[0], "run_id": r[1], "tool_name": r[2],
            "status": r[3], "error_code": r[4], "started_at": r[5],
            "finished_at": r[6], "duration_ms": r[7], "created_at": r[8],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Bulk operations
# ---------------------------------------------------------------------------


def delete_runs_by_session(session_id: str) -> int:
    """Delete all runs and tool calls for *session_id*. Returns count of runs deleted."""
    conn = _connect()
    _ensure_run_tables(conn)
    # Get run_ids first to delete their tool calls
    run_ids = [
        r[0] for r in
        conn.execute(
            "SELECT run_id FROM agent_runs WHERE session_id = ?", (session_id,)
        ).fetchall()
    ]
    for rid in run_ids:
        conn.execute("DELETE FROM agent_tool_calls WHERE run_id = ?", (rid,))
    cursor = conn.execute(
        "DELETE FROM agent_runs WHERE session_id = ?", (session_id,)
    )
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count


def cleanup_stuck_runs() -> int:
    """Mark all runs still 'running' as 'failed' with error_code 'server_restart'.

    Called at startup to recover from crashes / unclean shutdowns.
    Returns the number of runs cleaned up.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_run_tables(conn)
    cursor = conn.execute(
        "UPDATE agent_runs SET status = 'failed', error_code = 'server_restart',"
        " finished_at = ? WHERE status = 'running'",
        (now,),
    )
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count


# ---------------------------------------------------------------------------
# Tool call extraction from Hermes messages
# ---------------------------------------------------------------------------


def extract_tool_calls_from_messages(
    messages: list[dict],
) -> list[dict]:
    """Parse Hermes conversation messages and return a list of tool-call
    summaries.  Each summary contains:

        tool_name   — the function name invoked
        status      — 'success' or 'failed'
        error_code  — None or a short error tag

    This is post-hoc extraction: tool calls are recorded *after* the turn
    completes rather than in real time.  For the MVP this is the simplest
    unified recording point that avoids touching all 28 tool definitions.
    """
    # Collect tool_call_ids from assistant messages
    tool_call_map: dict[str, str] = {}  # tool_call_id → tool_name
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            tc_id = tc.get("id", "")
            if name and tc_id:
                tool_call_map[tc_id] = name

    # Collect tool results
    tool_results: dict[str, bool] = {}  # tool_call_id → success
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        tc_id = msg.get("tool_call_id", "")
        if not tc_id:
            continue
        content = msg.get("content", "")
        # A tool result containing "error" or "Error" is treated as failed
        failed = isinstance(content, str) and "error" in content.lower()
        tool_results[tc_id] = not failed

    summaries: list[dict] = []
    for tc_id, tool_name in tool_call_map.items():
        success = tool_results.get(tc_id, True)
        summaries.append({
            "tool_name": tool_name,
            "status": "success" if success else "failed",
            "error_code": None if success else "tool_returned_error",
        })
    return summaries

"""Backend write-operation confirmation state machine.

Problem: The current confirmation flow relies entirely on the model obeying
system-prompt rules ("show summary → wait for confirm → call write tool").
There is no server-side state tracking, so:
  - A user saying "确认" could confirm ANY pending action (not just theirs).
  - An expired confirmation could still execute.
  - A confirmed action could execute twice (no idempotency guard).
  - Arguments could leak tokens / credentials.

This module adds a SQLite-backed state machine that persists pending write
operations with ownership, expiry, and atomic consume semantics.  It is
designed to be a standalone module — it does NOT modify core.py or server.py
(yet).  Integration happens in a later phase once the streaming refactor lands.

Usage (integration sketch)::

    # In agent.run(), when the model decides to call a write tool:
    action_id = create_pending_action(
        user_id=user_id, session_id=session_id, role=role,
        tool_name="create_project",
        arguments_json='{"name": "test"}',
    )
    # Return a confirmation prompt to the user (NOT calling the tool yet).

    # When the user sends "确认":
    action = confirm_action(action_id, user_id, session_id)
    # Now actually invoke the tool.

    # After the tool succeeds (idempotent guard):
    ok = consume_action_once(action_id)
    assert ok  # True on first call, False thereafter.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("confirmation")

_DB_PATH = Path(__file__).parent / "conversations.db"

# How long a pending action lives before it expires (minutes).
DEFAULT_TTL_MINUTES = 5

# Sub-strings that MUST NOT appear in arguments_json.
_FORBIDDEN_ARG_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"bearer\s+[\w\-\.]+",       # Bearer token
        r"authorization",            # Authorization header name
        r"cookie",                   # Cookie header or value
        r"x-api-key",                # API key header
        r"api[_-]?key",              # api_key / apikey
        r"access[_-]?token",         # access_token / accessToken
        r"refresh[_-]?token",        # refresh token
        r"password",                 # password field
        r"secret",                   # secret field
        r"zata[_-]?password",        # ZATA_PASSWORD env/field
        r"private[_-]?key",          # private key
    ]
]

# Maximum allowed length for arguments_json (prevents giant payloads).
_MAX_ARGUMENTS_BYTES = 64 * 1024  # 64 KB

# Valid status transitions.
# pending → confirmed → executed
# pending → cancelled
# pending → expired  (set by cleanup / check logic)
# confirmed → executed  (consume_action_once)
_VALID_STATUSES = frozenset({
    "pending", "confirmed", "cancelled", "expired", "executed",
})


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(_DB_PATH))


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_actions (
            action_id      TEXT PRIMARY KEY,
            user_id        TEXT NOT NULL,
            session_id     TEXT NOT NULL,
            role           TEXT NOT NULL DEFAULT '',
            tool_name      TEXT NOT NULL,
            arguments_json TEXT NOT NULL DEFAULT '{}',
            status         TEXT NOT NULL DEFAULT 'pending',
            created_at     TEXT NOT NULL,
            expires_at     TEXT NOT NULL,
            executed_at    TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pending_user_sess "
        "ON pending_actions(user_id, session_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pending_status "
        "ON pending_actions(status)"
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class ConfirmationError(ValueError):
    """Raised when a confirmation operation is invalid."""


def _validate_arguments_json(arguments_json: str) -> None:
    """Raise ConfirmationError if *arguments_json* looks suspicious.

    Checks:
      - Must be valid JSON.
      - Must not contain tokens / credentials / secrets.
      - Must not exceed the size limit.
    """
    if not arguments_json:
        return

    raw_bytes = arguments_json.encode("utf-8")
    if len(raw_bytes) > _MAX_ARGUMENTS_BYTES:
        raise ConfirmationError(
            f"arguments_json too large ({len(raw_bytes)} bytes, "
            f"max {_MAX_ARGUMENTS_BYTES})"
        )

    # Must be valid JSON
    try:
        json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ConfirmationError(
            f"arguments_json is not valid JSON: {exc}"
        ) from exc

    # Forbidden sub-strings
    for pattern in _FORBIDDEN_ARG_PATTERNS:
        if pattern.search(arguments_json):
            raise ConfirmationError(
                f"arguments_json contains forbidden pattern: {pattern.pattern!r}"
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_pending_action(
    user_id: str,
    session_id: str,
    role: str,
    tool_name: str,
    arguments_json: str = "{}",
    *,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> str:
    """Create a pending write-action that requires user confirmation.

    Args:
        user_id: The authenticated user who initiated the action.
        session_id: The conversation session.
        role: The user's role (admin / collector).
        tool_name: The write tool being requested (e.g. ``create_project``).
        arguments_json: JSON-encoded tool arguments.
        ttl_minutes: How many minutes until the action expires.

    Returns:
        *action_id* — a unique identifier for the pending action.

    Raises:
        ConfirmationError: if *arguments_json* contains sensitive data.
    """
    _validate_arguments_json(arguments_json)

    action_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl_minutes)

    conn = _connect()
    _ensure_table(conn)
    conn.execute(
        "INSERT INTO pending_actions "
        "(action_id, user_id, session_id, role, tool_name, arguments_json,"
        " status, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
        (
            action_id, user_id, session_id, role,
            tool_name, arguments_json,
            now.isoformat(), expires_at.isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    logger.info(
        "Created pending action %s: tool=%s user=%s session=%s role=%s",
        action_id, tool_name, user_id, session_id, role,
    )
    return action_id


def get_pending_action(action_id: str) -> dict[str, Any] | None:
    """Return a pending-action row as a dict, or None."""
    conn = _connect()
    _ensure_table(conn)
    row = conn.execute(
        "SELECT action_id, user_id, session_id, role, tool_name,"
        " arguments_json, status, created_at, expires_at, executed_at"
        " FROM pending_actions WHERE action_id = ?",
        (action_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None
    return {
        "action_id": row[0],
        "user_id": row[1],
        "session_id": row[2],
        "role": row[3],
        "tool_name": row[4],
        "arguments_json": row[5],
        "status": row[6],
        "created_at": row[7],
        "expires_at": row[8],
        "executed_at": row[9],
    }


def _transition_status(
    action_id: str,
    user_id: str,
    session_id: str,
    new_status: str,
) -> dict[str, Any]:
    """Validate ownership / session / expiry, then transition status.

    Returns the updated action dict.

    Raises:
        ConfirmationError: on any violation (wrong user, wrong session,
                           expired, already final, etc.).
    """
    if new_status not in _VALID_STATUSES:
        raise ConfirmationError(f"Invalid status: {new_status!r}")

    action = get_pending_action(action_id)
    if action is None:
        raise ConfirmationError(f"Action not found: {action_id!r}")

    # --- Ownership checks ---
    if action["user_id"] != user_id:
        raise ConfirmationError(
            f"User {user_id!r} cannot operate on action {action_id!r} "
            f"(owner is {action['user_id']!r})"
        )
    if action["session_id"] != session_id:
        raise ConfirmationError(
            f"Session {session_id!r} cannot operate on action {action_id!r} "
            f"(owned by session {action['session_id']!r})"
        )

    # --- Status checks ---
    current = action["status"]

    # Once in a final state, no further transitions
    if current in ("cancelled", "expired", "executed"):
        raise ConfirmationError(
            f"Action {action_id!r} is already {current}"
        )

    # pending → confirmed; confirmed → confirmed is idempotent (no-op)
    if new_status == "confirmed":
        if current == "confirmed":
            return action  # idempotent — already confirmed
        if current != "pending":
            raise ConfirmationError(
                f"Action {action_id!r} is {current}, not pending"
            )

    # Only pending or confirmed → cancelled
    if new_status == "cancelled" and current not in ("pending", "confirmed"):
        raise ConfirmationError(
            f"Cannot cancel action {action_id!r} in status {current}"
        )

    # --- Expiry check (only for confirm / cancel, not for system expiry) ---
    if new_status in ("confirmed", "cancelled"):
        expires_at = datetime.fromisoformat(action["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Auto-expire it first
            _mark_expired(action_id)
            raise ConfirmationError(
                f"Action {action_id!r} expired at {action['expires_at']}"
            )

    # --- Persist transition ---
    now = datetime.now(timezone.utc).isoformat()
    executed_at = now if new_status == "executed" else None

    conn = _connect()
    _ensure_table(conn)
    conn.execute(
        "UPDATE pending_actions SET status = ?, executed_at = ?"
        " WHERE action_id = ?",
        (new_status, executed_at, action_id),
    )
    conn.commit()
    conn.close()

    logger.info("Action %s: %s → %s", action_id, current, new_status)
    action["status"] = new_status
    if executed_at:
        action["executed_at"] = executed_at
    return action


def _mark_expired(action_id: str) -> None:
    """Set an action's status to 'expired' (internal helper)."""
    conn = _connect()
    _ensure_table(conn)
    conn.execute(
        "UPDATE pending_actions SET status = 'expired' WHERE action_id = ?",
        (action_id,),
    )
    conn.commit()
    conn.close()


def confirm_action(
    action_id: str, user_id: str, session_id: str,
) -> dict[str, Any]:
    """Confirm a pending action — called when the user says "确认".

    Validates:
      - *user_id* owns the action.
      - *session_id* matches the action's session.
      - The action has not expired.
      - The action is still in "pending" status.

    Returns the updated action dict with status "confirmed".

    Raises:
        ConfirmationError: on any validation failure.
    """
    return _transition_status(action_id, user_id, session_id, "confirmed")


def cancel_action(
    action_id: str, user_id: str, session_id: str,
) -> dict[str, Any]:
    """Cancel a pending or confirmed action — user said "取消".

    Same ownership / session / expiry validation as ``confirm_action``.

    Returns the updated action dict with status "cancelled".

    Raises:
        ConfirmationError: on any validation failure.
    """
    return _transition_status(action_id, user_id, session_id, "cancelled")


def consume_action_once(action_id: str) -> bool:
    """Atomically mark a confirmed action as executed.

    This is the idempotency guard — it succeeds **exactly once** per action.
    Designed to be called immediately before invoking the actual write tool.

    Returns:
        ``True`` if this call performed the transition (confirmed → executed).
        ``False`` if the action was already executed, cancelled, expired,
        or does not exist.

    Does NOT raise — callers should treat ``False`` as "do not execute".
    """
    conn = _connect()
    _ensure_table(conn)

    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "UPDATE pending_actions"
        " SET status = 'executed', executed_at = ?"
        " WHERE action_id = ? AND status = 'confirmed'",
        (now, action_id),
    )
    conn.commit()
    consumed = cursor.rowcount > 0
    conn.close()

    if consumed:
        logger.info("Action %s consumed (confirmed → executed)", action_id)
    else:
        # Check why — for logging only
        action = get_pending_action(action_id)
        if action is None:
            logger.warning(
                "consume_action_once: action %s not found", action_id,
            )
        else:
            logger.warning(
                "consume_action_once: action %s is %s (not confirmed)",
                action_id, action["status"],
            )

    return consumed


def cleanup_expired() -> int:
    """Mark all expired pending / confirmed actions as 'expired'.

    Returns the number of actions cleaned up.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    _ensure_table(conn)
    cursor = conn.execute(
        "UPDATE pending_actions SET status = 'expired'"
        " WHERE status IN ('pending', 'confirmed') AND expires_at < ?",
        (now,),
    )
    conn.commit()
    count = cursor.rowcount
    conn.close()
    if count:
        logger.info("Cleaned up %d expired action(s)", count)
    return count


def list_pending_actions(
    user_id: str, session_id: str,
) -> list[dict[str, Any]]:
    """Return all pending/confirmed actions for a (user, session) pair,
    newest first.  Useful for the client to display what's awaiting
    confirmation.
    """
    conn = _connect()
    _ensure_table(conn)
    rows = conn.execute(
        "SELECT action_id, user_id, session_id, role, tool_name,"
        " arguments_json, status, created_at, expires_at, executed_at"
        " FROM pending_actions"
        " WHERE user_id = ? AND session_id = ?"
        "   AND status IN ('pending', 'confirmed')"
        " ORDER BY created_at DESC",
        (user_id, session_id),
    ).fetchall()
    conn.close()
    return [
        {
            "action_id": r[0], "user_id": r[1], "session_id": r[2],
            "role": r[3], "tool_name": r[4], "arguments_json": r[5],
            "status": r[6], "created_at": r[7], "expires_at": r[8],
            "executed_at": r[9],
        }
        for r in rows
    ]

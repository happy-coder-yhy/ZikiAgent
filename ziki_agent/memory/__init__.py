"""Memory package — short-term and long-term conversation memory."""

from .memory_management import (
    CONTEXT_WINDOW_SIZE,
    add_message,
    add_messages_batch,
    get_history,
    clear_session,
    list_sessions,
    session_belongs_to,
)

from .long_term_memory import (
    LongTermMemoryManager,
    get_long_term_memory,
    upsert_long_term_memory,
    count_user_messages,
)

__all__ = [
    # short-term
    "CONTEXT_WINDOW_SIZE",
    "add_message",
    "add_messages_batch",
    "get_history",
    "clear_session",
    "list_sessions",
    "session_belongs_to",
    # long-term
    "LongTermMemoryManager",
    "get_long_term_memory",
    "upsert_long_term_memory",
    "count_user_messages",
]

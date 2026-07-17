"""Memory package — short-term and long-term conversation memory."""

from .memory_management import (
    CONTEXT_WINDOW_SIZE,
    add_message,
    add_messages_batch,
    get_history,
    get_complete_history,
    clear_session,
    list_sessions,
    session_belongs_to,
    get_session_owner,
    validate_session_owner,
)

from .long_term_memory import (
    LongTermMemoryManager,
    get_long_term_memory,
    upsert_long_term_memory,
    count_user_messages,
    delete_long_term_memory,
)

__all__ = [
    # short-term
    "CONTEXT_WINDOW_SIZE",
    "add_message",
    "add_messages_batch",
    "get_history",
    "get_complete_history",
    "clear_session",
    "list_sessions",
    "session_belongs_to",
    "get_session_owner",
    "validate_session_owner",
    # long-term
    "LongTermMemoryManager",
    "get_long_term_memory",
    "upsert_long_term_memory",
    "count_user_messages",
    "delete_long_term_memory",
]

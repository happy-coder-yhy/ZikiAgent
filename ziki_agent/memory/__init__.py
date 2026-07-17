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
    get_session_title,
    upsert_session_title,
    delete_session_title,
)

from .long_term_memory import (
    LongTermMemoryManager,
    get_long_term_memory,
    upsert_long_term_memory,
    count_user_messages,
    delete_long_term_memory,
)

from .session_title import (
    SessionTitleManager,
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
    "get_session_title",
    "upsert_session_title",
    "delete_session_title",
    # long-term
    "LongTermMemoryManager",
    "get_long_term_memory",
    "upsert_long_term_memory",
    "count_user_messages",
    "delete_long_term_memory",
    # session title
    "SessionTitleManager",
]

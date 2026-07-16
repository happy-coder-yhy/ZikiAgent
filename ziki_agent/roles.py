"""Role definitions and tool allowlists for Ziki Agent.

Roles come from the trusted authentication layer (JWT bearer token), never
from user messages, prompt text, or model output.

Allowed roles:
  admin     — 13 read-only admin tools
  collector —  3 read-only collector tools
  unknown   —  any other value → rejected

These are code constants for the MVP, not database-backed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Allowed roles
# ---------------------------------------------------------------------------

ALLOWED_ROLES = frozenset({"admin", "collector"})


def validate_role(role: str) -> str:
    """Normalise and validate a role string.

    Returns the normalised role if valid.
    Raises ValueError for unknown roles.
    """
    role = role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise ValueError(f"不支持的角色: {role}")
    return role


# ---------------------------------------------------------------------------
# Tool allowlists
# ---------------------------------------------------------------------------
# These names match the 28 tools registered in mcp_server/server.py exactly.
# Keep in sync with the actual tool names from:
#   mcp_server/admin/*.py  and  mcp_server/collector/*.py

ADMIN_READONLY_TOOLS = frozenset({
    # platform_config
    "get_platform_config",
    "get_scene",
    "get_task_purpose",
    "search_user",
    # project
    "get_projects",
    # scene_task
    "get_scene_task",
    "create_scene_task",
    "update_scene_task",
    "publish_scene_task",   
    # task_work
    "task_summary",
    "task_detail",
    "job_summary",
    "job_detail",
    "task_job_details",
    # job_maintenance
    "create_job",
    "update_job",
    "delete_job",
    # device
    "device_summary",
    "device_detail",
})

COLLECTOR_READONLY_TOOLS = frozenset({
    "query_task_job",
    "query_my_device",
    "query_device_binding",
})


def get_allowlist_for_role(role: str) -> frozenset[str]:
    """Return the tool-name allowlist for *role*.

    Unknown roles raise ValueError.
    """
    role = validate_role(role)
    if role == "admin":
        return ADMIN_READONLY_TOOLS
    return COLLECTOR_READONLY_TOOLS


# ---------------------------------------------------------------------------
# Legacy tool list (for verification — all 28 must remain)
# ---------------------------------------------------------------------------

ALL_28_TOOLS = frozenset({
    # admin/platform_config (4)
    "get_platform_config", "get_scene", "get_task_purpose", "search_user",
    # admin/scene_task (4)
    "create_scene_task", "get_scene_task", "update_scene_task", "publish_scene_task",
    # admin/project (2)
    "get_projects", "create_project",
    # admin/task_work (5)
    "task_summary", "task_detail", "job_summary", "job_detail", "task_job_details",
    # admin/scene_task_job (3)
    "create_job", "update_job", "delete_job",
    # admin/device (4)
    "device_summary", "device_detail", "bind_collector_or_job", "change_bind",
    # collector/task_job (2)
    "query_task_job", "claim_job",
    # collector/device (4)
    "query_my_device", "query_device_binding", "bind_job_to_device", "bind_self_to_device",
})

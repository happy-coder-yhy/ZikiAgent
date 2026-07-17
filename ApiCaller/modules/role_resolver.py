"""Casdoor role resolver — maps platform role names to local roles via API.

Uses Zata RBAC ``GET /api/zata-rbac/userinfo`` to query the current user's
roles directly (with the user's own token).  Falls back to ``GET /user/roles``
(admin API) when called without a user token.

Platform → Local mapping:
  System-Administrator → admin
  Data-Collector       → collector
"""

from __future__ import annotations

import os
from typing import Optional

from .api_caller import APICallerConfig, ZataAPICaller

# ---------------------------------------------------------------------------
# Platform → local role mapping
# ---------------------------------------------------------------------------

_PLATFORM_ROLE_MAP = {
    "System-Administrator": "admin",
    "Data-Collector": "collector",
}

# ---------------------------------------------------------------------------
# Shared server-token caller (lazy, used only for fallback path)
# ---------------------------------------------------------------------------

_caller: Optional[ZataAPICaller] = None


def _get_caller() -> ZataAPICaller:
    """Return a shared ZataAPICaller using the server's admin token."""
    global _caller
    if _caller is not None:
        return _caller

    base_url = os.environ.get("ZATA_BASE_URL", "http://10.9.103.101:30080/")
    config = APICallerConfig(base_url=base_url)
    _caller = ZataAPICaller(config)

    access_token = os.environ.get("ZATA_ACCESS_TOKEN", "")
    if access_token:
        _caller.set_access_token(access_token)
    else:
        username = os.environ.get("ZATA_USERNAME", "admin")
        password = os.environ.get("ZATA_PASSWORD", "")
        organization = os.environ.get("ZATA_ORGANIZATION", "agent")
        resp = _caller.login(username, password, organization)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Casdoor 登录失败: status={resp.status_code}, body={resp.body}"
            )

    return _caller


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _resolve_via_userinfo(token: str) -> Optional[str]:
    """Primary path: call /userinfo with the end-user's own token.

    Returns the local role directly from the ``roles`` array.
    """
    base_url = os.environ.get("ZATA_BASE_URL", "http://10.9.103.101:30080/")
    config = APICallerConfig(base_url=base_url)
    caller = ZataAPICaller(config)
    caller.set_access_token(token)

    resp = caller.userinfo()
    if resp.status_code != 200:
        return None

    data = resp.body
    if not isinstance(data, dict):
        return None

    roles = data.get("roles") or []
    for role_name in roles:
        local_role = _PLATFORM_ROLE_MAP.get(role_name)
        if local_role:
            return local_role

    return None


def _resolve_via_role_list(user_id: str, user_name: str) -> Optional[str]:
    """Fallback: iterate all roles via admin API, match user by id/name."""
    caller = _get_caller()
    resp = caller.get_user_roles(page_num=1, page_size=100)
    if resp.status_code != 200:
        return None

    data = resp.body
    if not isinstance(data, dict):
        return None

    results = data.get("metadata", {}).get("results") or []
    for role_entry in results:
        role_name = role_entry.get("name", "")
        local_role = _PLATFORM_ROLE_MAP.get(role_name)
        if not local_role:
            continue
        users = role_entry.get("users") or []
        if user_id in users:
            return local_role
        if user_name and f"agent/{user_name}" in users:
            return local_role

    return None


def resolve_role_from_platform(
    user_id: str = "",
    user_name: str = "",
    token: str = "",
) -> Optional[str]:
    """Resolve the user's platform role and map to local role.

    Priority:
      1. **userinfo** — call ``GET /api/zata-rbac/userinfo`` with the
         end-user's own token.  The response contains a ``roles`` array
         (e.g. ``["System-Administrator"]``).  Fast, direct, no iteration.
      2. **role list** — call ``GET /user/roles`` with the server's admin
         token, then match *user_id* / *user_name* against each role's
         member list.  Used when no user token is available.

    Args:
        user_id: The user's unique ID (from JWT ``id`` / ``sub``).
        user_name: The user's login name (from JWT ``name``).
        token: The end-user's raw JWT (from ``Authorization: Bearer ...``).
               When provided, the primary ``userinfo`` path is used.

    Returns:
        Local role string (``"admin"`` or ``"collector"``), or ``None``.
    """
    # 1. Primary: userinfo with end-user token
    if token:
        resolved = _resolve_via_userinfo(token)
        if resolved:
            return resolved

    # 2. Fallback: iterate role list with server admin token
    if user_id:
        return _resolve_via_role_list(user_id, user_name)

    return None


def get_platform_role_map() -> dict:
    """Return a copy of the platform → local role mapping."""
    return dict(_PLATFORM_ROLE_MAP)

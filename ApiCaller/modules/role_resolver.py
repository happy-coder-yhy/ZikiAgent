"""Casdoor role resolver — maps platform role names to local roles via API.

When the JWT lacks a ``role`` claim, this module queries the Casdoor
``GET /user/roles`` API to find which platform role a user belongs to,
then maps it to the local role name used by the agent.

Platform → Local mapping:
  Data-Administrator → admin
  Data-Collector     → collector

.. note::

    The API returns user entries with an ``"agent/"`` prefix
    (e.g. ``"agent/collector"``), while the JWT ``name`` claim is bare
    (e.g. ``"collector"``).  We match on ``f"agent/{user_name}"``.
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
# Lazy-initialised API caller
# ---------------------------------------------------------------------------

_caller: Optional[ZataAPICaller] = None


def _get_caller() -> ZataAPICaller:
    """Return a shared ZataAPICaller instance, creating it on first call."""
    global _caller
    if _caller is not None:
        return _caller

    base_url = os.environ.get("ZATA_BASE_URL", "http://10.9.103.101:30080/")
    config = APICallerConfig(base_url=base_url)
    _caller = ZataAPICaller(config)

    # Use access_token from .env if set, otherwise fall back to login
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


def resolve_role_from_platform(user_id: str, user_name: str = "") -> Optional[str]:
    """Query Casdoor for a user's platform role and map to local role.

    Args:
        user_id: The user's unique ID (from JWT ``id`` / ``sub`` claim).
        user_name: The user's login name (from JWT ``name`` claim).
                   Used because the API stores users as ``"agent/{name}"``.

    Returns:
        Local role string (``"admin"`` or ``"collector"``), or ``None`` if
        the user is not found in any recognised role.
    """
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

        # Match: API returns "agent/{name}", JWT name is bare.
        # e.g. API "agent/collector" ↔ JWT name "collector"
        if user_id in users:
            return local_role
        if user_name and f"agent/{user_name}" in users:
            return local_role

    return None


def get_platform_role_map() -> dict:
    """Return a copy of the platform → local role mapping."""
    return dict(_PLATFORM_ROLE_MAP)

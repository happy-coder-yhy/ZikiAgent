"""JWT access_token decoding — extract user identity without verification.

The access_token is issued by Casdoor (internal auth gateway). We decode
without cryptographic verification because:
- The token comes from a trusted internal service
- We only need identity claims (id, name, displayName), not proof of authenticity
- Token expiry and signature are enforced by the gateway, not this service
"""

from __future__ import annotations

import base64
import json
from typing import Any


class TokenDecodeError(ValueError):
    """Raised when the access_token cannot be decoded."""


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a JWT access_token to extract user identity claims.

    Args:
        token: Raw JWT string (header.payload.signature).

    Returns:
        dict with keys: user_id (str), name (str), displayName (str).
        Also includes raw claims under a ``raw`` key for debugging.

    Raises:
        TokenDecodeError: If the token is malformed or missing required claims.
    """
    if not token or not isinstance(token, str):
        raise TokenDecodeError("access_token 不能为空")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise TokenDecodeError(
            f"JWT 格式无效：期望 3 段，实际 {len(parts)} 段"
        )

    try:
        # Pad and decode the payload segment (base64url, no validation)
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        claims: dict[str, Any] = json.loads(payload_bytes)
    except (ValueError, json.JSONDecodeError) as exc:
        raise TokenDecodeError(f"JWT payload 解码失败: {exc}") from exc

    user_id = claims.get("id") or claims.get("sub") or ""
    name = claims.get("name") or ""
    display_name = claims.get("displayName") or ""

    if not user_id:
        raise TokenDecodeError(
            "JWT payload 缺少用户标识字段（id 或 sub）"
        )

    return {
        "user_id": user_id,
        "name": name,
        "displayName": display_name,
        "raw": claims,
    }

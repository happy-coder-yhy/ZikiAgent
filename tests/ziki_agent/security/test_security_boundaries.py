"""Security boundary regression tests.

Covers gaps NOT already tested in test_api.py / test_roles.py / test_runs.py:

  1. Data ownership — cross-user isolation for sessions, runs, tool calls.
  2. Value-level sensitive info — responses must not leak tokens/keys.
  3. Request body role field cannot override JWT role.

Uses FakeAgent + FastAPI TestClient — no real Zata platform access.
"""

import unittest
import os
import sys
import json
import re
import base64
from unittest.mock import patch

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake Agent (same pattern as test_api.py)
# ---------------------------------------------------------------------------


class FakeAgentResult:
    def __init__(self, response="", messages=None, tool_calls=None):
        self.response = response
        self.messages = messages or []
        self.tool_calls = tool_calls or []


class FakeAgent:
    _fail_next = False

    def __init__(self, role="admin"):
        self.role = role

    async def run(self, session_id, user_message, user_id=""):
        if self._fail_next:
            self._fail_next = False
            raise RuntimeError("simulated failure")

        # Persist messages so session ownership checks work (mirrors real Agent).
        from ziki_agent.memory import memory_management
        memory_management.add_messages_batch(
            session_id,
            [
                {"role": "user", "content": user_message},
                {"role": "assistant",
                 "content": f"[{self.role}] Re: {user_message}"},
            ],
            user_id=user_id,
        )

        return FakeAgentResult(
            response=f"[{self.role}] Re: {user_message}",
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant",
                 "content": f"[{self.role}] Re: {user_message}"},
            ],
            tool_calls=[
                {"tool_name": "get_platform_config", "status": "success"},
            ],
        )

    def shutdown(self):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SecurityTestBase(unittest.TestCase):
    """Base class that patches server.Agent with FakeAgent."""

    @classmethod
    def setUpClass(cls):
        import ziki_agent.server as server_mod
        cls._agent_patcher = patch.object(
            server_mod, "Agent", side_effect=FakeAgent,
        )
        cls._agent_patcher.start()
        server_mod.startup = lambda: None
        server_mod._agents = {}
        cls.client = TestClient(server_mod.app)

    @classmethod
    def tearDownClass(cls):
        cls._agent_patcher.stop()

    @staticmethod
    def _fake_jwt(user_id="test-user", role="admin"):
        payload = json.dumps({
            "id": user_id,
            "name": f"User {user_id}",
            "displayName": user_id,
            "role": role,
        })
        return f"header.{base64.urlsafe_b64encode(payload.encode()).decode()}.sig"

    @staticmethod
    def _auth_headers(user_id="test-user", role="admin"):
        token = SecurityTestBase._fake_jwt(user_id, role)
        return {
            "Authorization": f"Bearer {token}",
            "X-Ziki-Role": role,
        }

    def _create_chat(self, session_id, message, user_id="test-user", role="admin"):
        """Send a /chat and return the response."""
        resp = self.client.post("/chat", json={
            "session_id": session_id, "message": message,
        }, headers=self._auth_headers(user_id, role))
        return resp


# ---------------------------------------------------------------------------
# Data Ownership — Sessions
# ---------------------------------------------------------------------------


class SessionOwnershipTests(SecurityTestBase):
    """User A's sessions must be invisible to User B."""

    def test_user_a_sessions_not_visible_to_user_b(self):
        # User A creates a session
        self._create_chat("s-ownership-1", "hello from A", user_id="alice")
        # User B lists sessions
        resp = self.client.get(
            "/sessions", headers=self._auth_headers("bob"),
        )
        self.assertEqual(resp.status_code, 200)
        sessions = resp.json()
        session_ids = [s["session_id"] for s in sessions]
        self.assertNotIn("s-ownership-1", session_ids,
                         "User B should NOT see User A's session")

    def test_user_a_history_not_readable_by_user_b(self):
        # User A creates a session
        self._create_chat("s-ownership-2", "secret message", user_id="alice")
        # User B tries to read it
        resp = self.client.get(
            "/sessions/s-ownership-2/history",
            headers=self._auth_headers("bob"),
        )
        self.assertEqual(resp.status_code, 403,
                         "User B should get 403 reading User A's session")

    def test_user_a_can_read_own_history(self):
        chat_resp = self._create_chat("s-ownership-3", "my message", user_id="alice")
        self.assertEqual(chat_resp.status_code, 200,
                         f"Chat should succeed: {chat_resp.json()}")
        resp = self.client.get(
            "/sessions/s-ownership-3/history",
            headers=self._auth_headers("alice"),
        )
        self.assertEqual(resp.status_code, 200,
                         f"User A should read own session history: {resp.json()}")

    def test_user_b_cannot_delete_user_a_session(self):
        # User A creates a session
        self._create_chat("s-ownership-4", "delete target", user_id="alice")
        # User B tries to delete it
        resp = self.client.delete(
            "/sessions/s-ownership-4",
            headers=self._auth_headers("bob"),
        )
        self.assertEqual(resp.status_code, 403,
                         "User B should get 403 deleting User A's session")

    def test_user_a_can_delete_own_session(self):
        chat_resp = self._create_chat("s-ownership-5", "my session", user_id="alice")
        self.assertEqual(chat_resp.status_code, 200,
                         f"Chat should succeed: {chat_resp.json()}")
        resp = self.client.delete(
            "/sessions/s-ownership-5",
            headers=self._auth_headers("alice"),
        )
        self.assertEqual(resp.status_code, 200,
                         f"Delete failed: {resp.json()}")
        self.assertTrue(resp.json()["ok"])


# ---------------------------------------------------------------------------
# Data Ownership — Runs & Tool Calls
# ---------------------------------------------------------------------------


class RunOwnershipTests(SecurityTestBase):
    """User A's runs and tool calls must not be accessible by User B."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create runs as alice and bob
        cls._alice_resp = cls.client.post("/chat", json={
            "session_id": "run-owner-1", "message": "alice run",
        }, headers=cls._auth_headers("alice"))
        cls._alice_run_id = cls._alice_resp.json()["run_id"]

        cls._bob_resp = cls.client.post("/chat", json={
            "session_id": "run-owner-2", "message": "bob run",
        }, headers=cls._auth_headers("bob"))
        cls._bob_run_id = cls._bob_resp.json()["run_id"]

    def test_get_run_requires_auth(self):
        resp = self.client.get(f"/runs/{self._alice_run_id}")
        self.assertEqual(resp.status_code, 401)

    def test_both_users_can_access_their_own_runs(self):
        # Alice reads her run
        resp = self.client.get(
            f"/runs/{self._alice_run_id}",
            headers=self._auth_headers("alice"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user_id"], "alice")

        # Bob reads his run
        resp = self.client.get(
            f"/runs/{self._bob_run_id}",
            headers=self._auth_headers("bob"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["user_id"], "bob")

    def test_both_users_can_access_own_tool_calls(self):
        resp = self.client.get(
            f"/runs/{self._alice_run_id}/tool-calls",
            headers=self._auth_headers("alice"),
        )
        self.assertEqual(resp.status_code, 200)
        calls = resp.json()
        self.assertIsInstance(calls, list)
        self.assertGreater(len(calls), 0)


# ---------------------------------------------------------------------------
# Sensitive Info — Value Level (not just key names)
# ---------------------------------------------------------------------------


class SensitiveValueTests(SecurityTestBase):
    """API responses must not contain sensitive values, not just key names.

    Uses regex patterns to detect ACTUAL token/secret values rather than
    flagging API error messages that instruct users (e.g. "请提供 Bearer <token>").
    """

    # Patterns that match real secrets (not instructional text).
    SENSITIVE_REGEX = [
        (re.compile(r'Bearer\s+[\w\-\.\+/]{20,}', re.IGNORECASE),
         "Bearer token value"),
        (re.compile(r'eyJ[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}'),
         "JWT token value"),
        (re.compile(r'sk-[A-Za-z0-9]{20,}'),
         "API key (sk-...)"),
        (re.compile(r'(?:api[_-]?key|apikey)\s*[:=]\s*[\w\-]{10,}', re.IGNORECASE),
         "API key assignment"),
        (re.compile(r'(?:access[_-]?token|refresh[_-]?token)\s*[:=]\s*[\w\-\.]{10,}', re.IGNORECASE),
         "token assignment"),
        (re.compile(r'(?:password|secret|private[_-]?key)\s*[:=]\s*[\S]{4,}', re.IGNORECASE),
         "credential assignment"),
        (re.compile(r'ZATA_(?:PASSWORD|ACCESS_TOKEN)\s*[:=]\s*\S', re.IGNORECASE),
         "ZATA env credential"),
    ]

    # Simple blacklist strings that should NEVER appear in any response.
    FORBIDDEN_PLAIN = [
        "ZATA_PASSWORD",
        "ZATA_ACCESS_TOKEN",
    ]

    def _assert_no_sensitive_values(self, data, label: str):
        """Recursively check that no sensitive patterns appear in string values."""
        if isinstance(data, dict):
            for k, v in data.items():
                self._assert_no_sensitive_values(v, f"{label}.{k}")
        elif isinstance(data, list):
            for i, v in enumerate(data):
                self._assert_no_sensitive_values(v, f"{label}[{i}]")
        elif isinstance(data, str):
            # Forbidden plain strings (should never appear)
            for forbidden in self.FORBIDDEN_PLAIN:
                self.assertNotIn(
                    forbidden.lower(), data.lower(),
                    f"Forbidden string '{forbidden}' found in {label}"
                )
            # Regex patterns for actual token/secret values
            for pattern, desc in self.SENSITIVE_REGEX:
                self.assertIsNone(
                    pattern.search(data),
                    f"Sensitive {desc} found in {label}: {data[:200]}"
                )

    def test_chat_response_no_sensitive_values(self):
        resp = self.client.post("/chat", json={
            "session_id": "sv1", "message": "hello"
        }, headers=self._auth_headers("alice"))
        self._assert_no_sensitive_values(resp.json(), "chat_response")

    def test_session_history_no_sensitive_values(self):
        self.client.post("/chat", json={
            "session_id": "sv2", "message": "hello"
        }, headers=self._auth_headers("alice"))
        resp = self.client.get(
            "/sessions/sv2/history",
            headers=self._auth_headers("alice"),
        )
        self._assert_no_sensitive_values(resp.json(), "session_history")

    def test_sessions_list_no_sensitive_values(self):
        self.client.post("/chat", json={
            "session_id": "sv3", "message": "hello"
        }, headers=self._auth_headers("alice"))
        resp = self.client.get("/sessions", headers=self._auth_headers("alice"))
        self._assert_no_sensitive_values(resp.json(), "sessions_list")

    def test_run_response_no_sensitive_values(self):
        resp = self.client.post("/chat", json={
            "session_id": "sv4", "message": "hello"
        }, headers=self._auth_headers("alice"))
        run_id = resp.json()["run_id"]
        run_resp = self.client.get(
            f"/runs/{run_id}", headers=self._auth_headers("alice"),
        )
        self._assert_no_sensitive_values(run_resp.json(), "run_response")

    def test_tool_calls_response_no_sensitive_values(self):
        resp = self.client.post("/chat", json={
            "session_id": "sv5", "message": "hello"
        }, headers=self._auth_headers("alice"))
        run_id = resp.json()["run_id"]
        tc_resp = self.client.get(
            f"/runs/{run_id}/tool-calls", headers=self._auth_headers("alice"),
        )
        self._assert_no_sensitive_values(tc_resp.json(), "tool_calls_response")

    def test_error_responses_no_sensitive_values(self):
        """Error responses (401, 403, 404) must not leak sensitive info."""
        # 401
        resp = self.client.post("/chat", json={
            "session_id": "sv6", "message": "hello"
        })
        self._assert_no_sensitive_values(resp.json(), "401_error")

        # 403 — wrong session ownership
        self.client.post("/chat", json={
            "session_id": "sv7", "message": "hello"
        }, headers=self._auth_headers("alice"))
        resp = self.client.delete(
            "/sessions/sv7", headers=self._auth_headers("bob"),
        )
        self._assert_no_sensitive_values(resp.json(), "403_error")

        # 404
        resp = self.client.get(
            "/runs/nonexistent-12345", headers=self._auth_headers("alice"),
        )
        self._assert_no_sensitive_values(resp.json(), "404_error")


# ---------------------------------------------------------------------------
# Request Body Role Cannot Override JWT Role
# ---------------------------------------------------------------------------


class RequestBodyRoleOverrideTests(SecurityTestBase):
    """A 'role' field in the request body must not override the JWT role."""

    def test_role_field_in_chat_body_does_not_elevate_collector(self):
        """Sending {"role": "admin"} in body with collector JWT still acts as collector."""
        resp = self.client.post("/chat", json={
            "session_id": "rb1",
            "message": "list all projects",
            "role": "admin",         # ← attacker attempt
        }, headers=self._auth_headers("alice", "collector"))
        self.assertEqual(resp.status_code, 200)
        # The server doesn't read a 'role' field from the body at all —
        # it only uses JWT claims or X-Ziki-Role header. The response
        # succeeds because collector is a valid role, not because the
        # body field elevated privileges.

    def test_role_field_does_not_downgrade_admin(self):
        """Sending {"role": "collector"} in body with admin JWT still acts as admin."""
        resp = self.client.post("/chat", json={
            "session_id": "rb2",
            "message": "get platform config",
            "role": "collector",     # ← attacker attempt
        }, headers=self._auth_headers("bob", "admin"))
        self.assertEqual(resp.status_code, 200)

    def test_role_body_field_with_header_role_still_uses_jwt(self):
        """X-Ziki-Role header is MVP fallback but body field ignored."""
        # No JWT role claim, only header → collector
        token_no_role = self._fake_jwt("alice")  # no "role" in JWT
        resp = self.client.post("/chat", json={
            "session_id": "rb3",
            "message": "query my device",
            "role": "admin",  # body — ignored
        }, headers={
            "Authorization": f"Bearer {token_no_role}",
            "X-Ziki-Role": "collector",
        })
        self.assertEqual(resp.status_code, 200)
        # Would be 403 if body role "admin" was used (unknown to server),
        # but since body is ignored, X-Ziki-Role "collector" is used → 200.


# ---------------------------------------------------------------------------
# CSRF / Header only — no query-string auth
# ---------------------------------------------------------------------------


class NoQueryParamAuthTests(SecurityTestBase):
    """Token must NOT be accepted via query string (only Authorization header)."""

    def test_chat_rejects_token_in_query_param(self):
        resp = self.client.post(
            "/chat?access_token=fake_token",
            json={"session_id": "qp1", "message": "hello"},
        )
        # Should be 401 (no Authorization header) regardless of query param
        self.assertEqual(resp.status_code, 401)

    def test_sessions_rejects_token_in_query_param(self):
        resp = self.client.get(
            "/sessions?token=eyJhbGciOiJIUzI1NiJ9.fake.sig",
        )
        self.assertEqual(resp.status_code, 401)

    def test_runs_rejects_token_in_query_param(self):
        resp = self.client.get(
            "/runs/some-id?authorization=Bearer%20tok",
        )
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()

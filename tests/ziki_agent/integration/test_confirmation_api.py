"""Confirmation API integration tests — fake agent + TestClient."""

import unittest
import os
import sys
import json
import base64
from unittest.mock import patch

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fake Agent (writable — returns write tool calls for post-chat audit)
# ---------------------------------------------------------------------------


class FakeAgentResult:
    def __init__(self, response="", messages=None, tool_calls=None):
        self.response = response
        self.messages = messages or []
        self.tool_calls = tool_calls or []


class FakeAgent:
    """FakeAgent that can return configurable tool calls."""

    def __init__(self, role="admin"):
        self.role = role

    async def run(self, session_id, user_message, user_id=""):
        from ziki_agent.memory import memory_management
        memory_management.add_messages_batch(
            session_id,
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"[{self.role}] Re: {user_message}"},
            ],
            user_id=user_id,
        )
        return FakeAgentResult(
            response=f"[{self.role}] Re: {user_message}",
            tool_calls=[
                {"tool_name": "get_platform_config", "status": "success"},
            ],
        )

    def shutdown(self):
        pass


class FakeAgentWithWrite(FakeAgent):
    """FakeAgent that returns a write tool call (for post-chat audit tests)."""

    async def run(self, session_id, user_message, user_id=""):
        from ziki_agent.memory import memory_management
        memory_management.add_messages_batch(
            session_id,
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": f"[{self.role}] 已创建项目"},
            ],
            user_id=user_id,
        )
        return FakeAgentResult(
            response=f"[{self.role}] 项目已创建",
            tool_calls=[
                {"tool_name": "get_platform_config", "status": "success"},
                {"tool_name": "create_project", "status": "success"},
            ],
        )


# ---------------------------------------------------------------------------
# Base test class
# ---------------------------------------------------------------------------


class ConfirmationAPITestBase(unittest.TestCase):
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

    def setUp(self):
        """Clean up any pending actions before each test to prevent cross-test
        pollution (all tests share the real conversations.db)."""
        from ziki_agent import confirmation
        # Clean all pending/confirmed actions created by tests
        import sqlite3
        conn = sqlite3.connect(str(confirmation._DB_PATH))
        confirmation._ensure_table(conn)
        conn.execute("DELETE FROM pending_actions")
        conn.commit()
        conn.close()

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
        token = ConfirmationAPITestBase._fake_jwt(user_id, role)
        return {
            "Authorization": f"Bearer {token}",
            "X-Ziki-Role": role,
        }

    def _create_pending(self, user_id="u1", session_id="s1",
                        tool_name="create_project",
                        arguments_json='{"name": "test"}',
                        role="admin"):
        """Helper: create a pending action directly via confirmation module."""
        from ziki_agent import confirmation
        return confirmation.create_pending_action(
            user_id=user_id, session_id=session_id, role=role,
            tool_name=tool_name, arguments_json=arguments_json,
        )

    def _auth_with_session(self, user_id="test-user", role="admin",
                           session_id="s1"):
        """Auth headers + X-Ziki-Session-Id."""
        headers = self._auth_headers(user_id, role)
        headers["X-Ziki-Session-Id"] = session_id
        return headers


# ---------------------------------------------------------------------------
# Pre-chat hook tests via /chat endpoint
# ---------------------------------------------------------------------------


class PreChatHookTests(ConfirmationAPITestBase):
    """Test _handle_pre_chat_confirmation behavior via /chat."""

    def test_confirm_message_with_pending_actions_confirms_and_passes_through(self):
        """User says '确认' with pending actions → confirms → agent still runs."""
        self._create_pending(user_id="alice", session_id="hook-1",
                             tool_name="create_project")
        resp = self.client.post("/chat", json={
            "session_id": "hook-1", "message": "确认",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        # Agent should have run normally (pass-through after confirmation)
        self.assertIn("Re: 确认", data["answer"])

        # Verify the action was confirmed
        from ziki_agent import confirmation
        action = confirmation.get_pending_action(
            confirmation.list_pending_actions("alice", "hook-1")[0]["action_id"]
        )
        self.assertEqual(action["status"], "confirmed",
                         "Action should be confirmed after pre-chat hook")

    def test_confirm_message_without_pending_actions_passes_through(self):
        """User says '确认' with no pending actions → pass through to agent."""
        resp = self.client.post("/chat", json={
            "session_id": "hook-2", "message": "确认",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Re: 确认", resp.json()["answer"])

    def test_cancel_message_with_pending_actions_short_circuits(self):
        """User says '取消' with pending actions → short-circuit, agent NOT called."""
        self._create_pending(user_id="alice", session_id="hook-3",
                             tool_name="create_project")
        self._create_pending(user_id="alice", session_id="hook-3",
                             tool_name="delete_job")
        resp = self.client.post("/chat", json={
            "session_id": "hook-3", "message": "取消",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "cancelled")
        self.assertIn("已取消", data["answer"])
        self.assertIn("2", data["answer"])  # 2 pending actions cancelled

    def test_cancel_message_without_pending_actions_passes_through(self):
        """User says '取消' with no pending actions → pass through to agent."""
        resp = self.client.post("/chat", json={
            "session_id": "hook-4", "message": "取消",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Re: 取消", resp.json()["answer"])

    def test_normal_message_not_intercepted(self):
        """Normal message (not confirm/cancel) → no hook intervention."""
        resp = self.client.post("/chat", json={
            "session_id": "hook-5", "message": "列出所有项目",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Re: 列出所有项目", resp.json()["answer"])

    def test_confirm_only_confirms_own_sessions_actions(self):
        """User A's '确认' should not affect User B's pending actions."""
        # User A has a pending action
        aid_a = self._create_pending(user_id="alice", session_id="hook-a",
                                     tool_name="create_project")
        # User B has a pending action
        aid_b = self._create_pending(user_id="bob", session_id="hook-b",
                                     tool_name="delete_job")
        # Alice says '确认'
        resp = self.client.post("/chat", json={
            "session_id": "hook-a", "message": "确认",
        }, headers=self._auth_headers("alice"))
        self.assertEqual(resp.status_code, 200)

        # Bob's action should still be pending
        from ziki_agent import confirmation
        action_b = confirmation.get_pending_action(aid_b)
        self.assertEqual(action_b["status"], "pending",
                         "Bob's action should NOT be affected by Alice's confirm")

    def test_multiple_confirm_keywords_work(self):
        """Various confirmation keywords should all trigger the hook."""
        self._create_pending(user_id="alice", session_id="hook-6",
                             tool_name="create_project")
        for keyword in ["好的", "yes", "ok", "可以", "执行", "是", "行", "好",
                        "确定", "同意", "confirm"]:
            # Re-create pending action since previous was confirmed
            from ziki_agent import confirmation
            pending = confirmation.list_pending_actions("alice", "hook-6")
            if not pending:
                self._create_pending(user_id="alice", session_id="hook-6",
                                     tool_name="create_project")

            resp = self.client.post("/chat", json={
                "session_id": "hook-6", "message": keyword,
            }, headers=self._auth_headers("alice"))
            self.assertEqual(resp.status_code, 200,
                             f"Keyword '{keyword}' should get 200")

    def test_multiple_cancel_keywords_work(self):
        """Various cancel keywords should all trigger the hook."""
        for keyword in ["取消", "不", "no", "算了", "别", "cancel", "放弃", "拒绝"]:
            sid = f"hook-cancel-{keyword}"
            self._create_pending(user_id="alice", session_id=sid,
                                 tool_name="create_project")
            resp = self.client.post("/chat", json={
                "session_id": sid, "message": keyword,
            }, headers=self._auth_headers("alice"))
            self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Confirmation API endpoint tests
# ---------------------------------------------------------------------------


class ConfirmationEndpointsTests(ConfirmationAPITestBase):
    """Test GET/POST /actions/* endpoints."""

    def test_list_pending_actions_returns_200(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s1")
        resp = self.client.get(
            "/actions/pending",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s1"),
        )
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0]["action_id"], aid)

    def test_list_pending_missing_session_header_returns_400(self):
        resp = self.client.get(
            "/actions/pending",
            headers=self._auth_headers("u1"),
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_pending_user_isolation(self):
        """User A cannot see User B's pending actions."""
        self._create_pending(user_id="alice", session_id="ep-iso")
        resp = self.client.get(
            "/actions/pending",
            headers=self._auth_with_session(user_id="bob", session_id="ep-iso"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 0,
                         "User B should see empty list for User A's actions")

    def test_confirm_action_returns_200(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s2")
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s2"),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "confirmed")

    def test_confirm_wrong_user_returns_403(self):
        aid = self._create_pending(user_id="alice", session_id="ep-s3")
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_with_session(user_id="bob", session_id="ep-s3"),
        )
        self.assertEqual(resp.status_code, 403)

    def test_confirm_wrong_session_returns_403(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s4")
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_with_session(user_id="u1", session_id="ep-wrong"),
        )
        self.assertEqual(resp.status_code, 403)

    def test_confirm_missing_session_header_returns_400(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s5")
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_headers("u1"),
        )
        self.assertEqual(resp.status_code, 400)

    def test_confirm_nonexistent_action_returns_403(self):
        resp = self.client.post(
            "/actions/nonexistent-id/confirm",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s6"),
        )
        self.assertEqual(resp.status_code, 403)

    def test_confirm_expired_action_returns_403(self):
        from ziki_agent import confirmation
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="ep-s7", role="admin",
            tool_name="create_project",
            arguments_json="{}",
            ttl_minutes=0,  # instantly expired
        )
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s7"),
        )
        self.assertEqual(resp.status_code, 403)

    def test_cancel_action_returns_200(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s8")
        resp = self.client.post(
            f"/actions/{aid}/cancel",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s8"),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "cancelled")

    def test_cancel_wrong_user_returns_403(self):
        aid = self._create_pending(user_id="alice", session_id="ep-s9")
        resp = self.client.post(
            f"/actions/{aid}/cancel",
            headers=self._auth_with_session(user_id="bob", session_id="ep-s9"),
        )
        self.assertEqual(resp.status_code, 403)

    def test_cancel_missing_session_header_returns_400(self):
        aid = self._create_pending(user_id="u1", session_id="ep-s10")
        resp = self.client.post(
            f"/actions/{aid}/cancel",
            headers=self._auth_headers("u1"),
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_excludes_cancelled_and_executed(self):
        """List only shows pending/confirmed, not cancelled/executed."""
        aid1 = self._create_pending(user_id="u1", session_id="ep-s11")
        aid2 = self._create_pending(user_id="u1", session_id="ep-s11")
        from ziki_agent import confirmation
        confirmation.cancel_action(aid1, "u1", "ep-s11")

        resp = self.client.get(
            "/actions/pending",
            headers=self._auth_with_session(user_id="u1", session_id="ep-s11"),
        )
        items = resp.json()
        action_ids = [i["action_id"] for i in items]
        self.assertNotIn(aid1, action_ids, "cancelled should not appear")
        self.assertIn(aid2, action_ids, "pending should appear")


# ---------------------------------------------------------------------------
# Post-chat audit tests
# ---------------------------------------------------------------------------


class PostChatAuditTests(ConfirmationAPITestBase):
    """Test _post_chat_audit — confirmed actions consumed after write tool execution."""

    def test_write_tool_call_with_confirmed_action_consumes_it(self):
        """After agent returns with write tool call, confirmed action is consumed."""
        from ziki_agent import confirmation
        import ziki_agent.server as server_mod

        # Create and confirm a pending action
        aid = self._create_pending(user_id="u1", session_id="audit-1",
                                   tool_name="create_project")
        confirmation.confirm_action(aid, "u1", "audit-1")

        # Patch Agent to return write tool calls for this test only
        with patch.object(server_mod, "Agent", side_effect=FakeAgentWithWrite):
            server_mod._agents = {}
            resp = self.client.post("/chat", json={
                "session_id": "audit-1", "message": "创建项目",
            }, headers=self._auth_headers("u1"))
            self.assertEqual(resp.status_code, 200)

        # The confirmed action should now be consumed (executed)
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "executed",
                         "Confirmed action should be consumed after write tool executes")

    def test_readonly_tool_calls_do_not_trigger_consume(self):
        """Read-only tool calls should NOT consume confirmed actions."""
        from ziki_agent import confirmation

        # Create and confirm a pending action
        aid = self._create_pending(user_id="u1", session_id="audit-2",
                                   tool_name="create_project")
        confirmation.confirm_action(aid, "u1", "audit-2")

        # Regular FakeAgent (only readonly tool calls) — already the default
        resp = self.client.post("/chat", json={
            "session_id": "audit-2", "message": "列出项目",
        }, headers=self._auth_headers("u1"))
        self.assertEqual(resp.status_code, 200)

        # Action should still be confirmed (not consumed by readonly calls)
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "confirmed",
                         "Readonly tool calls should not consume confirmed actions")


# ---------------------------------------------------------------------------
# Full lifecycle test
# ---------------------------------------------------------------------------


class FullConfirmationLifecycleTests(ConfirmationAPITestBase):
    """Test complete flow: create pending → confirm via API → consume via /chat."""

    def test_full_lifecycle_via_api(self):
        """Create, confirm via API, then verify post-chat consume."""
        from ziki_agent import confirmation
        import ziki_agent.server as server_mod

        # 1. Model decides to call write tool → frontend creates pending action
        aid = self._create_pending(user_id="u1", session_id="life-1",
                                   tool_name="create_project")

        # 2. User clicks 'confirm' button → frontend calls confirm API
        resp = self.client.post(
            f"/actions/{aid}/confirm",
            headers=self._auth_with_session(user_id="u1", session_id="life-1"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

        # 3. Agent executes the write tool → post-chat audit consumes
        with patch.object(server_mod, "Agent", side_effect=FakeAgentWithWrite):
            server_mod._agents = {}
            resp = self.client.post("/chat", json={
                "session_id": "life-1", "message": "创建项目",
            }, headers=self._auth_headers("u1"))
            self.assertEqual(resp.status_code, 200)

        # 4. Action should be consumed (executed) and not re-consumable
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "executed")
        self.assertFalse(confirmation.consume_action_once(aid))

    def test_cancel_stops_execution(self):
        """Cancel should prevent the action from being consumable."""
        from ziki_agent import confirmation

        aid = self._create_pending(user_id="u1", session_id="life-2",
                                   tool_name="delete_job")
        confirmation.confirm_action(aid, "u1", "life-2")

        # User cancels via API
        resp = self.client.post(
            f"/actions/{aid}/cancel",
            headers=self._auth_with_session(user_id="u1", session_id="life-2"),
        )
        self.assertEqual(resp.status_code, 200)

        # Cancelled action cannot be consumed
        self.assertFalse(confirmation.consume_action_once(aid))
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "cancelled")


# ---------------------------------------------------------------------------
# Unit: is_write_tool
# ---------------------------------------------------------------------------


class IsWriteToolTests(unittest.TestCase):
    """Test roles.is_write_tool function."""

    @classmethod
    def setUpClass(cls):
        _proj = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if _proj not in sys.path:
            sys.path.insert(0, _proj)

    def test_admin_write_tools_return_true(self):
        from ziki_agent.roles import is_write_tool
        self.assertTrue(is_write_tool("create_project"))
        self.assertTrue(is_write_tool("create_scene_task"))
        self.assertTrue(is_write_tool("update_scene_task"))
        self.assertTrue(is_write_tool("publish_scene_task"))
        self.assertTrue(is_write_tool("create_job"))
        self.assertTrue(is_write_tool("update_job"))
        self.assertTrue(is_write_tool("delete_job"))
        self.assertTrue(is_write_tool("bind_collector_or_job"))
        self.assertTrue(is_write_tool("change_bind"))

    def test_collector_write_tools_return_true(self):
        from ziki_agent.roles import is_write_tool
        self.assertTrue(is_write_tool("claim_job"))
        self.assertTrue(is_write_tool("bind_job_to_device"))
        self.assertTrue(is_write_tool("bind_self_to_device"))

    def test_readonly_tools_return_false(self):
        from ziki_agent.roles import is_write_tool
        self.assertFalse(is_write_tool("get_platform_config"))
        self.assertFalse(is_write_tool("get_scene"))
        self.assertFalse(is_write_tool("get_task_purpose"))
        self.assertFalse(is_write_tool("search_user"))
        self.assertFalse(is_write_tool("get_projects"))
        self.assertFalse(is_write_tool("get_scene_task"))
        self.assertFalse(is_write_tool("task_summary"))
        self.assertFalse(is_write_tool("task_detail"))
        self.assertFalse(is_write_tool("job_summary"))
        self.assertFalse(is_write_tool("job_detail"))
        self.assertFalse(is_write_tool("task_job_details"))
        self.assertFalse(is_write_tool("device_summary"))
        self.assertFalse(is_write_tool("device_detail"))
        self.assertFalse(is_write_tool("query_task_job"))
        self.assertFalse(is_write_tool("query_my_device"))
        self.assertFalse(is_write_tool("query_device_binding"))

    def test_unknown_tool_returns_false(self):
        from ziki_agent.roles import is_write_tool
        self.assertFalse(is_write_tool("nonexistent_tool"))
        self.assertFalse(is_write_tool(""))
        self.assertFalse(is_write_tool("rm -rf /"))


if __name__ == "__main__":
    unittest.main()

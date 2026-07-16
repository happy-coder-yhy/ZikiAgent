"""Confirmation state machine tests — fake DB, no real Zata platform."""

import unittest
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ziki_agent import confirmation


class ConfirmationDBIsolation(unittest.TestCase):
    """Each test class uses a temp DB to avoid polluting the real one."""

    @classmethod
    def setUpClass(cls):
        cls._orig_db = confirmation._DB_PATH
        import tempfile
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        confirmation._DB_PATH = type(confirmation._DB_PATH)(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        confirmation._DB_PATH = cls._orig_db
        os.unlink(cls._tmp.name)


class CreatePendingActionTests(ConfirmationDBIsolation):
    """Test create_pending_action."""

    def test_create_returns_action_id_and_pending_status(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "test"}',
        )
        self.assertTrue(len(aid) > 0)
        action = confirmation.get_pending_action(aid)
        self.assertIsNotNone(action)
        self.assertEqual(action["user_id"], "u1")
        self.assertEqual(action["session_id"], "s1")
        self.assertEqual(action["role"], "admin")
        self.assertEqual(action["tool_name"], "create_project")
        self.assertEqual(action["status"], "pending")
        self.assertIsNotNone(action["expires_at"])
        self.assertIsNone(action["executed_at"])

    def test_create_default_arguments_json(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="collector",
            tool_name="claim_job",
        )
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["arguments_json"], "{}")

    def test_create_accepts_empty_json(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="delete_job",
            arguments_json="{}",
        )
        self.assertIsNotNone(confirmation.get_pending_action(aid))

    def test_create_accepts_empty_string_arguments(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="delete_job",
            arguments_json="",
        )
        self.assertIsNotNone(confirmation.get_pending_action(aid))


class CreatePendingActionSecurityTests(ConfirmationDBIsolation):
    """Test that create_pending_action rejects sensitive arguments."""

    def _assert_rejected(self, arguments_json: str, label: str):
        with self.assertRaises(
            confirmation.ConfirmationError,
            msg=f"Should reject: {label}",
        ):
            confirmation.create_pending_action(
                user_id="u1", session_id="s1", role="admin",
                tool_name="create_project",
                arguments_json=arguments_json,
            )

    def test_rejects_bearer_token(self):
        self._assert_rejected(
            '{"token": "Bearer eyJhbGciOiJIUzI1NiJ9.xxx"}',
            "Bearer token in JSON",
        )

    def test_rejects_authorization_header(self):
        self._assert_rejected(
            '{"header": "Authorization"}',
            "Authorization string",
        )

    def test_rejects_cookie(self):
        self._assert_rejected(
            '{"cookie": "session=abc123"}',
            "Cookie value",
        )

    def test_rejects_api_key(self):
        self._assert_rejected(
            '{"x-api-key": "sk-abc123"}',
            "API key header",
        )
        self._assert_rejected(
            '{"api_key": "sk-abc123"}',
            "api_key field",
        )

    def test_rejects_access_token(self):
        self._assert_rejected(
            '{"access_token": "tok123"}',
            "access_token",
        )
        self._assert_rejected(
            '{"accessToken": "tok123"}',
            "accessToken camelCase",
        )

    def test_rejects_refresh_token(self):
        self._assert_rejected(
            '{"refresh_token": "rt123"}',
            "refresh_token",
        )

    def test_rejects_password(self):
        self._assert_rejected(
            '{"password": "secret123"}',
            "password field",
        )
        self._assert_rejected(
            '{"zata_password": "zp123"}',
            "zata_password field",
        )

    def test_rejects_secret(self):
        self._assert_rejected(
            '{"client_secret": "cs123"}',
            "secret field",
        )

    def test_rejects_private_key(self):
        self._assert_rejected(
            '{"private_key": "-----BEGIN RSA PRIVATE KEY-----"}',
            "private_key",
        )

    def test_rejects_invalid_json(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.create_pending_action(
                user_id="u1", session_id="s1", role="admin",
                tool_name="delete_job",
                arguments_json="{not valid json",
            )

    def test_rejects_oversized_arguments(self):
        big = "x" * (64 * 1024 + 1)
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.create_pending_action(
                user_id="u1", session_id="s1", role="admin",
                tool_name="create_project",
                arguments_json=f'{{"data": "{big}"}}',
            )


class ConfirmActionTests(ConfirmationDBIsolation):
    """Test confirm_action happy path and edge cases."""

    def setUp(self):
        self.aid = confirmation.create_pending_action(
            user_id="confirm-u1", session_id="confirm-s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "p1"}',
        )

    def test_confirm_sets_status_confirmed(self):
        action = confirmation.confirm_action(
            self.aid, "confirm-u1", "confirm-s1")
        self.assertEqual(action["status"], "confirmed")

    def test_confirm_is_idempotent(self):
        confirmation.confirm_action(self.aid, "confirm-u1", "confirm-s1")
        # Second confirm on already-confirmed should succeed (idempotent)
        action = confirmation.confirm_action(
            self.aid, "confirm-u1", "confirm-s1")
        self.assertEqual(action["status"], "confirmed")

    def test_confirm_wrong_user_rejected(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(self.aid, "confirm-u2", "confirm-s1")

    def test_confirm_wrong_session_rejected(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(self.aid, "confirm-u1", "confirm-s2")

    def test_confirm_nonexistent_action_rejected(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(
                "nonexistent", "confirm-u1", "confirm-s1")

    def test_confirm_cannot_skip_user_validation(self):
        """User B cannot confirm just by knowing user A's action_id."""
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(self.aid, "confirm-u2", "confirm-s2")

    def test_confirm_expired_action_rejected(self):
        # Create action with TTL=0 (immediately expired)
        aid = confirmation.create_pending_action(
            user_id="confirm-u1", session_id="confirm-s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "ephemeral"}',
            ttl_minutes=0,
        )
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(aid, "confirm-u1", "confirm-s1")


class CancelActionTests(ConfirmationDBIsolation):
    """Test cancel_action."""

    def setUp(self):
        self.aid = confirmation.create_pending_action(
            user_id="cancel-u1", session_id="cancel-s1", role="admin",
            tool_name="delete_job",
            arguments_json='{"scene_task_name": "t1"}',
        )

    def test_cancel_sets_status_cancelled(self):
        action = confirmation.cancel_action(
            self.aid, "cancel-u1", "cancel-s1")
        self.assertEqual(action["status"], "cancelled")

    def test_cancel_confirmed_action(self):
        confirmation.confirm_action(self.aid, "cancel-u1", "cancel-s1")
        action = confirmation.cancel_action(
            self.aid, "cancel-u1", "cancel-s1")
        self.assertEqual(action["status"], "cancelled")

    def test_cancel_wrong_user_rejected(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.cancel_action(self.aid, "cancel-u2", "cancel-s1")

    def test_cancel_wrong_session_rejected(self):
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.cancel_action(self.aid, "cancel-u1", "cancel-s2")

    def test_cancelled_cannot_be_confirmed(self):
        confirmation.cancel_action(self.aid, "cancel-u1", "cancel-s1")
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(self.aid, "cancel-u1", "cancel-s1")

    def test_cancel_expired_action_rejected(self):
        aid = confirmation.create_pending_action(
            user_id="cancel-u1", session_id="cancel-s1", role="admin",
            tool_name="create_project",
            arguments_json="{}",
            ttl_minutes=0,
        )
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.cancel_action(aid, "cancel-u1", "cancel-s1")


class ConsumeActionOnceTests(ConfirmationDBIsolation):
    """Test the atomic consume (idempotency) guard."""

    def setUp(self):
        self.aid = confirmation.create_pending_action(
            user_id="consume-u1", session_id="consume-s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "p1"}',
        )
        confirmation.confirm_action(self.aid, "consume-u1", "consume-s1")

    def test_first_consume_returns_true(self):
        self.assertTrue(confirmation.consume_action_once(self.aid))
        action = confirmation.get_pending_action(self.aid)
        self.assertEqual(action["status"], "executed")
        self.assertIsNotNone(action["executed_at"])

    def test_second_consume_returns_false(self):
        self.assertTrue(confirmation.consume_action_once(self.aid))
        self.assertFalse(confirmation.consume_action_once(self.aid))

    def test_consume_pending_returns_false(self):
        """Cannot consume an action that hasn't been confirmed yet."""
        aid2 = confirmation.create_pending_action(
            user_id="consume-u1", session_id="consume-s1", role="admin",
            tool_name="delete_job",
            arguments_json="{}",
        )
        self.assertFalse(confirmation.consume_action_once(aid2))
        action = confirmation.get_pending_action(aid2)
        self.assertEqual(action["status"], "pending")

    def test_consume_cancelled_returns_false(self):
        confirmation.cancel_action(self.aid, "consume-u1", "consume-s1")
        self.assertFalse(confirmation.consume_action_once(self.aid))

    def test_consume_nonexistent_returns_false(self):
        self.assertFalse(confirmation.consume_action_once("nonexistent"))

    def test_consume_is_atomic_against_race(self):
        """Two consumes on the same action: only one succeeds."""
        # Simulate two concurrent callers
        r1 = confirmation.consume_action_once(self.aid)
        r2 = confirmation.consume_action_once(self.aid)
        # Exactly one succeeds (order doesn't matter — first gets True)
        self.assertTrue(r1 or r2)
        # At least one fails
        self.assertFalse(r1 and r2)


class CleanupExpiredTests(ConfirmationDBIsolation):
    """Test cleanup_expired."""

    def test_cleans_up_expired_pending_actions(self):
        for _ in range(3):
            confirmation.create_pending_action(
                user_id="u1", session_id="s1", role="admin",
                tool_name="create_project",
                arguments_json="{}",
                ttl_minutes=0,  # instantly expired
            )
        count = confirmation.cleanup_expired()
        self.assertEqual(count, 3)

    def test_does_not_touch_executed_actions(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="create_project",
            arguments_json="{}",
        )
        confirmation.confirm_action(aid, "u1", "s1")
        confirmation.consume_action_once(aid)
        count = confirmation.cleanup_expired()
        self.assertEqual(count, 0)
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "executed")

    def test_does_not_touch_cancelled_actions(self):
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="create_project",
            arguments_json="{}",
        )
        confirmation.cancel_action(aid, "u1", "s1")
        count = confirmation.cleanup_expired()
        self.assertEqual(count, 0)


class ListPendingActionsTests(ConfirmationDBIsolation):
    """Test list_pending_actions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        # Clean any leftovers from previous test methods in this class
        import sqlite3
        conn = sqlite3.connect(str(confirmation._DB_PATH))
        confirmation._ensure_table(conn)
        conn.execute("DELETE FROM pending_actions")
        conn.commit()
        conn.close()

        self.aid1 = confirmation.create_pending_action(
            user_id="list-u1", session_id="list-s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "p1"}',
        )
        self.aid2 = confirmation.create_pending_action(
            user_id="list-u1", session_id="list-s1", role="admin",
            tool_name="delete_job",
            arguments_json='{"scene_task_name": "t1"}',
        )

    def test_lists_pending_actions_for_user_session(self):
        actions = confirmation.list_pending_actions("list-u1", "list-s1")
        self.assertEqual(len(actions), 2)
        statuses = {a["status"] for a in actions}
        self.assertEqual(statuses, {"pending"})

    def test_does_not_include_cancelled(self):
        confirmation.cancel_action(self.aid1, "list-u1", "list-s1")
        actions = confirmation.list_pending_actions("list-u1", "list-s1")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action_id"], self.aid2)

    def test_does_not_include_executed(self):
        confirmation.confirm_action(self.aid1, "list-u1", "list-s1")
        confirmation.consume_action_once(self.aid1)
        actions = confirmation.list_pending_actions("list-u1", "list-s1")
        self.assertEqual(len(actions), 1)

    def test_wrong_user_sees_empty(self):
        actions = confirmation.list_pending_actions("list-u2", "list-s1")
        self.assertEqual(len(actions), 0)

    def test_wrong_session_sees_empty(self):
        actions = confirmation.list_pending_actions("list-u1", "list-s2")
        self.assertEqual(len(actions), 0)

    def test_newest_first(self):
        actions = confirmation.list_pending_actions("list-u1", "list-s1")
        self.assertEqual(actions[0]["action_id"], self.aid2)  # newer
        self.assertEqual(actions[1]["action_id"], self.aid1)  # older


class FullLifecycleTests(ConfirmationDBIsolation):
    """Test the complete happy path: create → confirm → consume."""

    def test_full_lifecycle(self):
        # 1. Model decides to call a write tool → backend creates pending action
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="create_project",
            arguments_json='{"name": "My Project", "description": "desc"}',
        )
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "pending")
        self.assertEqual(action["tool_name"], "create_project")

        # 2. User says "确认"
        confirmation.confirm_action(aid, "u1", "s1")
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "confirmed")

        # 3. Before actually calling the tool, consume (atomic guard)
        ok = confirmation.consume_action_once(aid)
        self.assertTrue(ok)
        action = confirmation.get_pending_action(aid)
        self.assertEqual(action["status"], "executed")

        # 4. Double-execute prevented
        ok2 = confirmation.consume_action_once(aid)
        self.assertFalse(ok2)

    def test_parallel_users_isolated(self):
        """Two users creating actions → each only sees/controls their own."""
        a1 = confirmation.create_pending_action(
            user_id="alice", session_id="sa", role="admin",
            tool_name="create_project", arguments_json="{}",
        )
        a2 = confirmation.create_pending_action(
            user_id="bob", session_id="sb", role="collector",
            tool_name="claim_job", arguments_json="{}",
        )

        # Alice can confirm her own
        confirmation.confirm_action(a1, "alice", "sa")

        # Alice cannot touch Bob's
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(a2, "alice", "sa")

        # Bob cannot touch Alice's
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(a1, "bob", "sb")

        # Each only lists their own
        self.assertEqual(len(confirmation.list_pending_actions("alice", "sa")), 1)
        self.assertEqual(len(confirmation.list_pending_actions("bob", "sb")), 1)

    def test_cannot_confirm_by_just_saying_yes(self):
        """User saying '确认' should only confirm the action tied to their session."""
        aid = confirmation.create_pending_action(
            user_id="u1", session_id="s1", role="admin",
            tool_name="create_project", arguments_json="{}",
        )
        # Attacker in a different session with same user_id cannot confirm
        # (would require knowing session_id — but even if they guess user_id match...)
        # Actually if same user different session, still rejected:
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.confirm_action(aid, "u1", "s2")


if __name__ == "__main__":
    unittest.main()

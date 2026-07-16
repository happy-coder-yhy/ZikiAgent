"""Run persistence tests — no real Zata platform access."""

import unittest
import os
import sys
import json

# Ensure project root and ziki_agent on path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ziki_agent import runs


class RunPersistenceTests(unittest.TestCase):
    """Test agent_runs CRUD operations."""

    @classmethod
    def setUpClass(cls):
        # Use an in-memory / temp DB to avoid polluting the real one
        cls._orig_db = runs._DB_PATH
        import tempfile
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        runs._DB_PATH = type(runs._DB_PATH)(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        runs._DB_PATH = cls._orig_db
        os.unlink(cls._tmp.name)

    def test_create_run_returns_run_id_and_status_running(self):
        rid = runs.create_run("s1", "hello", user_id="u1", role="admin")
        self.assertTrue(len(rid) > 0)
        data = runs.get_run(rid)
        self.assertEqual(data["session_id"], "s1")
        self.assertEqual(data["user_message"], "hello")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["role"], "admin")

    def test_complete_run_sets_answer_and_status(self):
        rid = runs.create_run("s2", "test", user_id="u1")
        runs.complete_run(rid, "answer 42")
        data = runs.get_run(rid)
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["answer"], "answer 42")
        self.assertIsNotNone(data["finished_at"])
        self.assertIsNotNone(data["duration_ms"])

    def test_fail_run_sets_error_code_without_exception_text(self):
        rid = runs.create_run("s3", "test")
        runs.fail_run(rid, "agent_execution_failed")
        data = runs.get_run(rid)
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["error_code"], "agent_execution_failed")
        self.assertIsNone(data["answer"])

    def test_multiple_runs_in_same_session(self):
        r1 = runs.create_run("s4", "msg1", user_id="u1")
        r2 = runs.create_run("s4", "msg2", user_id="u1")
        self.assertNotEqual(r1, r2)
        sessions = runs.list_runs_by_session("s4")
        self.assertEqual(len(sessions), 2)

    def test_consecutive_requests_have_different_run_ids(self):
        r1 = runs.create_run("s5", "first")
        r2 = runs.create_run("s5", "second")
        self.assertNotEqual(r1, r2)

    def test_no_token_or_sensitive_fields_in_db(self):
        """Verify the agent_runs table does not have sensitive columns."""
        rid = runs.create_run("s6", "safe message", user_id="u1")
        data = runs.get_run(rid)
        # Only safe fields should exist
        safe_keys = {"run_id", "session_id", "user_id", "role", "user_message",
                     "status", "answer", "error_code", "started_at",
                     "finished_at", "duration_ms", "created_at"}
        self.assertTrue(set(data.keys()).issubset(safe_keys))
        # No token / authorization / cookie fields
        for key in data:
            self.assertNotIn("token", key.lower())
            self.assertNotIn("auth", key.lower())
            self.assertNotIn("cookie", key.lower())

    def test_get_nonexistent_run_returns_none(self):
        self.assertIsNone(runs.get_run("nonexistent-id"))


if __name__ == "__main__":
    unittest.main()

"""ToolCall persistence tests — no real Zata platform access."""

import unittest
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ziki_agent import runs


class ToolCallPersistenceTests(unittest.TestCase):
    """Test agent_tool_calls CRUD operations."""

    @classmethod
    def setUpClass(cls):
        cls._orig_db = runs._DB_PATH
        import tempfile
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        runs._DB_PATH = type(runs._DB_PATH)(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        runs._DB_PATH = cls._orig_db
        os.unlink(cls._tmp.name)

    def setUp(self):
        self.run_id = runs.create_run("tc-session", "test", user_id="u1")

    def test_start_tool_call_creates_running_record(self):
        cid = runs.start_tool_call(self.run_id, "get_platform_config")
        self.assertTrue(len(cid) > 0)
        calls = runs.list_tool_calls_by_run(self.run_id)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["tool_name"], "get_platform_config")
        self.assertEqual(calls[0]["status"], "running")

    def test_complete_tool_call_sets_success(self):
        cid = runs.start_tool_call(self.run_id, "search_user")
        runs.complete_tool_call(cid)
        calls = runs.list_tool_calls_by_run(self.run_id)
        self.assertEqual(calls[0]["status"], "success")

    def test_fail_tool_call_sets_failed(self):
        cid = runs.start_tool_call(self.run_id, "get_scene")
        runs.fail_tool_call(cid, "tool_execution_failed")
        calls = runs.list_tool_calls_by_run(self.run_id)
        self.assertEqual(calls[0]["status"], "failed")
        self.assertEqual(calls[0]["error_code"], "tool_execution_failed")

    def test_deny_tool_call_sets_denied(self):
        cid = runs.deny_tool_call(self.run_id, "create_project")
        calls = runs.list_tool_calls_by_run(self.run_id)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["status"], "denied")
        self.assertEqual(calls[0]["error_code"], "tool_not_allowed_for_role")

    def test_multiple_tool_calls_per_run(self):
        runs.start_tool_call(self.run_id, "get_platform_config")
        runs.start_tool_call(self.run_id, "search_user")
        runs.start_tool_call(self.run_id, "device_summary")
        calls = runs.list_tool_calls_by_run(self.run_id)
        self.assertEqual(len(calls), 3)

    def test_tool_call_bound_to_correct_run(self):
        r2 = runs.create_run("tc-s2", "other", user_id="u1")
        c1 = runs.start_tool_call(self.run_id, "tool-a")
        c2 = runs.start_tool_call(r2, "tool-b")
        calls1 = runs.list_tool_calls_by_run(self.run_id)
        calls2 = runs.list_tool_calls_by_run(r2)
        self.assertEqual(len(calls1), 1)
        self.assertEqual(calls2[0]["tool_name"], "tool-b")

    def test_no_token_or_raw_response_saved(self):
        cid = runs.start_tool_call(self.run_id, "search_user")
        runs.complete_tool_call(cid)
        data = runs.list_tool_calls_by_run(self.run_id)[0]
        safe_keys = {"tool_call_id", "run_id", "tool_name", "status",
                     "error_code", "started_at", "finished_at",
                     "duration_ms", "created_at"}
        self.assertTrue(set(data.keys()).issubset(safe_keys))
        for key in data:
            self.assertNotIn("token", key.lower())
            self.assertNotIn("auth", key.lower())
            self.assertNotIn("raw", key.lower())

    def test_consecutive_requests_do_not_mix_run_ids(self):
        r2 = runs.create_run("tc-s3", "second request", user_id="u1")
        c1 = runs.start_tool_call(self.run_id, "tool-on-r1")
        c2 = runs.start_tool_call(r2, "tool-on-r2")
        # Verify each run only has its own tool call
        r1_calls = runs.list_tool_calls_by_run(self.run_id)
        r2_calls = runs.list_tool_calls_by_run(r2)
        self.assertEqual([c["tool_name"] for c in r1_calls], ["tool-on-r1"])
        self.assertEqual([c["tool_name"] for c in r2_calls], ["tool-on-r2"])


class ToolCallExtractionTests(unittest.TestCase):
    """Test extracting tool calls from Hermes messages."""

    def test_extracts_tool_calls_from_assistant_and_tool_messages(self):
        messages = [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_platform_config", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": '{"projects": []}',
            },
            {"role": "assistant", "content": "Here are your projects."},
        ]
        result = runs.extract_tool_calls_from_messages(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["tool_name"], "get_platform_config")
        self.assertEqual(result[0]["status"], "success")

    def test_detects_failed_tool_call(self):
        messages = [
            {"role": "user", "content": "do something"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_err",
                        "type": "function",
                        "function": {"name": "create_project", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_err",
                "content": "Error: permission denied",
            },
        ]
        result = runs.extract_tool_calls_from_messages(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "failed")
        self.assertEqual(result[0]["error_code"], "tool_returned_error")

    def test_multiple_tool_calls_in_one_message(self):
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "c1", "type": "function",
                     "function": {"name": "get_platform_config", "arguments": "{}"}},
                    {"id": "c2", "type": "function",
                     "function": {"name": "search_user", "arguments": '{"name":"test"}'}},
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "ok"},
            {"role": "tool", "tool_call_id": "c2", "content": "ok"},
        ]
        result = runs.extract_tool_calls_from_messages(messages)
        self.assertEqual(len(result), 2)
        names = {tc["tool_name"] for tc in result}
        self.assertEqual(names, {"get_platform_config", "search_user"})

    def test_no_tool_calls_returns_empty(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = runs.extract_tool_calls_from_messages(messages)
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()

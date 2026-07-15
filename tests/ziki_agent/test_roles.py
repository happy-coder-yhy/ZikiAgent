"""Role allowlist tests — no real Zata platform access."""

import unittest
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from ziki_agent import roles


class RoleValidationTests(unittest.TestCase):
    """Test role validation and allowlist resolution."""

    def test_admin_role_is_valid(self):
        self.assertEqual(roles.validate_role("admin"), "admin")

    def test_collector_role_is_valid(self):
        self.assertEqual(roles.validate_role("collector"), "collector")

    def test_unknown_role_raises_value_error(self):
        with self.assertRaises(ValueError):
            roles.validate_role("hacker")

    def test_empty_role_raises_value_error(self):
        with self.assertRaises(ValueError):
            roles.validate_role("")

    def test_admin_role_case_insensitive_normalized(self):
        self.assertEqual(roles.validate_role("ADMIN"), "admin")
        self.assertEqual(roles.validate_role("Admin"), "admin")

    def test_whitespace_trimmed(self):
        self.assertEqual(roles.validate_role("  admin  "), "admin")


class AdminAllowlistTests(unittest.TestCase):
    """Test admin tool allowlist contains expected tools."""

    def test_admin_allowlist_has_13_tools(self):
        allowlist = roles.get_allowlist_for_role("admin")
        self.assertEqual(len(allowlist), 13)

    def test_admin_allows_readonly_tools(self):
        allowlist = roles.get_allowlist_for_role("admin")
        self.assertIn("get_platform_config", allowlist)
        self.assertIn("get_scene", allowlist)
        self.assertIn("get_task_purpose", allowlist)
        self.assertIn("search_user", allowlist)
        self.assertIn("get_projects", allowlist)
        self.assertIn("get_scene_task", allowlist)
        self.assertIn("task_summary", allowlist)
        self.assertIn("task_detail", allowlist)
        self.assertIn("job_summary", allowlist)
        self.assertIn("job_detail", allowlist)
        self.assertIn("task_job_details", allowlist)
        self.assertIn("device_summary", allowlist)
        self.assertIn("device_detail", allowlist)

    def test_admin_denies_write_tools(self):
        allowlist = roles.get_allowlist_for_role("admin")
        self.assertNotIn("create_scene_task", allowlist)
        self.assertNotIn("update_scene_task", allowlist)
        self.assertNotIn("publish_scene_task", allowlist)
        self.assertNotIn("create_project", allowlist)
        self.assertNotIn("create_job", allowlist)
        self.assertNotIn("update_job", allowlist)
        self.assertNotIn("delete_job", allowlist)
        self.assertNotIn("bind_collector_or_job", allowlist)
        self.assertNotIn("change_bind", allowlist)

    def test_admin_denies_collector_tools(self):
        allowlist = roles.get_allowlist_for_role("admin")
        self.assertNotIn("query_task_job", allowlist)
        self.assertNotIn("claim_job", allowlist)
        self.assertNotIn("query_my_device", allowlist)
        self.assertNotIn("query_device_binding", allowlist)
        self.assertNotIn("bind_job_to_device", allowlist)
        self.assertNotIn("bind_self_to_device", allowlist)


class CollectorAllowlistTests(unittest.TestCase):
    """Test collector tool allowlist contains expected tools."""

    def test_collector_allowlist_has_3_tools(self):
        allowlist = roles.get_allowlist_for_role("collector")
        self.assertEqual(len(allowlist), 3)

    def test_collector_allows_readonly_tools(self):
        allowlist = roles.get_allowlist_for_role("collector")
        self.assertIn("query_task_job", allowlist)
        self.assertIn("query_my_device", allowlist)
        self.assertIn("query_device_binding", allowlist)

    def test_collector_denies_admin_tools(self):
        allowlist = roles.get_allowlist_for_role("collector")
        self.assertNotIn("get_platform_config", allowlist)
        self.assertNotIn("search_user", allowlist)
        self.assertNotIn("device_summary", allowlist)
        self.assertNotIn("create_scene_task", allowlist)

    def test_collector_denies_write_tools(self):
        allowlist = roles.get_allowlist_for_role("collector")
        self.assertNotIn("claim_job", allowlist)
        self.assertNotIn("bind_job_to_device", allowlist)
        self.assertNotIn("bind_self_to_device", allowlist)


class AllToolsIntegrityTests(unittest.TestCase):
    """Verify all 28 legacy tools are still tracked."""

    def test_all_28_tools_present(self):
        self.assertEqual(len(roles.ALL_28_TOOLS), 28)

    def test_every_allowlist_tool_is_in_all28(self):
        for tool in roles.ADMIN_READONLY_TOOLS | roles.COLLECTOR_READONLY_TOOLS:
            self.assertIn(tool, roles.ALL_28_TOOLS,
                          f"{tool} should be in ALL_28_TOOLS")


if __name__ == "__main__":
    unittest.main()

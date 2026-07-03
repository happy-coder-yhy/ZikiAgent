"""Tests for collection work preflight verification."""

import json
from pathlib import Path
import unittest

from ApiCaller.modules.verifier import (
    REQUIRED_FIELD_PROFILES,
    verify_collection_work,
    verify_instruction_task_creation,
    verify_jobs_creation,
    verify_project_creation,
    verify_scene_task_creation,
    verify_strict_task_creation,
    verify_strict_task_from_template_creation,
)


class CollectionWorkVerifierTest(unittest.TestCase):
    """Verify planned collection work against aaaaaa platform snapshot."""

    def test_reports_project_conflict_and_all_missing_task_configuration(self):
        snapshot = {
            "projects": [{"id": 1, "name": "_zac_test_project"}],
            "labels": [{"id": 10, "categoryCode": "scene", "name": "收银区"}],
            "device_types": [{"id": 20, "name": "机械臂"}],
            "object_categories": [{"id": 30, "name": "水果"}],
            "object_items": [{"id": 40, "name": "苹果"}],
        }

        result = verify_collection_work(
            planned_project={"name": "_zac_test_project"},
            planned_task={
                "title": "_zac_test_task",
                "sceneId": 999,
                "deviceTypeId": 998,
                "objectBindings": [
                    {
                        "placeholder": "商品",
                        "objectCategoryId": 997,
                        "objectItemIds": [996],
                    }
                ],
            },
            planned_jobs=[],
            platform_snapshot=snapshot,
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["scope"], item["field"], item["reason"]) for item in result.conflicts],
            [("project", "name", "conflicting")],
        )
        self.assertEqual(
            [(item["scope"], item["field"], item["expected"], item["reason"]) for item in result.configuration_gaps],
            [
                ("task", "initialState", "non-empty initialState", "missing"),
                ("task", "actionSteps", "non-empty actionSteps", "missing"),
                ("task", "sceneId", 999, "missing"),
                ("task", "deviceTypeId", 998, "missing"),
                ("task", "objectBindings[].objectCategoryId", 997, "missing"),
                ("task", "objectBindings[].objectItemIds", 996, "missing"),
            ],
        )
        self.assertEqual(result.resolved, {})

    def test_allows_valid_plan_and_returns_resolved_ids(self):
        snapshot = {
            "projects": [],
            "labels": [{"id": 10, "categoryCode": "scene", "name": "收银区"}],
            "device_types": [{"id": 20, "name": "机械臂"}],
            "object_categories": [{"id": 30, "name": "水果"}],
            "object_items": [{"id": 40, "name": "苹果"}],
        }

        result = verify_collection_work(
            planned_project={"name": "_zac_test_project"},
            planned_task={
                "title": "_zac_test_task",
                "sceneId": 10,
                "deviceTypeId": 20,
                "initialState": "商品放在桌面",
                "actionSteps": [{"actionText": "移动商品", "stepOrder": 1}],
                "objectBindings": [
                    {
                        "placeholder": "商品",
                        "objectCategoryId": 30,
                        "objectItemIds": [40],
                    }
                ],
            },
            planned_jobs=[{"requiredRepeat": 1}],
            platform_snapshot=snapshot,
        )

        self.assertTrue(result.can_create)
        self.assertEqual(result.configuration_gaps, [])
        self.assertEqual(result.conflicts, [])
        self.assertEqual(
            result.resolved,
            {
                "project.name": "_zac_test_project",
                "sceneId": 10,
                "deviceTypeId": 20,
                "objectBindings[].objectCategoryId": 30,
                "objectBindings[].objectItemIds": 40,
            },
        )

    def test_reports_missing_required_task_and_job_fields(self):
        result = verify_collection_work(
            planned_project={"name": "_zac_test_project"},
            planned_task={},
            planned_jobs=[{}],
            platform_snapshot={"projects": []},
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["scope"], item["field"], item["reason"]) for item in result.configuration_gaps],
            [
                ("task", "sceneId", "missing"),
                ("task", "title", "missing"),
                ("job", "jobs[0].requiredRepeat", "missing"),
            ],
        )

    def test_project_creation_can_be_verified_without_task_or_jobs(self):
        result = verify_project_creation(
            planned_project={"name": "_zac_test_project"},
            platform_snapshot={"projects": [{"id": 1, "name": "_zac_test_project"}]},
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["reason"], item["rule_type"]) for item in result.conflicts],
            [("name", "conflicting", "business_profile")],
        )

    def test_scene_task_creation_uses_lightweight_required_profile(self):
        result = verify_scene_task_creation(
            planned_task={"projectId": 7, "sceneId": 10, "title": "_zac_test_scene"},
            platform_snapshot={"labels": [{"id": 10, "categoryCode": "scene"}]},
        )

        self.assertTrue(result.can_create)
        self.assertEqual(result.configuration_gaps, [])
        self.assertEqual(result.resolved["sceneId"], 10)

    def test_scene_task_creation_reports_openapi_and_business_required_fields(self):
        result = verify_scene_task_creation(planned_task={}, platform_snapshot={})

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.configuration_gaps],
            [
                ("sceneId", "openapi_required"),
                ("title", "openapi_required"),
                ("projectId", "business_profile"),
            ],
        )

    def test_instruction_task_creation_requires_prompt_instruction(self):
        result = verify_instruction_task_creation(
            planned_task={"projectId": 7, "sceneId": 10, "title": "_zac_test_instruction"},
            platform_snapshot={"labels": [{"id": 10, "categoryCode": "scene"}]},
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.configuration_gaps],
            [("promptInstruction", "business_profile")],
        )

    def test_instruction_task_creation_uses_web_video_instruction_profile(self):
        result = verify_instruction_task_creation(
            planned_task={
                "projectId": 7,
                "sceneId": 10,
                "title": "_zac_test_instruction",
                "promptInstruction": "collect cashier videos",
            },
            platform_snapshot={"labels": [{"id": 10, "categoryCode": "scene"}]},
        )

        self.assertTrue(result.can_create)
        self.assertEqual(result.configuration_gaps, [])
        self.assertEqual(result.resolved["sceneId"], 10)

    def test_strict_task_creation_requires_strict_business_profile_fields(self):
        result = verify_strict_task_creation(
            planned_task={"projectId": 7, "sceneId": 10, "title": "_zac_test_strict"},
            platform_snapshot={"labels": [{"id": 10, "categoryCode": "scene"}]},
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.configuration_gaps],
            [
                ("deviceTypeId", "business_profile"),
                ("initialState", "business_profile"),
                ("actionSteps", "business_profile"),
                ("objectBindings", "business_profile"),
            ],
        )

    def test_strict_task_from_template_checks_template_required_fields(self):
        result = verify_strict_task_from_template_creation(
            planned_task={"projectId": 7, "deviceTypeId": 20, "templateItems": [{}]},
            platform_snapshot={"device_types": [{"id": 20, "name": "机械臂"}]},
        )

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.configuration_gaps],
            [("templateItems[].templateId", "openapi_required")],
        )

    def test_jobs_creation_can_be_verified_without_project_or_task(self):
        result = verify_jobs_creation(planned_jobs=[{}])

        self.assertFalse(result.can_create)
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.configuration_gaps],
            [("jobs[0].requiredRepeat", "openapi_required")],
        )

    def test_unconfirmed_platform_rules_are_warnings_not_blocking_errors(self):
        result = verify_strict_task_creation(
            planned_task={
                "projectId": 7,
                "sceneId": 10,
                "title": "_zac_test_strict",
                "deviceTypeId": 20,
                "initialState": "object on table",
                "actionSteps": [{"actionText": "move", "stepOrder": 1}],
                "objectBindings": [{"objectCategoryId": 30, "placeholder": "object"}],
                "duration": 24,
            },
            platform_snapshot={
                "labels": [{"id": 10, "categoryCode": "scene"}],
                "device_types": [{"id": 20, "name": "机械臂"}],
                "object_categories": [{"id": 30, "name": "物品"}],
            },
        )

        self.assertTrue(result.can_create)
        self.assertEqual(result.configuration_gaps, [])
        self.assertEqual(
            [(item["field"], item["rule_type"]) for item in result.warnings],
            [("duration", "unconfirmed_platform_rule")],
        )

    def test_required_field_profiles_cover_openapi_required_schemas(self):
        openapi_path = Path(__file__).resolve().parents[1] / "docs" / "data-manager.openapi.json"
        openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
        schemas = openapi["components"]["schemas"]

        create_task_required = set(
            schemas["zata-manager_internal_dto_request.CreateTaskReq"]["required"]
        )
        create_task_from_template_required = set(
            schemas["zata-manager_internal_dto_request.CreateTaskFromTemplateReq"]["required"]
        )
        template_item_required = set(
            schemas["zata-manager_internal_dto_request.TaskTemplateItemReq"]["required"]
        )

        self.assertLessEqual(
            create_task_required,
            set(REQUIRED_FIELD_PROFILES["scene_task"]["openapi_required"]),
        )
        self.assertLessEqual(
            create_task_required,
            set(REQUIRED_FIELD_PROFILES["instruction_task"]["openapi_required"]),
        )
        self.assertLessEqual(
            create_task_required,
            set(REQUIRED_FIELD_PROFILES["strict_task"]["openapi_required"]),
        )
        self.assertLessEqual(
            create_task_from_template_required,
            set(REQUIRED_FIELD_PROFILES["strict_task_from_template"]["openapi_required"]),
        )
        self.assertLessEqual(
            template_item_required,
            set(REQUIRED_FIELD_PROFILES["task_template_item"]["openapi_required"]),
        )


if __name__ == "__main__":
    unittest.main()

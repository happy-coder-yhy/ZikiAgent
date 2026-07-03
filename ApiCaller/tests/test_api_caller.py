"""Tests for the generic and Zata-specific API callers."""

import json
import unittest
from unittest.mock import patch

from ApiCaller.modules.api_caller import (
    APICaller,
    APICallerConfig,
    CreateJobReq,
    JobItemReq,
    TaskActionStepReq,
    TaskObjectBindingReq,
    TaskTemplateItemReq,
    TaskUserReq,
    ZataAPICaller,
)


class FakeHTTPResponse:
    """Provide the minimal urllib response interface used by APICaller."""

    def __init__(self, body):
        self.status = 200
        self.headers = {}
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self._body


class APICallerTest(unittest.TestCase):
    """Verify generic requests have no Zata business behavior."""

    def test_build_url_joins_base_path_and_query(self):
        caller = APICaller(APICallerConfig(base_url="https://platform.example/"))

        url = caller.build_url("health", {"tag": ["aaaaaa", "b"], "skip": None})

        self.assertEqual(url, "https://platform.example/health?tag=a&tag=b")

    @patch("modules.api_caller.request.urlopen")
    def test_base_request_does_not_add_authorization(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = APICaller(APICallerConfig(base_url="https://platform.example"))

        caller.request("GET", "/health")

        sent_request = mock_urlopen.call_args.args[0]
        self.assertIsNone(sent_request.get_header("Authorization"))


class ZataAPICallerTest(unittest.TestCase):
    """Verify Zata routing and login-derived Bearer authorization."""

    @patch("modules.api_caller.request.urlopen")
    def test_login_token_is_used_for_data_manager_request(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"metadata": {"accessToken": "login-token"}}),
            FakeHTTPResponse({"metadata": {"accessToken": "refreshed-token"}}),
            FakeHTTPResponse({}),
        ]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.login("user", "password", "tenant")
        caller.login("user", "password", "tenant")
        caller.create_task(
            sceneId=1,
            title="task",
            collectMethod="web_video",
            taskCategory="scene",
            projectId=7,
        )

        login_request = mock_urlopen.call_args_list[0].args[0]
        refresh_request = mock_urlopen.call_args_list[1].args[0]
        task_request = mock_urlopen.call_args_list[2].args[0]
        self.assertEqual(login_request.full_url, "https://platform.example/api/zata-rbac/login")
        self.assertIsNone(login_request.get_header("Authorization"))
        self.assertIsNone(refresh_request.get_header("Authorization"))
        self.assertEqual(task_request.full_url, "https://platform.example/api/zata-manager/projects/7/tasks")
        self.assertEqual(task_request.get_header("Authorization"), "Bearer refreshed-token")

    @patch("modules.api_caller.request.urlopen")
    def test_users_use_rbac_service_prefix(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.list_users()

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(sent_request.full_url, "https://platform.example/api/zata-rbac/users")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer token")

    @patch("modules.api_caller.request.urlopen")
    def test_user_name_pool_uses_rbac_name_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.list_users_by_name("collector")

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://platform.example/api/zata-rbac/users/name?name=collector",
        )
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer token")

    @patch("modules.api_caller.request.urlopen")
    def test_category_label_pool_only_passes_requested_filters(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.list_labels_by_category(categoryCode="task_purpose", name="collection")

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://platform.example/api/zata-manager/labels?categoryCode=task_purpose&name=collection",
        )

    @patch("modules.api_caller.request.urlopen")
    def test_device_type_pool_uses_data_manager_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.list_device_types(name="arm", pageSize=20)

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://platform.example/api/zata-manager/device-types?name=arm&pageSize=20",
        )

    @patch("modules.api_caller.request.urlopen")
    def test_scene_labels_query_uses_label_tree_scene_category(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.list_scene_labels(parentId=3, name="sorting")

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://platform.example/api/zata-manager/labels/tree?categoryCode=scene&parentId=3&name=sorting",
        )
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer token")

    @patch("modules.api_caller.request.urlopen")
    def test_object_library_query_and_create_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}), FakeHTTPResponse({})]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.list_object_categories(name="food")
        caller.create_object_item(categoryId=10, name="cabbage")

        category_request = mock_urlopen.call_args_list[0].args[0]
        item_request = mock_urlopen.call_args_list[1].args[0]
        self.assertEqual(
            category_request.full_url,
            "https://platform.example/api/zata-manager/object-categories?name=food",
        )
        self.assertEqual(item_request.full_url, "https://platform.example/api/zata-manager/object-items")
        self.assertEqual(json.loads(item_request.data.decode("utf-8")), {"categoryId": 10, "name": "cabbage"})

    @patch("modules.api_caller.request.urlopen")
    def test_scene_task_template_read_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}), FakeHTTPResponse({})]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.list_scene_task_templates(title="cashier", sceneId=1, pageNum=1, pageSize=10)
        caller.get_scene_task_template(2)

        list_request = mock_urlopen.call_args_list[0].args[0]
        detail_request = mock_urlopen.call_args_list[1].args[0]
        self.assertEqual(
            list_request.full_url,
            "https://platform.example/api/zata-manager/templates?title=cashier&sceneId=1&pageNum=1&pageSize=10",
        )
        self.assertEqual(list_request.get_method(), "GET")
        self.assertEqual(detail_request.full_url, "https://platform.example/api/zata-manager/templates/2")
        self.assertEqual(detail_request.get_method(), "GET")

    @patch("modules.api_caller.request.urlopen")
    def test_create_project_and_label_build_structured_json_body(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}), FakeHTTPResponse({})]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.create_project(name="collection")
        caller.create_label(categoryCode="scene", name="shelf")

        project_request = mock_urlopen.call_args_list[0].args[0]
        label_request = mock_urlopen.call_args_list[1].args[0]
        self.assertEqual(project_request.full_url, "https://platform.example/api/zata-manager/projects")
        self.assertEqual(json.loads(project_request.data.decode("utf-8")), {"name": "collection"})
        self.assertEqual(label_request.full_url, "https://platform.example/api/zata-manager/labels")
        self.assertEqual(
            json.loads(label_request.data.decode("utf-8")),
            {"categoryCode": "scene", "name": "shelf"},
        )

    @patch("modules.api_caller.request.urlopen")
    def test_task_release_and_delete_routes_use_latest_admin_paths(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({}),
            FakeHTTPResponse({}),
            FakeHTTPResponse({}),
        ]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.publish_task(11)
        caller.unpublish_task(11)
        caller.delete_task(11)

        publish_request = mock_urlopen.call_args_list[0].args[0]
        unpublish_request = mock_urlopen.call_args_list[1].args[0]
        delete_request = mock_urlopen.call_args_list[2].args[0]
        self.assertEqual(
            publish_request.full_url,
            "https://platform.example/api/zata-manager/tasks/11/publish",
        )
        self.assertEqual(publish_request.get_method(), "POST")
        self.assertEqual(
            unpublish_request.full_url,
            "https://platform.example/api/zata-manager/tasks/11/unpublish",
        )
        self.assertEqual(unpublish_request.get_method(), "POST")
        self.assertEqual(
            delete_request.full_url,
            "https://platform.example/api/zata-manager/tasks/11",
        )
        self.assertEqual(delete_request.get_method(), "DELETE")
        self.assertEqual(delete_request.get_header("Authorization"), "Bearer token")

    @patch("modules.api_caller.request.urlopen")
    def test_task_update_archive_and_keep_jobs_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}) for _ in range(4)]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.update_task(taskId=12, sceneId=1, title="updated")
        caller.update_task_keep_jobs(taskId=12, sceneId=1, title="kept")
        caller.archive_task(12)
        caller.unarchive_task(12)

        update_request = mock_urlopen.call_args_list[0].args[0]
        keep_jobs_request = mock_urlopen.call_args_list[1].args[0]
        archive_request = mock_urlopen.call_args_list[2].args[0]
        unarchive_request = mock_urlopen.call_args_list[3].args[0]
        self.assertEqual(update_request.full_url, "https://platform.example/api/zata-manager/tasks/12")
        self.assertEqual(update_request.get_method(), "PUT")
        self.assertEqual(json.loads(update_request.data.decode("utf-8")), {"sceneId": 1, "title": "updated"})
        self.assertEqual(
            keep_jobs_request.full_url,
            "https://platform.example/api/zata-manager/tasks/12/keep-jobs",
        )
        self.assertEqual(keep_jobs_request.get_method(), "PUT")
        self.assertEqual(json.loads(keep_jobs_request.data.decode("utf-8")), {"sceneId": 1, "title": "kept"})
        self.assertEqual(
            archive_request.full_url,
            "https://platform.example/api/zata-manager/tasks/12/archive",
        )
        self.assertEqual(archive_request.get_method(), "POST")
        self.assertEqual(
            unarchive_request.full_url,
            "https://platform.example/api/zata-manager/tasks/12/unarchive",
        )
        self.assertEqual(unarchive_request.get_method(), "POST")

    @patch("modules.api_caller.request.urlopen")
    def test_rbac_userinfo_uses_latest_userinfo_endpoint(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse({})
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))
        caller.set_access_token("token")

        caller.userinfo()

        sent_request = mock_urlopen.call_args.args[0]
        self.assertEqual(sent_request.full_url, "https://platform.example/api/zata-rbac/userinfo")
        self.assertEqual(sent_request.get_method(), "GET")
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer token")

    @patch("modules.api_caller.request.urlopen")
    def test_project_label_and_object_update_delete_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}) for _ in range(8)]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.update_project(projectId=3, name="p")
        caller.delete_project(3)
        caller.update_label_category(categoryCode="scene", name="Scene")
        caller.delete_label_category("scene")
        caller.update_label(labelId=4, name="Shelf")
        caller.delete_label(4)
        caller.update_object_category(objectCategoryId=5, name="Food")
        caller.delete_object_category(5)

        requests = [call.args[0] for call in mock_urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://platform.example/api/zata-manager/projects/3")
        self.assertEqual(requests[0].get_method(), "PUT")
        self.assertEqual(json.loads(requests[0].data.decode("utf-8")), {"name": "p"})
        self.assertEqual(requests[1].full_url, "https://platform.example/api/zata-manager/projects/3")
        self.assertEqual(requests[1].get_method(), "DELETE")
        self.assertEqual(
            requests[2].full_url,
            "https://platform.example/api/zata-manager/label-categories/scene",
        )
        self.assertEqual(requests[2].get_method(), "PUT")
        self.assertEqual(
            requests[3].full_url,
            "https://platform.example/api/zata-manager/label-categories/scene",
        )
        self.assertEqual(requests[3].get_method(), "DELETE")
        self.assertEqual(requests[4].full_url, "https://platform.example/api/zata-manager/labels/4")
        self.assertEqual(requests[4].get_method(), "PUT")
        self.assertEqual(requests[5].full_url, "https://platform.example/api/zata-manager/labels/4")
        self.assertEqual(requests[5].get_method(), "DELETE")
        self.assertEqual(
            requests[6].full_url,
            "https://platform.example/api/zata-manager/object-categories/5",
        )
        self.assertEqual(requests[6].get_method(), "PUT")
        self.assertEqual(
            requests[7].full_url,
            "https://platform.example/api/zata-manager/object-categories/5",
        )
        self.assertEqual(requests[7].get_method(), "DELETE")

    @patch("modules.api_caller.request.urlopen")
    def test_device_object_item_and_job_admin_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}) for _ in range(11)]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.create_device_type(name="arm")
        caller.get_device_type(2)
        caller.update_device_type(deviceTypeId=2, name="arm-v2")
        caller.delete_device_type(2)
        caller.list_devices(deviceName="station")
        caller.create_device(deviceCode="A001", deviceTypeId=3, deviceName="station")
        caller.get_device_by_code("A001")
        caller.update_device(deviceId=9, deviceName="station-v2")
        caller.delete_device(9)
        caller.update_object_item(objectItemId=7, categoryId=10, name="cabbage-v2")
        caller.delete_object_item(7)

        requests = [call.args[0] for call in mock_urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://platform.example/api/zata-manager/device-types")
        self.assertEqual(requests[0].get_method(), "POST")
        self.assertEqual(requests[1].full_url, "https://platform.example/api/zata-manager/device-types/2")
        self.assertEqual(requests[1].get_method(), "GET")
        self.assertEqual(requests[2].full_url, "https://platform.example/api/zata-manager/device-types/2")
        self.assertEqual(requests[2].get_method(), "PUT")
        self.assertEqual(requests[3].full_url, "https://platform.example/api/zata-manager/device-types/2")
        self.assertEqual(requests[3].get_method(), "DELETE")
        self.assertEqual(
            requests[4].full_url,
            "https://platform.example/api/zata-manager/devices?deviceName=station",
        )
        self.assertEqual(requests[4].get_method(), "GET")
        self.assertEqual(requests[5].full_url, "https://platform.example/api/zata-manager/devices")
        self.assertEqual(
            json.loads(requests[5].data.decode("utf-8")),
            {"deviceCode": "A001", "deviceName": "station", "deviceTypeId": 3},
        )
        self.assertEqual(requests[5].get_method(), "POST")
        self.assertEqual(
            requests[6].full_url,
            "https://platform.example/api/zata-manager/devices/code/A001",
        )
        self.assertEqual(requests[6].get_method(), "GET")
        self.assertEqual(requests[7].full_url, "https://platform.example/api/zata-manager/devices/9")
        self.assertEqual(requests[7].get_method(), "PUT")
        self.assertEqual(requests[8].full_url, "https://platform.example/api/zata-manager/devices/9")
        self.assertEqual(requests[8].get_method(), "DELETE")
        self.assertEqual(requests[9].full_url, "https://platform.example/api/zata-manager/object-items/7")
        self.assertEqual(requests[9].get_method(), "PUT")
        self.assertEqual(requests[10].full_url, "https://platform.example/api/zata-manager/object-items/7")
        self.assertEqual(requests[10].get_method(), "DELETE")

    @patch("modules.api_caller.request.urlopen")
    def test_job_update_delete_and_batch_delete_routes(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}) for _ in range(3)]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.get_job(8)
        caller.update_job(jobId=8, requiredRepeat=3)
        caller.delete_jobs(ids=[8, 9])

        get_request = mock_urlopen.call_args_list[0].args[0]
        update_request = mock_urlopen.call_args_list[1].args[0]
        delete_request = mock_urlopen.call_args_list[2].args[0]
        self.assertEqual(get_request.full_url, "https://platform.example/api/zata-manager/jobs/8")
        self.assertEqual(get_request.get_method(), "GET")
        self.assertEqual(update_request.full_url, "https://platform.example/api/zata-manager/jobs/8")
        self.assertEqual(update_request.get_method(), "PUT")
        self.assertEqual(
            json.loads(update_request.data.decode("utf-8")),
            {"requiredRepeat": 3},
        )
        self.assertEqual(
            delete_request.full_url,
            "https://platform.example/api/zata-manager/jobs/batch-delete",
        )
        self.assertEqual(delete_request.get_method(), "POST")
        self.assertEqual(json.loads(delete_request.data.decode("utf-8")), {"ids": [8, 9]})

    @patch("modules.api_caller.request.urlopen")
    def test_task_and_job_nested_request_objects_build_json_body(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}), FakeHTTPResponse({})]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.create_task(
            sceneId=1,
            title="structured task",
            collectMethod="robot",
            taskCategory="strict",
            projectId=7,
            collectors=[TaskUserReq(userId="u1", userName="collector")],
            actionSteps=[
                TaskActionStepReq(
                    actionText="move object",
                    stepOrder=1,
                    atomicAbilityId=3,
                )
            ],
            objectBindings=[
                TaskObjectBindingReq(
                    objectCategoryId=13,
                    placeholder="水果",
                    objectItemIds=[20, 21],
                )
            ],
        )
        caller.create_jobs(
            taskId=9,
            jobs=[
                CreateJobReq(
                    requiredRepeat=3,
                    name="job",
                    items=[
                        JobItemReq(
                            displayName="苹果",
                            img="https://example.test/apple.png",
                            name="apple",
                            type=1,
                            value=21,
                            valueName="苹果",
                        )
                    ],
                )
            ],
        )

        task_request = mock_urlopen.call_args_list[0].args[0]
        jobs_request = mock_urlopen.call_args_list[1].args[0]
        self.assertEqual(task_request.full_url, "https://platform.example/api/zata-manager/projects/7/tasks")
        self.assertEqual(
            json.loads(task_request.data.decode("utf-8")),
            {
                "actionSteps": [
                    {
                        "actionText": "move object",
                        "atomicAbilityId": 3,
                        "stepOrder": 1,
                    }
                ],
                "collectMethod": "robot",
                "collectors": [{"userId": "u1", "userName": "collector"}],
                "objectBindings": [
                    {
                        "objectCategoryId": 13,
                        "objectItemIds": [20, 21],
                        "placeholder": "水果",
                    }
                ],
                "projectId": 7,
                "sceneId": 1,
                "taskCategory": "strict",
                "title": "structured task",
            },
        )
        self.assertEqual(jobs_request.full_url, "https://platform.example/api/zata-manager/tasks/9/jobs")
        self.assertEqual(
            json.loads(jobs_request.data.decode("utf-8")),
            {
                "jobs": [
                    {
                        "items": [
                            {
                                "displayName": "苹果",
                                "img": "https://example.test/apple.png",
                                "name": "apple",
                                "type": 1,
                                "value": 21,
                                "valueName": "苹果",
                            }
                        ],
                        "name": "job",
                        "requiredRepeat": 3,
                    }
                ]
            },
        )

    @patch("modules.api_caller.request.urlopen")
    def test_task_creation_wrappers_match_strict_instruction_scene_and_template_capabilities(self, mock_urlopen):
        mock_urlopen.side_effect = [FakeHTTPResponse({}) for _ in range(4)]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.create_strict_task(
            projectId=7,
            sceneId=1,
            title="strict task",
            deviceTypeId=3,
            initialState="object on shelf",
            actionSteps=[TaskActionStepReq(actionText="move object", stepOrder=1)],
            objectBindings=[TaskObjectBindingReq(objectCategoryId=13, placeholder="object")],
        )
        caller.create_scene_task(
            projectId=7,
            sceneId=2,
            title="scene task",
        )
        caller.create_instruction_task(
            projectId=7,
            sceneId=3,
            title="instruction task",
            promptInstruction="find cashier area",
        )
        caller.create_strict_task_from_template(
            projectId=7,
            taskPurposeId=188,
            deviceTypeId=3,
            templateItems=[
                TaskTemplateItemReq(
                    templateId=2,
                    autoCreateInstance=True,
                    jobCount=2,
                    jobPlanCollectCount=30,
                )
            ],
        )

        strict_request = mock_urlopen.call_args_list[0].args[0]
        scene_request = mock_urlopen.call_args_list[1].args[0]
        instruction_request = mock_urlopen.call_args_list[2].args[0]
        template_request = mock_urlopen.call_args_list[3].args[0]
        self.assertEqual(strict_request.full_url, "https://platform.example/api/zata-manager/projects/7/tasks")
        self.assertEqual(scene_request.full_url, "https://platform.example/api/zata-manager/projects/7/tasks")
        self.assertEqual(instruction_request.full_url, "https://platform.example/api/zata-manager/projects/7/tasks")
        self.assertEqual(
            json.loads(strict_request.data.decode("utf-8")),
            {
                "actionSteps": [{"actionText": "move object", "stepOrder": 1}],
                "collectMethod": "robot",
                "deviceTypeId": 3,
                "initialState": "object on shelf",
                "objectBindings": [{"objectCategoryId": 13, "placeholder": "object"}],
                "projectId": 7,
                "sceneId": 1,
                "taskCategory": "strict",
                "title": "strict task",
            },
        )
        self.assertEqual(
            json.loads(scene_request.data.decode("utf-8")),
            {
                "collectMethod": "web_video",
                "projectId": 7,
                "sceneId": 2,
                "taskCategory": "scene",
                "title": "scene task",
            },
        )
        self.assertEqual(
            json.loads(instruction_request.data.decode("utf-8")),
            {
                "collectMethod": "web_video",
                "projectId": 7,
                "promptInstruction": "find cashier area",
                "sceneId": 3,
                "taskCategory": "instruction",
                "title": "instruction task",
            },
        )
        self.assertEqual(
            template_request.full_url,
            "https://platform.example/api/zata-manager/projects/7/tasks/from-template",
        )
        self.assertEqual(
            json.loads(template_request.data.decode("utf-8")),
            {
                "collectMethod": "robot",
                "deviceTypeId": 3,
                "projectId": 7,
                "taskPurposeId": 188,
                "templateItems": [
                    {
                        "autoCreateInstance": True,
                        "jobCount": 2,
                        "jobPlanCollectCount": 30,
                        "templateId": 2,
                    }
                ],
            },
        )

    @patch("modules.api_caller.request.urlopen")
    def test_sync_platform_configuration_collects_reference_values(self, mock_urlopen):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"metadata": {"records": [{"id": 1, "name": "project"}]}}),
            FakeHTTPResponse({"metadata": {"records": [{"id": 2, "title": "task"}]}}),
            FakeHTTPResponse({"metadata": [{"code": "scene", "name": "场景"}]}),
            FakeHTTPResponse(
                {
                    "metadata": [
                        {
                            "id": 10,
                            "code": "kitchen",
                            "name": "厨房",
                            "children": [{"id": 11, "code": "sink", "name": "水槽"}],
                        }
                    ]
                }
            ),
            FakeHTTPResponse(
                {
                    "metadata": [
                        {
                            "id": 20,
                            "name": "物品目录",
                            "children": [{"id": 22, "name": "子目录"}],
                        }
                    ]
                }
            ),
            FakeHTTPResponse({"metadata": {"results": []}}),
            FakeHTTPResponse({"metadata": {"results": [{"id": 21, "name": "杯子"}]}}),
            FakeHTTPResponse({"metadata": {"records": [{"id": 3, "name": "机械臂"}]}}),
            FakeHTTPResponse({"metadata": {"records": [{"id": 4, "deviceName": "采集台"}]}}),
        ]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        snapshot = caller.sync_platform_configuration(pageSize=50)

        self.assertEqual(snapshot["projects"], [{"id": 1, "name": "project"}])
        self.assertEqual(snapshot["tasks"], [{"id": 2, "title": "task"}])
        self.assertEqual(snapshot["label_categories"], [{"code": "scene", "name": "场景"}])
        self.assertEqual(
            snapshot["object_categories"],
            [
                {"id": 20, "name": "物品目录", "path": None, "level": None, "parentId": None},
                {"id": 22, "name": "子目录", "path": None, "level": None, "parentId": 20},
            ],
        )
        self.assertEqual(snapshot["object_items"], [{"id": 21, "name": "杯子"}])
        self.assertEqual(snapshot["device_types"], [{"id": 3, "name": "机械臂"}])
        self.assertEqual(snapshot["devices"], [{"id": 4, "deviceName": "采集台"}])
        self.assertEqual(
            snapshot["labels"],
            [
                {"categoryCode": "scene", "id": 10, "code": "kitchen", "name": "厨房", "parentId": None},
                {"categoryCode": "scene", "id": 11, "code": "sink", "name": "水槽", "parentId": 10},
            ],
        )

        requests = [call.args[0] for call in mock_urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://platform.example/api/zata-manager/projects?pageNum=1&pageSize=50")
        self.assertEqual(requests[1].full_url, "https://platform.example/api/zata-manager/tasks?pageNum=1&pageSize=50")
        self.assertEqual(requests[2].full_url, "https://platform.example/api/zata-manager/label-categories")
        self.assertEqual(requests[3].full_url, "https://platform.example/api/zata-manager/labels/tree?categoryCode=scene")
        self.assertEqual(requests[4].full_url, "https://platform.example/api/zata-manager/object-categories")
        self.assertEqual(requests[5].full_url, "https://platform.example/api/zata-manager/object-items?categoryId=20&pageNum=1&pageSize=50")
        self.assertEqual(requests[6].full_url, "https://platform.example/api/zata-manager/object-items?categoryId=22&pageNum=1&pageSize=50")
        self.assertEqual(requests[7].full_url, "https://platform.example/api/zata-manager/device-types?pageNum=1&pageSize=50")
        self.assertEqual(requests[8].full_url, "https://platform.example/api/zata-manager/devices?pageNum=1&pageSize=50")

    @patch("modules.api_caller.time.sleep")
    @patch("modules.api_caller.request.urlopen")
    def test_sync_platform_configuration_can_throttle_real_server_requests(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            FakeHTTPResponse({"metadata": {"records": []}}),
            FakeHTTPResponse({"metadata": {"records": []}}),
            FakeHTTPResponse({"metadata": []}),
            FakeHTTPResponse({"metadata": []}),
            FakeHTTPResponse({"metadata": {"records": []}}),
            FakeHTTPResponse({"metadata": {"records": []}}),
        ]
        caller = ZataAPICaller(APICallerConfig(base_url="https://platform.example"))

        caller.sync_platform_configuration(pageSize=1, request_interval_seconds=2.2)

        self.assertEqual(mock_urlopen.call_count, 6)
        self.assertEqual(mock_sleep.call_count, 5)
        mock_sleep.assert_called_with(2.2)


if __name__ == "__main__":
    unittest.main()

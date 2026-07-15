"""MCP Server 单元测试。"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from ApiCaller.modules.api_caller import APIResponse


class MCPToolFunctionsTest(unittest.TestCase):
    """测试 MCP 工具函数的核心逻辑（绕过 FastMCP 框架直接测试）。"""

    def setUp(self):
        # 直接从 server 模块获取工具函数
        import mcp_server.server as server_mod

        self.server_mod = server_mod

        # 构建 mock caller
        self.mock_caller = MagicMock()

        # 用 mock caller 重建 app，从中提取工具函数
        app = self.server_mod.create_app(caller=self.mock_caller)

        # 通过 FastMCP 的工具管理器获取工具函数
        # FastMCP 内部将工具注册为 Tool 对象
        tool_manager = app._tool_manager
        self.tools = {}
        for tool in tool_manager._tools.values():
            self.tools[tool.name] = tool.fn

    def test_get_platform_config_success(self):
        """get_platform_config 成功返回平台配置。"""
        # Mock individual API methods
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": [{"id": 1, "name": "测试项目"}]}},
            raw_text='{"code":0,"metadata":{"records":[{"id":1,"name":"测试项目"}]}}',
        )
        self.mock_caller.list_tasks.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='{"code":0,"metadata":{"records":[]}}',
        )
        self.mock_caller.list_scene_labels.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": [{"id": 10, "name": "超市", "children": []}]},
            raw_text='{"code":0,"metadata":[{"id":10,"name":"超市","children":[]}]}',
        )
        self.mock_caller.list_device_types.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='{"code":0,"metadata":{"records":[]}}',
        )
        self.mock_caller.get_label_tree.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": [
                    {
                        "id": 139, "code": "task_stage", "name": "任务用途",
                        "children": [
                            {"id": 206, "name": "正式采集"},
                            {"id": 207, "name": "开发测试"},
                        ],
                    },
                    {
                        "id": 145, "code": "task_type", "name": "任务类型",
                        "children": [
                            {"id": 304, "name": "长程"},
                            {"id": 305, "name": "短程"},
                        ],
                    },
                ],
            },
            raw_text='{"code":0,"metadata":[...]}',
        )

        result_str = self.tools["get_platform_config"](page_size=200)
        result = json.loads(result_str)

        self.assertIn("projects", result)
        self.assertEqual(result["projects"][0]["name"], "测试项目")
        self.assertIn("scene_labels", result)
        self.assertEqual(result["scene_labels"][0]["name"], "超市")
        self.assertIn("_project_summary", result)
        self.assertIn("task_purposes", result)
        self.assertEqual(result["task_purposes"][0]["name"], "正式采集")
        self.assertEqual(result["task_purposes"][1]["name"], "开发测试")
        self.assertIn("task_type_options", result)
        self.assertEqual(result["task_type_options"][0]["name"], "长程")

    def test_get_platform_config_error(self):
        """get_platform_config 部分接口异常时返回警告而非抛出异常。"""
        self.mock_caller.list_projects.side_effect = RuntimeError("连接失败")
        self.mock_caller.list_tasks.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='{"code":0,"metadata":{"records":[]}}',
        )
        self.mock_caller.list_scene_labels.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": []},
            raw_text='{"code":0,"metadata":[]}',
        )
        self.mock_caller.list_device_types.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='{"code":0,"metadata":{"records":[]}}',
        )
        self.mock_caller.get_label_tree.side_effect = RuntimeError("任务标签树接口异常")

        result_str = self.tools["get_platform_config"]()
        result = json.loads(result_str)

        self.assertIn("projects", result)
        self.assertEqual(result["projects"], [])
        self.assertIn("_warnings", result)
        self.assertTrue(any("连接失败" in w for w in result["_warnings"]))
        self.assertTrue(any("任务标签树接口异常" in w for w in result["_warnings"]))

    def test_get_platform_config_includes_purpose_summary(self):
        """get_platform_config 返回 _purpose_summary 快捷映射。"""
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": [{"id": 1, "name": "测试项目"}]}},
            raw_text='...',
        )
        self.mock_caller.list_tasks.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='...',
        )
        self.mock_caller.list_scene_labels.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": [{"id": 10, "name": "超市", "children": []}]},
            raw_text='...',
        )
        self.mock_caller.list_device_types.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='...',
        )
        self.mock_caller.get_label_tree.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": [
                    {
                        "id": 139, "code": "task_stage", "name": "任务用途",
                        "children": [
                            {"id": 206, "name": "正式采集"},
                            {"id": 209, "name": "仿真评测"},
                        ],
                    },
                ],
            },
            raw_text='...',
        )

        result_str = self.tools["get_platform_config"]()
        result = json.loads(result_str)

        self.assertIn("_purpose_summary", result)
        self.assertEqual(result["_purpose_summary"]["仿真评测"], 209)
        self.assertEqual(result["_purpose_summary"]["正式采集"], 206)

    def test_get_task_purpose_success(self):
        """get_task_purpose 成功查到用途 ID。"""
        self.mock_caller.get_label_tree.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": [
                    {
                        "id": 139, "code": "task_stage", "name": "任务用途",
                        "children": [
                            {"id": 206, "name": "正式采集"},
                            {"id": 207, "name": "开发测试"},
                            {"id": 209, "name": "仿真评测"},
                        ],
                    },
                    {
                        "id": 145, "code": "task_type", "name": "任务类型",
                        "children": [{"id": 304, "name": "长程"}, {"id": 305, "name": "短程"}],
                    },
                ],
            },
            raw_text='...',
        )

        result_str = self.tools["get_task_purpose"](name="仿真评测")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["name"], "仿真评测")
        self.assertEqual(result["id"], 209)
        self.assertIn("summary", result)

    def test_get_task_purpose_not_found(self):
        """get_task_purpose 找不到时返回错误。"""
        self.mock_caller.get_label_tree.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": [
                    {
                        "id": 139, "code": "task_stage", "name": "任务用途",
                        "children": [{"id": 206, "name": "正式采集"}],
                    },
                ],
            },
            raw_text='...',
        )

        result_str = self.tools["get_task_purpose"](name="不存在的用途")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("不存在的用途", result["error"])
        self.assertIn("available_purposes", result)

    def test_get_task_purpose_http_error(self):
        """get_task_purpose API 异常时正确处理。"""
        self.mock_caller.get_label_tree.return_value = APIResponse(
            status_code=500, headers={},
            body={"message": "服务器错误"},
            raw_text='...',
        )

        result_str = self.tools["get_task_purpose"](name="仿真评测")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("500", result["error"])

    def test_get_task_purpose_exception(self):
        """get_task_purpose 异常时返回错误 JSON。"""
        self.mock_caller.get_label_tree.side_effect = RuntimeError("标签树接口超时")

        result_str = self.tools["get_task_purpose"](name="仿真评测")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("标签树接口超时", result["error"])

    # ------------------------------------------------------------------
    # 测试: get_scene
    # ------------------------------------------------------------------

    def _mock_scene_labels(self, tree: list):
        """Helper: mock caller.list_scene_labels to return given tree."""
        self.mock_caller.list_scene_labels.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": tree},
            raw_text="...",
        )

    def test_get_scene_main_scene_found(self):
        """get_scene 查询主场景名称返回 ID。"""
        self._mock_scene_labels([
            {"id": 180, "name": "居家", "children": [
                {"id": 181, "name": "客厅", "children": []},
                {"id": 182, "name": "整理", "children": []},
            ]},
            {"id": 190, "name": "工厂", "children": [
                {"id": 191, "name": "车间", "children": []},
            ]},
        ])

        result_str = self.tools["get_scene"](name="居家")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["name"], "居家")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["id"], 180)
        self.assertIsNone(result["matches"][0]["parentId"])
        self.assertIn("main_scenes", result)
        self.assertEqual(result["main_scenes"]["居家"], 180)
        self.assertEqual(result["main_scenes"]["工厂"], 190)

    def test_get_scene_sub_scene_found(self):
        """get_scene 查询子场景名称返回 ID 及父场景信息。"""
        self._mock_scene_labels([
            {"id": 180, "name": "居家", "children": [
                {"id": 181, "name": "客厅", "children": []},
                {"id": 182, "name": "整理", "children": []},
            ]},
        ])

        result_str = self.tools["get_scene"](name="客厅")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["name"], "客厅")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["matches"][0]["id"], 181)
        self.assertEqual(result["matches"][0]["parentId"], 180)
        self.assertEqual(result["matches"][0]["parentName"], "居家")

    def test_get_scene_ambiguous(self):
        """get_scene 同名子场景在不同主场景下全部列出。"""
        self._mock_scene_labels([
            {"id": 180, "name": "居家", "children": [
                {"id": 182, "name": "整理", "children": []},
            ]},
            {"id": 190, "name": "工厂", "children": [
                {"id": 192, "name": "整理", "children": []},
            ]},
        ])

        result_str = self.tools["get_scene"](name="整理")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["ambiguous"])
        self.assertEqual(result["matches"][0]["id"], 182)
        self.assertEqual(result["matches"][0]["parentName"], "居家")
        self.assertEqual(result["matches"][1]["id"], 192)
        self.assertEqual(result["matches"][1]["parentName"], "工厂")

    def test_get_scene_not_found(self):
        """get_scene 找不到时返回错误及可用场景列表。"""
        self._mock_scene_labels([
            {"id": 180, "name": "居家", "children": []},
            {"id": 190, "name": "工厂", "children": []},
        ])

        result_str = self.tools["get_scene"](name="不存在的场景")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("不存在的场景", result["error"])
        self.assertIn("main_scenes", result)
        self.assertEqual(result["main_scenes"]["居家"], 180)

    def test_get_scene_similar_suggestion(self):
        """get_scene 找不到时提供模糊匹配建议。"""
        self._mock_scene_labels([
            {"id": 180, "name": "居家生活", "children": []},
            {"id": 181, "name": "居家办公", "children": []},
        ])

        result_str = self.tools["get_scene"](name="居家")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("similar", result)
        self.assertIn("居家生活", result["similar"])
        self.assertIn("居家办公", result["similar"])

    def test_get_scene_http_error(self):
        """get_scene API 返回非 200 时正确处理。"""
        self.mock_caller.list_scene_labels.return_value = APIResponse(
            status_code=500, headers={},
            body={"message": "服务器错误"},
            raw_text="...",
        )

        result_str = self.tools["get_scene"](name="居家")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("500", result["error"])

    def test_get_scene_exception(self):
        """get_scene 异常时返回错误 JSON。"""
        self.mock_caller.list_scene_labels.side_effect = RuntimeError("场景标签接口超时")

        result_str = self.tools["get_scene"](name="居家")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("场景标签接口超时", result["error"])

    def test_create_scene_task_success(self):
        """create_scene_task 成功创建任务。"""
        self.mock_caller.create_scene_task.return_value = APIResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"id": 42, "title": "新任务"},
            raw_text='{"id":42,"title":"新任务"}',
        )

        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="商超收银场景采集",
            task_type="短程",
            task_purpose_id=100,
            difficulty="简单",
            device_scheme_id=200,
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["id"], 42)
        self.mock_caller.create_scene_task.assert_called_once_with(
            projectId=1,
            sceneId=5,
            title="商超收银场景采集",
            description=None,
            collectMethod="web_video",
            taskPurposeId=100,
            taskType=305,
            difficulty=1,
            deviceSchemeId=200,
            deviceTypeId=200,
            collectModeId=None,
            collectSchemeId=None,
            spaceIds=None,
            customLabelIds=None,
            recognitionEnabled=None,
            videoQuality=None,
            remark=None,
        )

    def test_create_scene_task_with_all_params(self):
        """create_scene_task 传入所有可选参数。"""
        self.mock_caller.create_scene_task.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 99},
            raw_text='{"id":99}',
        )

        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="仓库盘点采集",
            task_type="长程",
            task_purpose_id=10,
            difficulty="困难",
            device_scheme_id=300,
            device_type_id=300,
            description="库房A区",
            collect_method="robot",
            collect_mode_id=20,
            collect_scheme_id=30,
            space_ids=[100, 200],
            custom_label_ids=[50, 60],
            recognition_enabled=True,
            video_quality=1080,
        )
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.mock_caller.create_scene_task.assert_called_once_with(
            projectId=1,
            sceneId=5,
            title="仓库盘点采集",
            description="库房A区",
            collectMethod="robot",
            taskPurposeId=10,
            taskType=304,
            difficulty=3,
            deviceSchemeId=300,
            deviceTypeId=300,
            collectModeId=20,
            collectSchemeId=30,
            spaceIds=[100, 200],
            customLabelIds=[50, 60],
            recognitionEnabled=True,
            videoQuality=1080,
            remark=None,
        )

    def test_create_scene_task_api_error(self):
        """create_scene_task API 返回非 200 时正确处理。"""
        self.mock_caller.create_scene_task.return_value = APIResponse(
            status_code=400,
            headers={},
            body={"message": "参数错误"},
            raw_text='{"message":"参数错误"}',
        )

        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="测试",
            task_type="短程",
            task_purpose_id=100,
            difficulty="简单",
            device_scheme_id=200,
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)

    def test_create_scene_task_exception(self):
        """create_scene_task 异常时返回错误 JSON。"""
        self.mock_caller.create_scene_task.side_effect = RuntimeError("网络超时")

        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="测试",
            task_type="短程",
            task_purpose_id=100,
            difficulty="简单",
            device_scheme_id=200,
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("网络超时", result["error"])

    def test_create_scene_task_invalid_task_type(self):
        """create_scene_task 无效的 task_type 返回错误提示。"""
        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="测试",
            task_type="超长程",
            task_purpose_id=100,
            difficulty="简单",
            device_scheme_id=200,
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("短程", result["error"])
        self.assertIn("长程", result["error"])

    def test_create_scene_task_invalid_difficulty(self):
        """create_scene_task 无效的 difficulty 返回错误提示。"""
        result_str = self.tools["create_scene_task"](
            project_id=1,
            scene_id=5,
            title="测试",
            task_type="短程",
            task_purpose_id=100,
            difficulty="中等",
            device_scheme_id=200,
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("简单", result["error"])
        self.assertIn("普通", result["error"])
        self.assertIn("困难", result["error"])


    # ------------------------------------------------------------------
    # 测试: get_projects
    # ------------------------------------------------------------------

    def test_get_projects_success(self):
        """get_projects 成功返回项目列表。"""
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=200,
            headers={},
            body={
                "code": 0,
                "metadata": {
                    "records": [
                        {"id": 1, "name": "测试项目A", "description": "项目A描述"},
                        {"id": 2, "name": "测试项目B", "description": None},
                    ]
                },
            },
            raw_text='...',
        )

        result_str = self.tools["get_projects"]()
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["projects"][0]["name"], "测试项目A")
        self.assertEqual(result["projects"][0]["description"], "项目A描述")
        self.assertEqual(result["projects"][1]["name"], "测试项目B")

    def test_get_projects_with_name_filter(self):
        """get_projects 支持按名称筛选。"""
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"code": 0, "metadata": {"records": [{"id": 3, "name": "筛选项目"}]}},
            raw_text='...',
        )

        result_str = self.tools["get_projects"](name="筛选", page_num=1, page_size=50)
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(result["projects"][0]["name"], "筛选项目")
        self.mock_caller.list_projects.assert_called_with(
            name="筛选", pageNum=1, pageSize=50
        )

    def test_get_projects_empty(self):
        """get_projects 没有项目时返回空列表。"""
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text='...',
        )

        result_str = self.tools["get_projects"]()
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["projects"], [])

    def test_get_projects_http_error(self):
        """get_projects API 返回非 200 时正确处理。"""
        self.mock_caller.list_projects.return_value = APIResponse(
            status_code=500,
            headers={},
            body={"message": "服务器错误"},
            raw_text='...',
        )

        result_str = self.tools["get_projects"]()
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("500", result["error"])

    def test_get_projects_exception(self):
        """get_projects 异常时返回错误 JSON。"""
        self.mock_caller.list_projects.side_effect = RuntimeError("网络超时")

        result_str = self.tools["get_projects"]()
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("网络超时", result["error"])

    # ------------------------------------------------------------------
    # 测试: create_project
    # ------------------------------------------------------------------

    def test_create_project_success(self):
        """create_project 成功创建项目。"""
        self.mock_caller.create_project.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 10, "name": "新项目"},
            raw_text='...',
        )

        result_str = self.tools["create_project"](name="新项目")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["id"], 10)
        self.mock_caller.create_project.assert_called_once_with(
            name="新项目",
            description=None,
        )

    def test_create_project_with_description(self):
        """create_project 传入描述。"""
        self.mock_caller.create_project.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 11, "name": "带描述的项目"},
            raw_text='...',
        )

        result_str = self.tools["create_project"](
            name="带描述的项目",
            description="这是一个测试项目",
        )
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.mock_caller.create_project.assert_called_once_with(
            name="带描述的项目",
            description="这是一个测试项目",
        )

    def test_create_project_api_error(self):
        """create_project API 返回非 200 时正确处理。"""
        self.mock_caller.create_project.return_value = APIResponse(
            status_code=400,
            headers={},
            body={"message": "项目名称已存在"},
            raw_text='...',
        )

        result_str = self.tools["create_project"](name="重名项目")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)

    def test_create_project_exception(self):
        """create_project 异常时返回错误 JSON。"""
        self.mock_caller.create_project.side_effect = RuntimeError("创建失败")

        result_str = self.tools["create_project"](name="错误项目")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("创建失败", result["error"])

    # ------------------------------------------------------------------
    # 测试: get_scene_task
    # ------------------------------------------------------------------

    def _mock_list_tasks(self, tasks: list[dict], code: int = 0):
        """Helper: mock caller.list_tasks to return given tasks."""
        self.mock_caller.list_tasks.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"code": code, "metadata": {"records": tasks}},
            raw_text="...",
        )

    def _mock_get_task_detail(self, task: dict, status_code: int = 200):
        """Helper: mock caller.get_task to return a detailed task."""
        self.mock_caller.get_task.return_value = APIResponse(
            status_code=status_code,
            headers={},
            body={"code": 0, "metadata": task},
            raw_text="...",
        )

    def test_get_scene_task_found_exact(self):
        """get_scene_task 找到一条任务并返回完整详情。"""
        self._mock_list_tasks([
            {"id": 42, "title": "商超收银场景采集", "projectId": 1, "status": 0},
        ])
        self._mock_get_task_detail({
            "id": 42, "title": "商超收银场景采集", "projectId": 1, "sceneId": 5,
            "taskType": 305, "difficulty": 1, "status": 0, "description": "测试描述",
            "deviceTypeId": 200, "collectMethod": "web_video", "taskPurposeId": 100,
        })

        result_str = self.tools["get_scene_task"](title="商超收银", collect_method="web_video")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["task"]["id"], 42)
        self.assertEqual(result["task"]["title"], "商超收银场景采集")
        self.mock_caller.list_tasks.assert_called_once_with(
            collectMethod="web_video",
            title="商超收银", projectId=None, pageNum=1, pageSize=20
        )
        self.mock_caller.get_task.assert_called_once_with(taskId=42)

    def test_get_scene_task_multiple_found(self):
        """get_scene_task 找到多条任务时返回列表。"""
        self._mock_list_tasks([
            {"id": 1, "title": "超市A采集", "projectId": 1, "status": 0},
            {"id": 2, "title": "超市B采集", "projectId": 1, "status": 0},
        ])

        result_str = self.tools["get_scene_task"](title="超市", collect_method="web_video")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["tasks"]), 2)
        self.assertIn("请用户指定具体任务 ID", result["message"])
        # 多条时不调 get_task
        self.mock_caller.get_task.assert_not_called()

    def test_get_scene_task_not_found(self):
        """get_scene_task 没有匹配任务时返回 found: false。"""
        self._mock_list_tasks([])

        result_str = self.tools["get_scene_task"](title="不存在的任务", collect_method="web_video")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertFalse(result["found"])
        self.assertEqual(result["tasks"], [])
        self.assertIn("不存在的任务", result["message"])

    def test_get_scene_task_with_project_id(self):
        """get_scene_task 传入 project_id 缩小搜索范围。"""
        self._mock_list_tasks([
            {"id": 10, "title": "仓库盘点", "projectId": 3, "status": 0},
        ])
        self._mock_get_task_detail({
            "id": 10, "title": "仓库盘点", "projectId": 3, "sceneId": 8,
            "taskType": 304, "difficulty": 2, "status": 0,
        })

        result_str = self.tools["get_scene_task"](title="仓库盘点", collect_method="web_video", project_id=3)
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.mock_caller.list_tasks.assert_called_once_with(
            collectMethod="web_video",
            title="仓库盘点", projectId=3, pageNum=1, pageSize=20
        )

    def test_get_scene_task_http_error(self):
        """get_scene_task API 返回非 200 时正确处理。"""
        self.mock_caller.list_tasks.return_value = APIResponse(
            status_code=500,
            headers={},
            body={"message": "服务器错误"},
            raw_text="...",
        )

        result_str = self.tools["get_scene_task"](title="测试", collect_method="web_video")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("500", result["error"])

    def test_get_scene_task_exception(self):
        """get_scene_task 异常时返回错误 JSON。"""
        self.mock_caller.list_tasks.side_effect = RuntimeError("网络超时")

        result_str = self.tools["get_scene_task"](title="测试", collect_method="web_video")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("网络超时", result["error"])

    def test_get_scene_task_exact_detail_fallback(self):
        """get_scene_task 获取详情失败时回退到列表数据。"""
        self._mock_list_tasks([
            {"id": 42, "title": "商超收银", "projectId": 1, "status": 0},
        ])
        # get_task 失败
        self.mock_caller.get_task.side_effect = RuntimeError("连接断开")

        result_str = self.tools["get_scene_task"](title="商超收银", collect_method="web_video")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["task"]["id"], 42)

    # ------------------------------------------------------------------
    # 测试: update_scene_task
    # ------------------------------------------------------------------

    def _mock_get_task(self, task_id: int, status: int = 0, **overrides):
        """Helper: mock caller.get_task to return a task with given overrides."""
        default_task = {
            "id": task_id,
            "projectId": 1,
            "sceneId": 5,
            "title": "原任务标题",
            "description": "原描述",
            "taskType": 305,  # 短程
            "difficulty": 1,  # 简单
            "deviceTypeId": 200,
            "collectMethod": "web_video",
            "taskPurposeId": 100,
            "collectModeId": None,
            "collectSchemeId": None,
            "spaceIds": None,
            "customLabelIds": None,
            "recognitionEnabled": None,
            "videoQuality": None,
            "status": status,
        }
        default_task.update(overrides)
        self.mock_caller.get_task.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"code": 0, "metadata": default_task},
            raw_text="...",
        )

    def test_update_scene_task_success(self):
        """update_scene_task 成功修改单个字段。"""
        self._mock_get_task(task_id=42, status=0)
        self.mock_caller._request_data_manager.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 42, "title": "新标题"},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](task_id=42, title="新标题")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["title"], "新标题")
        self.assertEqual(result["updated_fields"], ["title"])
        # 验证 _request_data_manager 被调用时带上了 taskCategory 和正确的字段
        call_body = self.mock_caller._request_data_manager.call_args.kwargs["json_body"]
        self.assertEqual(call_body["taskId"], 42)
        self.assertEqual(call_body["title"], "新标题")
        self.assertEqual(call_body["sceneId"], 5)
        self.assertEqual(call_body["taskCategory"], "scene")

    def test_update_scene_task_multiple_fields(self):
        """update_scene_task 同时修改多个字段。"""
        self._mock_get_task(task_id=42, status=0)
        self.mock_caller._request_data_manager.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 42, "title": "新标题", "description": "新描述"},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](
            task_id=42,
            title="新标题",
            description="新描述",
            difficulty="困难",
            task_type="长程",
        )
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertIn("title", result["updated_fields"])
        self.assertIn("description", result["updated_fields"])
        call_body = self.mock_caller._request_data_manager.call_args.kwargs["json_body"]
        self.assertEqual(call_body["title"], "新标题")
        self.assertEqual(call_body["description"], "新描述")
        self.assertEqual(call_body["difficulty"], 3)  # 困难 → 3
        self.assertEqual(call_body["taskType"], 304)  # 长程 → 304
        self.assertEqual(call_body["taskCategory"], "scene")

    def test_update_scene_task_no_fields(self):
        """update_scene_task 未指定修改字段时返回错误。"""
        self._mock_get_task(task_id=42, status=0)

        result_str = self.tools["update_scene_task"](task_id=42)
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("请指定要修改的字段", result["error"])

    def test_update_scene_task_invalid_task_type(self):
        """update_scene_task 无效 task_type 时返回错误。"""
        self._mock_get_task(task_id=42, status=0)

        result_str = self.tools["update_scene_task"](
            task_id=42, title="新标题", task_type="超长程"
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("短程", result["error"])
        self.assertIn("长程", result["error"])

    def test_update_scene_task_invalid_difficulty(self):
        """update_scene_task 无效 difficulty 时返回错误。"""
        self._mock_get_task(task_id=42, status=0)

        result_str = self.tools["update_scene_task"](
            task_id=42, title="新标题", difficulty="中等"
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("简单", result["error"])
        self.assertIn("普通", result["error"])
        self.assertIn("困难", result["error"])

    def test_update_scene_task_published(self):
        """update_scene_task 已发布任务由 API 拒绝，工具如实返回错误。"""
        self._mock_get_task(task_id=42, status=1)  # 模拟已发布任务
        # 模拟 API 返回错误——已发布任务不可修改
        self.mock_caller._request_data_manager.return_value = APIResponse(
            status_code=400,
            headers={},
            body={"message": "任务已发布，无法修改"},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](task_id=42, title="新标题")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertEqual(result["status_code"], 400)

    def test_update_scene_task_not_found(self):
        """update_scene_task 任务不存在时返回错误。"""
        self.mock_caller.get_task.return_value = APIResponse(
            status_code=404,
            headers={},
            body={"message": "任务不存在"},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](task_id=999, title="新标题")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("404", result["error"])

    def test_update_scene_task_http200_with_error_code(self):
        """update_scene_task API 返回 200 但 body 中带错误码时视为失败。"""
        self._mock_get_task(task_id=42, status=0)
        # API 返回 200 但 body 包含错误码——实际修改未生效
        self.mock_caller._request_data_manager.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"code": 16842753, "message": "taskCategory不能为空", "metadata": None},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](task_id=42, title="新标题")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("taskCategory", result.get("error", ""))
        self.assertNotIn("updated_fields", result)

    def test_update_scene_task_exception(self):
        """update_scene_task 异常时返回错误 JSON。"""
        self._mock_get_task(task_id=42, status=0)
        self.mock_caller._request_data_manager.side_effect = RuntimeError("更新失败")

        result_str = self.tools["update_scene_task"](task_id=42, title="新标题")
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("更新失败", result["error"])

    def test_update_scene_task_change_project(self):
        """update_scene_task 支持修改项目归属。"""
        self._mock_get_task(task_id=42, status=0, projectId=1)  # 原项目 ID=1
        self.mock_caller._request_data_manager.return_value = APIResponse(
            status_code=200,
            headers={},
            body={"id": 42, "projectId": 5, "title": "原任务标题"},
            raw_text="...",
        )

        result_str = self.tools["update_scene_task"](
            task_id=42, project_id=5
        )
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertIn("project_id", result["updated_fields"])
        call_body = self.mock_caller._request_data_manager.call_args.kwargs["json_body"]
        self.assertEqual(call_body["projectId"], 5)
        self.assertEqual(call_body["taskCategory"], "scene")

    # ------------------------------------------------------------------
    # 测试: query_device_binding (采集员 — 查询设备绑定情况)
    # ------------------------------------------------------------------

    def _setup_collector_tools(self):
        """Helper: rebuild app with collector tools only (reuse existing mock_caller)."""
        import mcp_server.server as server_mod

        app = server_mod.create_app(caller=self.mock_caller)
        tool_manager = app._tool_manager
        collector_tools = {}
        for tool in tool_manager._tools.values():
            if tool.name in (
                "query_device_binding",
                "query_my_device",
                "bind_job_to_device",
                "bind_self_to_device",
            ):
                collector_tools[tool.name] = tool.fn
        return collector_tools

    def test_query_device_binding_by_code_with_collector_and_job(self):
        """query_device_binding 按 device_code 查询，返回采集员 id/name/displayName 和作业信息。"""
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 42, "deviceCode": "dunjia_device001",
                    "deviceName": "agentTest", "deviceTypeName": "Android",
                    "deviceBodyName": "Xiaomi 14", "category": "robot",
                    "status": 1,
                    "collectorId": "6e1465a8-1234-5678-9abc-def012345678",
                    "jobId": 136,
                },
            },
            raw_text="...",
        )
        # Strategy 1: get_user 直接返回用户详情
        self.mock_caller.get_user.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": "6e1465a8-1234-5678-9abc-def012345678",
                    "username": "zhangsan", "displayName": "张三",
                    "status": 1, "createdAt": "2025-01-15T10:30:00Z",
                },
            },
            raw_text="...",
        )
        self.mock_caller.get_job.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 136, "name": "数据采集-第一批",
                    "description": "采集首页数据",
                    "collectStatus": 2, "reviewStatus": 0, "taskId": 261,
                    "progress": {"normalCollect": 45, "normalCollectTotal": 100},
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_code="dunjia_device001")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertTrue(result["has_binding"])

        collector = result["binding"]["collector"]
        self.assertIsNotNone(collector)
        self.assertEqual(collector["id"], "6e1465a8-1234-5678-9abc-def012345678")
        self.assertEqual(collector["name"], "zhangsan")
        self.assertEqual(collector["displayName"], "张三")

        job = result["binding"]["job"]
        self.assertIsNotNone(job)
        self.assertEqual(job["id"], 136)
        self.assertEqual(job["description"], "采集首页数据")
        self.assertEqual(job["collectStatus"], 2)

    def test_query_device_binding_collector_with_userName_field(self):
        """query_device_binding 兼容 API 返回 userName（驼峰命名）字段。"""
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 1, "deviceCode": "test001", "deviceName": "testDevice",
                    "deviceTypeName": "iOS", "deviceBodyName": "iPhone 15",
                    "category": "video", "status": 0,
                    "collectorId": "user-uuid-001", "jobId": None,
                },
            },
            raw_text="...",
        )
        # Strategy 1: get_user 返回 userName（驼峰）
        self.mock_caller.get_user.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": "user-uuid-001",
                    "userName": "wangwu", "displayName": "王五",
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_code="test001")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        collector = result["binding"]["collector"]
        self.assertIsNotNone(collector)
        self.assertEqual(collector["id"], "user-uuid-001")
        self.assertEqual(collector["name"], "wangwu")
        self.assertEqual(collector["displayName"], "王五")

    def test_query_device_binding_no_collector_bound(self):
        """query_device_binding 设备未绑定采集员和作业。"""
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 99, "deviceCode": "free_device", "deviceName": "空闲设备",
                    "deviceTypeName": "Android", "deviceBodyName": "Pixel 8",
                    "category": "robot", "status": 0,
                    "collectorId": None, "jobId": None,
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_code="free_device")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertFalse(result["has_binding"])
        self.assertIsNone(result["binding"]["collector"])
        self.assertIsNone(result["binding"]["job"])

    def test_query_device_binding_collector_not_found_in_users(self):
        """query_device_binding 采集员 ID 存在但所有查找策略都失败时，仍返回 id。"""
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 50, "deviceCode": "orphan_device", "deviceName": "孤儿设备",
                    "deviceTypeName": "Android", "deviceBodyName": "Samsung S24",
                    "category": "robot", "status": 1,
                    "collectorId": "unknown-user-uuid", "jobId": 200,
                },
            },
            raw_text="...",
        )
        # Strategy 1: get_user 查不到
        self.mock_caller.get_user.return_value = APIResponse(
            status_code=404, headers={},
            body={"message": "用户不存在"},
            raw_text="...",
        )
        self.mock_caller.list_users.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "records": [
                        {"id": "other-user", "username": "other", "displayName": "其他用户"},
                    ]
                },
            },
            raw_text="...",
        )
        self.mock_caller.list_users_by_name.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"results": []}},
            raw_text="...",
        )
        self.mock_caller.userinfo.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": "different-user", "name": "current", "displayName": "当前用户",
                },
            },
            raw_text="...",
        )
        self.mock_caller.get_job.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 200, "description": "测试作业",
                    "collectStatus": 1, "reviewStatus": 1, "taskId": 10,
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_code="orphan_device")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["has_binding"])
        collector = result["binding"]["collector"]
        self.assertIsNotNone(collector)
        self.assertEqual(collector["id"], "unknown-user-uuid")
        self.assertEqual(collector["name"], "")
        self.assertEqual(collector["displayName"], "")
        self.assertIsNotNone(result["binding"]["job"])
        self.assertEqual(result["binding"]["job"]["id"], 200)

    def test_query_device_binding_by_name_search(self):
        """query_device_binding 按 device_name 模糊搜索，唯一匹配时返回详情。"""
        self.mock_caller.list_devices.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "records": [
                        {
                            "id": 10, "deviceCode": "abc123",
                            "deviceName": "MyTestDevice", "deviceTypeName": "Android",
                            "category": "robot", "status": 1,
                            "collectorId": None, "jobId": None,
                        },
                    ]
                },
            },
            raw_text="...",
        )
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 10, "deviceCode": "abc123", "deviceName": "MyTestDevice",
                    "deviceTypeName": "Android", "deviceBodyName": "OnePlus 12",
                    "category": "robot", "status": 1,
                    "collectorId": None, "jobId": None,
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_name="MyTest")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        self.assertTrue(result["found"])
        self.assertFalse(result["has_binding"])
        self.assertEqual(result["device"]["deviceCode"], "abc123")

    def test_query_device_binding_user_list_with_results_format(self):
        """query_device_binding 兼容 metadata.results 格式（list_users_by_name 返回）。"""
        self.mock_caller.get_device_by_code.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "id": 7, "deviceCode": "dev007", "deviceName": "TestDevice7",
                    "deviceTypeName": "Android", "deviceBodyName": "Xiaomi 15",
                    "category": "robot", "status": 1,
                    "collectorId": "user-777", "jobId": None,
                },
            },
            raw_text="...",
        )
        # Strategy 1: get_user 404，落入 list_users_by_name
        self.mock_caller.get_user.return_value = APIResponse(
            status_code=404, headers={},
            body={"message": "用户不存在"},
            raw_text="...",
        )
        self.mock_caller.list_users.return_value = APIResponse(
            status_code=200, headers={},
            body={"code": 0, "metadata": {"records": []}},
            raw_text="...",
        )
        self.mock_caller.list_users_by_name.return_value = APIResponse(
            status_code=200, headers={},
            body={
                "code": 0,
                "metadata": {
                    "results": [
                        {
                            "id": "user-777", "username": "testuser",
                            "displayName": "测试用户",
                            "status": 1, "createdAt": "2025-06-01T08:00:00Z",
                        },
                    ]
                },
            },
            raw_text="...",
        )

        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"](device_code="dev007")
        result = json.loads(result_str)

        self.assertTrue(result["success"])
        collector = result["binding"]["collector"]
        self.assertIsNotNone(collector)
        self.assertEqual(collector["id"], "user-777")
        self.assertEqual(collector["name"], "testuser")
        self.assertEqual(collector["displayName"], "测试用户")

    def test_query_device_binding_no_params(self):
        """query_device_binding 不传参数时返回错误。"""
        tools = self._setup_collector_tools()
        result_str = tools["query_device_binding"]()
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("device_name", result["error"])


class MCPAppCreationTest(unittest.TestCase):
    """测试 MCP 应用创建逻辑。"""

    @patch("mcp_server.server._build_caller")
    def test_create_app_auto_caller(self, mock_build):
        """create_app() 不传 caller 时自动构建。"""
        mock_caller = MagicMock()
        mock_build.return_value = mock_caller

        from mcp_server.server import create_app

        app = create_app()

        self.assertIsNotNone(app)
        mock_build.assert_called_once()

    def test_create_app_with_caller(self):
        """create_app() 接收外部 caller。"""
        from mcp_server.server import create_app

        mock_caller = MagicMock()
        app = create_app(caller=mock_caller)

        self.assertIsNotNone(app)

    @patch("mcp_server.server._MCP_AVAILABLE", False)
    def test_create_app_no_mcp_sdk(self):
        """mcp SDK 不可用时抛出 ImportError。"""
        from mcp_server.server import create_app

        with self.assertRaises(ImportError):
            create_app(caller=MagicMock())


class CallerBuildingTest(unittest.TestCase):
    """测试 _build_caller 逻辑。"""

    @patch("mcp_server.server.ZataAPICaller")
    def test_build_caller_defaults(self, mock_zata):
        """_build_caller 使用默认环境变量。"""
        from mcp_server.server import _build_caller

        caller = _build_caller()

        mock_zata.assert_called_once()
        config = mock_zata.call_args[0][0]
        self.assertEqual(config.base_url, "http://10.9.103.101:30080/")
        mock_zata.return_value.login.assert_called_once_with(
            username="admin",
            password="1qaz@WSX1",
            organization="agent",
        )

    @patch.dict(
        "os.environ",
        {
            "ZATA_BASE_URL": "http://custom.url:8080/",
            "ZATA_USERNAME": "testuser",
            "ZATA_PASSWORD": "testpass",
            "ZATA_ORGANIZATION": "testorg",
        },
        clear=True,
    )
    @patch("mcp_server.server.ZataAPICaller")
    def test_build_caller_from_env(self, mock_zata):
        """_build_caller 使用环境变量覆盖默认值。"""
        from mcp_server.server import _build_caller

        caller = _build_caller()

        config = mock_zata.call_args[0][0]
        self.assertEqual(config.base_url, "http://custom.url:8080/")
        mock_zata.return_value.login.assert_called_once_with(
            username="testuser",
            password="testpass",
            organization="testorg",
        )


if __name__ == "__main__":
    unittest.main()

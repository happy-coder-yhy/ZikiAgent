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
            deviceTypeId=200,
            collectModeId=None,
            collectSchemeId=None,
            spaceIds=None,
            customLabelIds=None,
            recognitionEnabled=None,
            videoQuality=None,
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
            deviceTypeId=300,
            collectModeId=20,
            collectSchemeId=30,
            spaceIds=[100, 200],
            customLabelIds=[50, 60],
            recognitionEnabled=True,
            videoQuality=1080,
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
            device_type_id=200,
        )
        result = json.loads(result_str)

        self.assertFalse(result["success"])
        self.assertIn("简单", result["error"])
        self.assertIn("普通", result["error"])
        self.assertIn("困难", result["error"])


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

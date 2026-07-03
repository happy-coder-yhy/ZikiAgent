"""场景采集任务创建工具 — create_scene_task。"""

from __future__ import annotations

import json
from typing import Optional


# ---------------------------------------------------------------------------
# 枚举值映射
# ---------------------------------------------------------------------------

_TASK_TYPE_MAP: dict[str, int] = {
    "短程": 305,
    "长程": 304,
}

_DIFFICULTY_MAP: dict[str, int] = {
    "简单": 1,
    "普通": 2,
    "困难": 3,
}


# ---------------------------------------------------------------------------
# 工具注册
# ---------------------------------------------------------------------------

def register_tools(mcp, caller) -> None:
    """注册 create_scene_task 工具到 MCP 应用。"""

    @mcp.tool()
    def create_scene_task(
        project_id: int,
        scene_id: int,
        title: str,
        task_type: str,
        task_purpose_id: int,
        difficulty: str,
        device_type_id: int,
        description: Optional[str] = None,
        collect_method: str = "web_video",
        collect_mode_id: Optional[int] = None,
        collect_scheme_id: Optional[int] = None,
        space_ids: Optional[list[int]] = None,
        custom_label_ids: Optional[list[int]] = None,
        recognition_enabled: Optional[bool] = None,
        video_quality: Optional[int] = None,
    ) -> str:
        """创建场景采集任务。

        在指定项目的指定场景下创建一个场景视频采集任务。
        先调用 get_platform_config 获取可用的 project_id、scene_id、device_type_id 和 task_purpose_id。
        当用户没有提供以下必填信息时，请逐一询问用户，直至全部填写完整再调用此工具：

        **必填字段说明：**
        - task_type (str): 任务类型。"短程" 或 "长程"
        - task_purpose_id (int): 任务用途ID。可通过 get_platform_config 获取可用的任务用途标签列表及其ID
        - difficulty (str): 任务难度。"简单"、"普通" 或 "困难"
        - device_type_id (int): 设备类型ID。可通过 get_platform_config 获取可用的设备类型列表及其ID

        Args:
            project_id: 项目 ID（通过 get_platform_config 获取）
            scene_id: 场景标签 ID（通过 get_platform_config 获取）
            title: 任务标题
            task_type: 任务类型 — "短程" 或 "长程"
            task_purpose_id: 任务用途ID — 通过 get_platform_config 的 task_purposes 列表获取
            difficulty: 任务难度 — "简单"、"普通" 或 "困难"
            device_type_id: 设备类型ID — 通过 get_platform_config 的 device_types 列表获取
            description: 任务描述（可选）
            collect_method: 采集方式，默认 "web_video"
            collect_mode_id: 采集模式标签 ID（可选）
            collect_scheme_id: 采集方案标签 ID（可选）
            space_ids: 空间标签 ID 列表（可选）
            custom_label_ids: 自定义标签 ID 列表（可选）
            recognition_enabled: 是否启用 AI 识别（可选）
            video_quality: 视频画质设置（可选）
        """
        # 校验并映射 task_type
        task_type_val = _TASK_TYPE_MAP.get(task_type)
        if task_type_val is None:
            return json.dumps(
                {
                    "success": False,
                    "error": f"无效的任务类型：'{task_type}'，请选择 '短程' 或 '长程'",
                },
                ensure_ascii=False,
                indent=2,
            )

        # 校验并映射 difficulty
        difficulty_val = _DIFFICULTY_MAP.get(difficulty)
        if difficulty_val is None:
            return json.dumps(
                {
                    "success": False,
                    "error": f"无效的难度：'{difficulty}'，请选择 '简单'、'普通' 或 '困难'",
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            response = caller.create_scene_task(
                projectId=project_id,
                sceneId=scene_id,
                title=title,
                description=description,
                collectMethod=collect_method,
                taskPurposeId=task_purpose_id,
                taskType=task_type_val,
                difficulty=difficulty_val,
                deviceTypeId=device_type_id,
                collectModeId=collect_mode_id,
                collectSchemeId=collect_scheme_id,
                spaceIds=space_ids,
                customLabelIds=custom_label_ids,
                recognitionEnabled=recognition_enabled,
                videoQuality=video_quality,
            )

            return json.dumps(
                {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.body,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": str(e)},
                ensure_ascii=False,
                indent=2,
            )

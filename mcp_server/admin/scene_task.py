"""场景采集任务工具 — create_scene_task, update_scene_task。"""

from __future__ import annotations

import json
from typing import Any, Optional

from ApiCaller.modules.api_caller import _build_json_body, _extract_metadata_items


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

# 反向映射（int → Chinese）
_TASK_TYPE_REVERSE: dict[int, str] = {v: k for k, v in _TASK_TYPE_MAP.items()}
_DIFFICULTY_REVERSE: dict[int, str] = {v: k for k, v in _DIFFICULTY_MAP.items()}


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _extract_task_data(resp_body: Any) -> Optional[dict[str, Any]]:
    """从 get_task 响应中提取任务数据字典。"""
    if isinstance(resp_body, dict):
        # 优先取 metadata
        if "metadata" in resp_body:
            meta = resp_body["metadata"]
            if isinstance(meta, dict):
                return meta
        # 直接返回 body 本身（可能已经是任务对象）
        return resp_body
    return None


def _map_update_task_type(task_type: str) -> int | str:
    """将中文 task_type 转为 int，无效值直接返回原字符串供报错用。"""
    val = _TASK_TYPE_MAP.get(task_type)
    return task_type if val is None else val


def _map_update_difficulty(difficulty: str) -> int | str:
    """将中文 difficulty 转为 int，无效值直接返回原字符串供报错用。"""
    val = _DIFFICULTY_MAP.get(difficulty)
    return difficulty if val is None else val


# ---------------------------------------------------------------------------
# 工具注册
# ---------------------------------------------------------------------------

def register_tools(mcp, caller) -> None:
    """注册场景任务相关工具到 MCP 应用。"""

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

    # -------------------------------------------------------------------
    # 工具: get_scene_task
    # -------------------------------------------------------------------

    @mcp.tool()
    def get_scene_task(
        title: str,
        project_id: Optional[int] = None,
        page_size: int = 20,
    ) -> str:
        """根据任务名称查询场景采集任务。

        在修改任务前先调用此工具查询任务是否存在，获取任务 ID 和当前状态。
        支持模糊搜索，返回匹配任务的完整 JSON 信息。

        Args:
            title: 任务标题（支持模糊匹配）
            project_id: 项目 ID（选填，缩小搜索范围）
            page_size: 每页数量（默认 20，最大 200）
        """
        try:
            response = caller.list_tasks(
                title=title,
                projectId=project_id,
                pageNum=1,
                pageSize=min(page_size, 200),
            )

            if response.status_code != 200:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"查询任务列表失败: HTTP {response.status_code}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 从响应中提取任务列表
            tasks = _extract_metadata_items(response.body) if response.body else []

            if not tasks:
                return json.dumps(
                    {
                        "success": True,
                        "found": False,
                        "message": f"未找到标题包含「{title}」的场景任务",
                        "tasks": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 如果只找到一条，获取其完整详情
            if len(tasks) == 1:
                task_id = tasks[0].get("id")
                if task_id is not None:
                    try:
                        detail_resp = caller.get_task(taskId=task_id)
                        if detail_resp.status_code == 200:
                            detail_body = detail_resp.body
                            # 提取完整任务数据
                            task_detail = _extract_task_data(detail_body)
                            if task_detail:
                                task_detail["_match_type"] = "exact"
                                return json.dumps(
                                    {
                                        "success": True,
                                        "found": True,
                                        "count": 1,
                                        "task": task_detail,
                                    },
                                    ensure_ascii=False,
                                    indent=2,
                                )
                    except Exception:
                        pass  # 详情获取失败时回退到列表数据

                # 拿不到详情时返回列表中的信息
                return json.dumps(
                    {
                        "success": True,
                        "found": True,
                        "count": 1,
                        "task": tasks[0],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 多条匹配：返回列表供用户选择
            return json.dumps(
                {
                    "success": True,
                    "found": True,
                    "count": len(tasks),
                    "tasks": tasks,
                    "message": f"找到 {len(tasks)} 个匹配的任务，请用户指定具体任务 ID",
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询任务异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    # -------------------------------------------------------------------
    # 工具: update_scene_task
    # -------------------------------------------------------------------

    @mcp.tool()
    def update_scene_task(
        task_id: int,
        title: Optional[str] = None,
        scene_id: Optional[int] = None,
        description: Optional[str] = None,
        task_type: Optional[str] = None,
        task_purpose_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        device_type_id: Optional[int] = None,
        project_id: Optional[int] = None,
        collect_method: Optional[str] = None,
        collect_mode_id: Optional[int] = None,
        collect_scheme_id: Optional[int] = None,
        space_ids: Optional[list[int]] = None,
        custom_label_ids: Optional[list[int]] = None,
        recognition_enabled: Optional[bool] = None,
        video_quality: Optional[int] = None,
    ) -> str:
        """修改场景任务。

        修改指定场景任务的字段值。用户没说具体改什么时先询问。
        建议先通过 get_scene_task 查询任务状态。
        仅限未发布（status=1）的任务，已发布（status=2）的任务会被 API 拒绝。

        Args:
            task_id: 任务 ID（必填）
            title: 新的任务标题（选填）
            scene_id: 新的场景标签 ID（选填）
            description: 新的任务描述（选填）
            task_type: 新的任务类型 — "短程" 或 "长程"（选填）
            task_purpose_id: 新的任务用途 ID（选填）
            difficulty: 新的难度 — "简单"、"普通" 或 "困难"（选填）
            device_type_id: 新的设备类型 ID（选填）
            project_id: 新的项目 ID（选填，修改任务所属项目）
            collect_method: 新的采集方式（选填）
            collect_mode_id: 新的采集模式标签 ID（选填）
            collect_scheme_id: 新的采集方案标签 ID（选填）
            space_ids: 新的空间标签 ID 列表（选填）
            custom_label_ids: 新的自定义标签 ID 列表（选填）
            recognition_enabled: 是否启用 AI 识别（选填）
            video_quality: 新的视频画质设置（选填）
        """
        # 检查是否至少传了一个要修改的字段
        update_fields = {
            k: v for k, v in {
                "title": title,
                "scene_id": scene_id,
                "description": description,
                "task_type": task_type,
                "task_purpose_id": task_purpose_id,
                "difficulty": difficulty,
                "device_type_id": device_type_id,
                "project_id": project_id,
                "collect_method": collect_method,
                "collect_mode_id": collect_mode_id,
                "collect_scheme_id": collect_scheme_id,
                "space_ids": space_ids,
                "custom_label_ids": custom_label_ids,
                "recognition_enabled": recognition_enabled,
                "video_quality": video_quality,
            }.items() if v is not None
        }
        if not update_fields:
            return json.dumps(
                {
                    "success": False,
                    "error": "请指定要修改的字段，如 title、description、difficulty 等",
                },
                ensure_ascii=False,
                indent=2,
            )

        # 校验 task_type 值
        task_type_val: Optional[int] = None
        if task_type is not None:
            mapped = _map_update_task_type(task_type)
            if isinstance(mapped, str):
                return json.dumps(
                    {
                        "success": False,
                        "error": f"无效的任务类型：'{task_type}'，请选择 '短程' 或 '长程'",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            task_type_val = mapped

        # 校验 difficulty 值
        difficulty_val: Optional[int] = None
        if difficulty is not None:
            mapped = _map_update_difficulty(difficulty)
            if isinstance(mapped, str):
                return json.dumps(
                    {
                        "success": False,
                        "error": f"无效的难度：'{difficulty}'，请选择 '简单'、'普通' 或 '困难'",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            difficulty_val = mapped

        # 获取当前任务数据
        try:
            get_resp = caller.get_task(taskId=task_id)
            if get_resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"获取任务详情失败: HTTP {get_resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            current = _extract_task_data(get_resp.body)
            if not current:
                return json.dumps(
                    {"success": False, "error": "无法解析任务数据"},
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"获取任务详情异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

        # 从当前数据中获取 sceneId 和 title（update API 的必填字段）
        cur_scene_id = current.get("sceneId")
        cur_title = current.get("title")

        # 合并用户提交的变更
        merged_scene_id = scene_id if scene_id is not None else cur_scene_id
        merged_title = title if title is not None else cur_title

        if merged_scene_id is None:
            return json.dumps(
                {"success": False, "error": "无法确定场景 ID，当前任务数据中缺少 sceneId"},
                ensure_ascii=False,
                indent=2,
            )
        if not merged_title:
            return json.dumps(
                {"success": False, "error": "无法确定任务标题，当前任务数据中缺少 title"},
                ensure_ascii=False,
                indent=2,
            )

        # 从当前数据提取其他字段作为 fallback
        cur_project_id = current.get("projectId")
        merged_project_id = project_id if project_id is not None else cur_project_id
        cur_collect_method = current.get("collectMethod")
        cur_purpose_id = current.get("taskPurposeId")
        cur_device_type_id = current.get("deviceTypeId")
        cur_collect_mode_id = current.get("collectModeId")
        cur_collect_scheme_id = current.get("collectSchemeId")
        cur_space_ids = current.get("spaceIds")
        cur_custom_label_ids = current.get("customLabelIds")
        cur_recognition = current.get("recognitionEnabled")
        cur_video_quality = current.get("videoQuality")

        # 当前 difficulty 可能是 int 或 str，统一处理
        cur_difficulty_raw = current.get("difficulty")
        if isinstance(cur_difficulty_raw, int):
            cur_difficulty = cur_difficulty_raw
        elif isinstance(cur_difficulty_raw, str):
            cur_difficulty = _DIFFICULTY_MAP.get(cur_difficulty_raw)
        else:
            cur_difficulty = None

        # 当前 taskType 可能是 int 或 str
        cur_task_type_raw = current.get("taskType")
        if isinstance(cur_task_type_raw, int):
            cur_task_type = cur_task_type_raw
        elif isinstance(cur_task_type_raw, str):
            cur_task_type = _TASK_TYPE_MAP.get(cur_task_type_raw)
        else:
            cur_task_type = None

        try:
            # 使用 _request_data_manager 直接构建请求体，带上 taskCategory="scene"
            # （caller.update_task_keep_jobs 没有 taskCategory 参数，会报错）
            response = caller._request_data_manager(
                method="PUT",
                path=f"/tasks/{task_id}/keep-jobs",
                json_body=_build_json_body(
                    taskCategory="scene",
                    taskId=task_id,
                    sceneId=merged_scene_id,
                    title=merged_title,
                    projectId=merged_project_id,
                    description=description if description is not None else current.get("description"),
                    collectMethod=collect_method if collect_method is not None else cur_collect_method,
                    taskPurposeId=task_purpose_id if task_purpose_id is not None else cur_purpose_id,
                    taskType=task_type_val if task_type_val is not None else cur_task_type,
                    difficulty=difficulty_val if difficulty_val is not None else cur_difficulty,
                    deviceTypeId=device_type_id if device_type_id is not None else cur_device_type_id,
                    collectModeId=collect_mode_id if collect_mode_id is not None else cur_collect_mode_id,
                    collectSchemeId=collect_scheme_id if collect_scheme_id is not None else cur_collect_scheme_id,
                    spaceIds=space_ids if space_ids is not None else cur_space_ids,
                    customLabelIds=custom_label_ids if custom_label_ids is not None else cur_custom_label_ids,
                    recognitionEnabled=recognition_enabled if recognition_enabled is not None else cur_recognition,
                    videoQuality=video_quality if video_quality is not None else cur_video_quality,
                ),
            )

            # 判断是否真的成功：status_code=200 且 body 中无错误码
            is_success = response.status_code == 200
            error_body_msg = None
            if is_success and isinstance(response.body, dict):
                body_code = response.body.get("code")
                if body_code is not None and body_code != 0:
                    is_success = False
                    error_body_msg = response.body.get("message") or str(response.body)

            result: dict[str, Any] = {
                "success": is_success,
                "status_code": response.status_code,
                "data": response.body,
            }
            if is_success:
                result["updated_fields"] = list(update_fields.keys())
            else:
                result["error"] = error_body_msg or f"API 返回错误码 {response.body.get('code')}"

            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"修改任务异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

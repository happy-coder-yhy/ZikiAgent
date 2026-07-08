"""场景任务作业工具 — create_job, update_job, delete_job。"""

from __future__ import annotations

import json
from typing import Any, Optional

from ApiCaller.modules.api_caller import (
    CreateJobReq,
    _extract_metadata_items,
)
from mcp_server.admin.scene_task import _query_scene_task


def register_tools(mcp, caller) -> None:
    """注册场景任务作业相关工具到 MCP 应用。"""

    # -------------------------------------------------------------------
    # 工具: create_job
    # -------------------------------------------------------------------

    @mcp.tool()
    def create_job(
        scene_task_name: str,
        plan_collect_count: Optional[int] = None,
        description: Optional[str] = None,
        collect_method: str = "web_video",
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        required_member: Optional[int] = None,
        job_type: Optional[int] = None,
    ) -> str:
        """在指定场景任务下创建作业（Job）。

        必须先确认场景任务存在（仅匹配 taskCategory="scene" 的任务）。
        必填字段：plan_collect_count（计划采集数）、description（描述）。
        若用户未提供必填字段，需逐一询问直至完整。

        Args:
            scene_task_name: 场景任务名称（必填）
            plan_collect_count: 计划采集数（必填，对应 requiredRepeat）
            description: 作业描述（必填）
            collect_method: 采集方式，默认 "web_video"
            project_id: 项目 ID（选填，用于缩小场景任务搜索范围）
            name: 作业名称（选填）
            required_member: 需求人数（选填）
            job_type: 作业类型（选填）
        """
        # 校验必填字段：计划采集数
        if plan_collect_count is None:
            return json.dumps(
                {
                    "success": False,
                    "error": "请提供该作业的计划采集数（plan_collect_count）。",
                },
                ensure_ascii=False,
                indent=2,
            )

        # 校验必填字段：描述
        if not description or not description.strip():
            return json.dumps(
                {
                    "success": False,
                    "error": "请提供该作业的描述（description）。",
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            # 1. 查询场景任务（直接复用 get_scene_task）
            result = _query_scene_task(
                caller, scene_task_name.strip(), collect_method, project_id,
            )
            if not result.get("success") or not result.get("found"):
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"当前不存在该场景任务「{scene_task_name}」，"
                            f"暂不支持创建作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # 仅处理唯一匹配，多条匹配要求用户确认
            if result.get("count", 0) > 1:
                tasks = result.get("tasks", [])
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"找到 {len(tasks)} 个名称匹配的场景任务，"
                            f"请确认具体是哪一个。"
                        ),
                        "candidates": [
                            {"id": t.get("id"), "title": t.get("title"),
                             "status": t.get("status")}
                            for t in tasks
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task = result.get("task", {})
            # 确认是场景任务类型
            if task.get("taskCategory") != "scene":
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"「{scene_task_name}」不是场景任务（taskCategory="
                            f"{task.get('taskCategory')}），暂不支持创建作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task_id = task.get("id")

            # 2. 创建作业
            job_req = CreateJobReq(
                requiredRepeat=plan_collect_count,
                description=description.strip(),
                name=name,
                requiredMember=required_member,
                type=job_type,
            )

            response = caller.create_jobs(taskId=task_id, jobs=[job_req])

            is_success = response.status_code == 200
            error_msg = None
            if is_success and isinstance(response.body, dict):
                body_code = response.body.get("code")
                if body_code is not None and body_code != 0:
                    is_success = False
                    error_msg = response.body.get("message") or str(response.body)

            result_data: dict[str, Any] = {
                "success": is_success,
                "status_code": response.status_code,
                "data": response.body,
                "task_id": task_id,
                "task_name": task.get("title"),
            }
            if error_msg:
                result_data["error"] = error_msg

            return json.dumps(result_data, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"创建作业异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    # -------------------------------------------------------------------
    # 工具: update_job
    # -------------------------------------------------------------------

    @mcp.tool()
    def update_job(
        scene_task_name: str,
        job_description: str,
        plan_collect_count: Optional[int] = None,
        new_description: Optional[str] = None,
        collect_method: str = "web_video",
        project_id: Optional[int] = None,
        name: Optional[str] = None,
        required_member: Optional[int] = None,
        job_type: Optional[int] = None,
    ) -> str:
        """修改指定场景任务下的已有作业（Job）。

        根据作业描述（job_description）查找作业，定位到唯一作业后执行修改。
        若找到多个相同描述的作业，返回候选列表要求用户确认。

        Args:
            scene_task_name: 场景任务名称（必填）
            job_description: 要修改的作业描述，用于查找作业（必填）
            plan_collect_count: 新的计划采集数（选填，对应 requiredRepeat）
            new_description: 新的作业描述（选填）
            collect_method: 采集方式，默认 "web_video"
            project_id: 项目 ID（选填，用于缩小场景任务搜索范围）
            name: 新的作业名称（选填）
            required_member: 新的需求人数（选填）
            job_type: 新的作业类型（选填）
        """
        # 检查是否至少传了一个要修改的字段
        update_fields = {
            k: v
            for k, v in {
                "plan_collect_count": plan_collect_count,
                "description": new_description,
                "name": name,
                "required_member": required_member,
                "job_type": job_type,
            }.items()
            if v is not None
        }
        if not update_fields:
            return json.dumps(
                {
                    "success": False,
                    "error": (
                        "请指定要修改的字段，如 plan_collect_count（计划采集数）、"
                        "new_description（描述）等。"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            # 1. 查询场景任务（直接复用 get_scene_task）
            result = _query_scene_task(
                caller, scene_task_name.strip(), collect_method, project_id,
            )
            if not result.get("success") or not result.get("found"):
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"当前不存在该场景任务「{scene_task_name}」，"
                            f"暂不支持编辑作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if result.get("count", 0) > 1:
                tasks = result.get("tasks", [])
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"找到 {len(tasks)} 个名称匹配的场景任务，"
                            f"请确认具体是哪一个。"
                        ),
                        "candidates": [
                            {"id": t.get("id"), "title": t.get("title"),
                             "status": t.get("status")}
                            for t in tasks
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task = result.get("task", {})
            if task.get("taskCategory") != "scene":
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"「{scene_task_name}」不是场景任务（taskCategory="
                            f"{task.get('taskCategory')}），暂不支持编辑作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task_id = task.get("id")

            # 2. 根据描述查找作业（复用 caller.list_jobs）
            list_resp = caller.list_jobs(taskId=task_id, pageNum=1, pageSize=500)
            if list_resp.status_code != 200:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"查询作业列表失败: HTTP {list_resp.status_code}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            all_jobs = (
                _extract_metadata_items(list_resp.body) if list_resp.body else []
            )
            matched_jobs = [
                j for j in all_jobs
                if isinstance(j, dict)
                and j.get("description") == job_description.strip()
            ]

            if not matched_jobs:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"未找到描述为「{job_description}」的作业，"
                            f"请确认作业描述。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if len(matched_jobs) > 1:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"找到 {len(matched_jobs)} 个描述相同的作业，"
                            f"请确认需要修改哪一个。"
                        ),
                        "candidates": [
                            {
                                "id": j.get("id"),
                                "title": j.get("title"),
                                "description": j.get("description"),
                                "createdAt": j.get("createdAt"),
                                "requiredRepeat": j.get("requiredRepeat"),
                            }
                            for j in matched_jobs
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            job = matched_jobs[0]
            job_id = job.get("id")

            # 3. 执行修改
            # update_job API 要求 requiredRepeat 为必填
            new_required_repeat = (
                plan_collect_count
                if plan_collect_count is not None
                else job.get("requiredRepeat")
            )
            if new_required_repeat is None:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            "无法确定计划采集数，当前作业数据中缺少 requiredRepeat。"
                            "请提供 plan_collect_count。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            response = caller.update_job(
                jobId=job_id,
                requiredRepeat=new_required_repeat,
                description=(
                    new_description if new_description is not None
                    else job.get("description")
                ),
                name=name if name is not None else job.get("name"),
                requiredMember=(
                    required_member if required_member is not None
                    else job.get("requiredMember")
                ),
                type=job_type if job_type is not None else job.get("type"),
            )

            is_success = response.status_code == 200
            error_msg = None
            if is_success and isinstance(response.body, dict):
                body_code = response.body.get("code")
                if body_code is not None and body_code != 0:
                    is_success = False
                    error_msg = response.body.get("message") or str(response.body)

            result_data: dict[str, Any] = {
                "success": is_success,
                "status_code": response.status_code,
                "data": response.body,
                "job_id": job_id,
                "task_id": task_id,
                "task_name": task.get("title"),
            }
            if is_success:
                result_data["updated_fields"] = list(update_fields.keys())
            else:
                result_data["error"] = error_msg or "API 返回错误"

            return json.dumps(result_data, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"修改作业异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    # -------------------------------------------------------------------
    # 工具: delete_job
    # -------------------------------------------------------------------

    @mcp.tool()
    def delete_job(
        scene_task_name: str,
        job_description: str,
        collect_method: str = "web_video",
        project_id: Optional[int] = None,
    ) -> str:
        """删除指定场景任务下的已有作业（Job）。

        根据作业描述（job_description）查找作业，定位到唯一作业后执行删除。
        若找到多个相同描述的作业，返回候选列表要求用户确认。

        Args:
            scene_task_name: 场景任务名称（必填）
            job_description: 要删除的作业描述，用于查找作业（必填）
            collect_method: 采集方式，默认 "web_video"
            project_id: 项目 ID（选填，用于缩小场景任务搜索范围）
        """
        try:
            # 1. 查询场景任务（直接复用 get_scene_task）
            result = _query_scene_task(
                caller, scene_task_name.strip(), collect_method, project_id,
            )
            if not result.get("success") or not result.get("found"):
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"当前不存在该场景任务「{scene_task_name}」，"
                            f"暂不支持删除作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if result.get("count", 0) > 1:
                tasks = result.get("tasks", [])
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"找到 {len(tasks)} 个名称匹配的场景任务，"
                            f"请确认具体是哪一个。"
                        ),
                        "candidates": [
                            {"id": t.get("id"), "title": t.get("title"),
                             "status": t.get("status")}
                            for t in tasks
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task = result.get("task", {})
            if task.get("taskCategory") != "scene":
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"「{scene_task_name}」不是场景任务（taskCategory="
                            f"{task.get('taskCategory')}），暂不支持删除作业。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            task_id = task.get("id")

            # 2. 根据描述查找作业（复用 caller.list_jobs）
            list_resp = caller.list_jobs(taskId=task_id, pageNum=1, pageSize=500)
            if list_resp.status_code != 200:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"查询作业列表失败: HTTP {list_resp.status_code}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            all_jobs = (
                _extract_metadata_items(list_resp.body) if list_resp.body else []
            )
            matched_jobs = [
                j for j in all_jobs
                if isinstance(j, dict)
                and j.get("description") == job_description.strip()
            ]

            if not matched_jobs:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"未找到描述为「{job_description}」的作业，"
                            f"请确认作业描述。"
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if len(matched_jobs) > 1:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"找到 {len(matched_jobs)} 个描述相同的作业，"
                            f"请确认需要删除哪一个。"
                        ),
                        "candidates": [
                            {
                                "id": j.get("id"),
                                "title": j.get("title"),
                                "description": j.get("description"),
                                "createdAt": j.get("createdAt"),
                                "requiredRepeat": j.get("requiredRepeat"),
                            }
                            for j in matched_jobs
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            job = matched_jobs[0]
            job_id = job.get("id")

            # 3. 执行删除
            response = caller.delete_jobs(ids=[job_id])

            is_success = response.status_code == 200
            error_msg = None
            if is_success and isinstance(response.body, dict):
                body_code = response.body.get("code")
                if body_code is not None and body_code != 0:
                    is_success = False
                    error_msg = response.body.get("message") or str(response.body)

            result_data: dict[str, Any] = {
                "success": is_success,
                "status_code": response.status_code,
                "data": response.body,
                "deleted_job_id": job_id,
                "task_id": task_id,
                "task_name": task.get("title"),
            }
            if error_msg:
                result_data["error"] = error_msg

            return json.dumps(result_data, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"删除作业异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

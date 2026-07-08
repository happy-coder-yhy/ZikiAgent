"""任务作业概览工具 — task_summary（按 taskCategory 分类统计）。"""

from __future__ import annotations

import json
from typing import Any, Optional

from ApiCaller.modules.api_caller import _extract_metadata_items


# ---------------------------------------------------------------------------
# taskCategory 枚举值
# ---------------------------------------------------------------------------
_TASK_CATEGORY_SCENE = "scene"  # 场景任务
_TASK_CATEGORY_INSTRUCTION = "instruction"  # 指令任务
_TASK_CATEGORY_STRICT = "strict"  # 严格任务

# 已发布状态值（各分类通用）
_STATUS_PUBLISHED = 2


def register_tools(mcp, caller) -> None:
    """注册任务相关工具到 MCP 应用。"""

    def _query_tasks(
        caller, collect_method: str, title: Optional[str] = None,
        page_num: int = 1, page_size: int = 100,
    ) -> Optional[list[dict]]:
        """查询单个采集方式的任务列表，失败返回 None。"""
        try:
            resp = caller.list_tasks(
                collectMethod=collect_method,
                title=title,
                pageNum=page_num,
                pageSize=page_size,
            )
            if resp.status_code != 200:
                return None
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            if body_dict.get("code") is not None and body_dict.get("code") != 0:
                return None
            tasks = _extract_metadata_items(resp.body)
            return [t for t in tasks if isinstance(t, dict)]
        except Exception:
            return None

    @mcp.tool()
    def task_summary(
        collect_method: Optional[str] = None,
        title: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 100,
    ) -> str:
        """查询平台任务概要——返回任务总数及分类（场景/指令/严格）统计。

        ⚠️ 平台接口按采集方式隔离数据。不传 collect_method 时自动查询所有采集方式并聚合。
        若只想看某类采集方式的任务，可传入 collect_method 过滤。
        常见取值：可在 get_platform_config 的 device_schemes 中查看，通常有
        "web_video"（视频采集）、"robot"（真机采集）等。

        Args:
            collect_method: **可选**。采集方式，如 "web_video"、"robot"。不传则查询全部
            title: 按任务标题模糊筛选（可选）
            page_num: 页码，默认 1
            page_size: 每页数量，默认 100

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - total: 服务器返回的任务总数
            - scene_num: 场景任务数
            - instruction_num: 指令任务数
            - strict_num: 严格任务数
            - issued: 已发布任务数（status == 2）
            - tasks: 任务概要列表
        """

        try:
            # 确定要查询的采集方式列表
            if collect_method is not None:
                methods_to_query = [collect_method]
            else:
                # 自动尝试所有已知采集方式
                methods_to_query = ["web_video", "robot"]

            all_tasks: list[dict] = []
            seen_ids: set[int] = set()
            errors: list[str] = []

            for method in methods_to_query:
                tasks = _query_tasks(
                    caller, method, title=title,
                    page_num=page_num, page_size=page_size,
                )
                if tasks is None:
                    errors.append(f"查询「{method}」失败")
                    continue
                for t in tasks:
                    tid = t.get("id")
                    if tid is not None and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_tasks.append(t)

            # 按 taskCategory 分类统计
            scene_tasks = [t for t in all_tasks if t.get("taskCategory") == _TASK_CATEGORY_SCENE]
            instruction_tasks = [t for t in all_tasks if t.get("taskCategory") == _TASK_CATEGORY_INSTRUCTION]
            strict_tasks = [t for t in all_tasks if t.get("taskCategory") == _TASK_CATEGORY_STRICT]
            issued_tasks = [t for t in all_tasks if t.get("status") == _STATUS_PUBLISHED]

            # 概要列表
            summary = [
                {
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "status": t.get("status"),
                    "taskCategory": t.get("taskCategory"),
                }
                for t in all_tasks
            ]

            result: dict[str, Any] = {
                "success": True,
                "total": len(all_tasks),
                "scene_num": len(scene_tasks),
                "instruction_num": len(instruction_tasks),
                "strict_num": len(strict_tasks),
                "issued": len(issued_tasks),
                "tasks": summary,
            }
            if errors:
                result["_warnings"] = errors

            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询任务列表异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    @mcp.tool()
    def task_detail(task_id: int) -> str:
        """查询单个任务详情（完整字段）。

        Args:
            task_id: 任务 ID（必须为数字，可通过 task_summary 按名称模糊查询获得）

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - error: 错误信息（如果有）
            - data: 任务详情对象（仅非空字段，包含 jobCount 等完整信息）
            - detail: 摘要信息（id、title、status、jobCount、published）
        """

        try:
            resp = caller.get_task(task_id)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            # 从响应体中提取任务数据（兼容 metadata / data 两种 key）
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            task_data = (
                body_dict.get("metadata")
                or body_dict.get("data")
                or body_dict
            )
            if not isinstance(task_data, dict):
                task_data = {}

            # 筛选掉空值字段，保留有内容的字段便于查看
            non_null_data = {k: v for k, v in task_data.items() if v is not None}

            # 摘要信息
            detail = {
                "id": task_data.get("id"),
                "title": task_data.get("title"),
                "status": task_data.get("status"),
                "published": task_data.get("status") == _STATUS_PUBLISHED,
                "taskCategory": task_data.get("taskCategory"),
                "jobCount": task_data.get("jobCount", 0),
            }

            return json.dumps(
                {
                    "success": True,
                    "data": non_null_data,
                    "detail": detail,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询任务详情异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    @mcp.tool()
    def job_summary(
        collect_method: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 200,
    ) -> str:
        """查询平台作业概览——返回作业总数及分类（场景/指令/严格）统计，以及每个有作业的任务的作业数。

        ⚠️ 平台接口按采集方式隔离数据。不传 collect_method 时自动查询所有采集方式并聚合。
        若只想看某类采集方式的任务，可传入 collect_method 过滤。
        常见取值：可在 get_platform_config 的 device_schemes 中查看，通常有
        "web_video"（视频采集）、"robot"（真机采集）等。

        Args:
            collect_method: **可选**。采集方式，如 "web_video"、"robot"。不传则查询全部
            page_num: 页码，默认 1
            page_size: 每页数量，默认 200

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - total_jobs: 平台作业总数（所有任务的 jobCount 之和）
            - scene_jobs: 场景任务作业数
            - instruction_jobs: 指令任务作业数
            - strict_jobs: 严格任务作业数
            - task_count: 有作业的任务数（jobCount > 0）
            - task_jobs: 有作业的任务列表，按 jobCount 降序排列（id, title, taskCategory, jobCount）
        """

        try:
            # 确定要查询的采集方式列表
            if collect_method is not None:
                methods_to_query = [collect_method]
            else:
                methods_to_query = ["web_video", "robot"]

            all_tasks: list[dict] = []
            seen_ids: set[int] = set()
            errors: list[str] = []

            for method in methods_to_query:
                tasks = _query_tasks(
                    caller, method, page_num=page_num, page_size=page_size,
                )
                if tasks is None:
                    errors.append(f"查询「{method}」失败")
                    continue
                for t in tasks:
                    tid = t.get("id")
                    if tid is not None and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_tasks.append(t)

            total_jobs = 0
            scene_jobs = 0
            instruction_jobs = 0
            strict_jobs = 0
            task_jobs = []

            for t in all_tasks:
                job_count = t.get("jobCount", 0) or 0
                category = t.get("taskCategory", "")
                total_jobs += job_count

                if category == _TASK_CATEGORY_SCENE:
                    scene_jobs += job_count
                elif category == _TASK_CATEGORY_INSTRUCTION:
                    instruction_jobs += job_count
                elif category == _TASK_CATEGORY_STRICT:
                    strict_jobs += job_count

                if job_count > 0:
                    task_jobs.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "taskCategory": category,
                        "jobCount": job_count,
                    })

            task_jobs.sort(key=lambda x: x["jobCount"], reverse=True)

            return json.dumps(
                {
                    "success": True,
                    "total_jobs": total_jobs,
                    "scene_jobs": scene_jobs,
                    "instruction_jobs": instruction_jobs,
                    "strict_jobs": strict_jobs,
                    "task_count": len(task_jobs),
                    "task_jobs": task_jobs,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询作业概览异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )
        
    @mcp.tool()
    def job_detail(job_id: int) -> str:
        """查询单个作业详情（完整字段）。

        Args:
            job_id: 作业 ID（必须为数字，可通过 job_summary 按名称模糊查询获得）

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - error: 错误信息（如果有）
            - data: 作业详情对象（仅非空字段，包含 taskId、collectStatus 等完整信息）
            - detail: 摘要信息（id、title、taskId、taskTitle、taskCategory、
              collectStatus、collectStatusLabel[未分配/已分配/已领取]、
              reviewStatus、reviewStatusLabel、receiveCount、requiredMember）
        """
        try:
            resp = caller.get_job(job_id)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            # 从响应体中提取作业数据（兼容多种响应结构：
            #   {"code": 0, "metadata": {job_detail}} / {"code": 0, "data": {job_detail}}）
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            job_data = (
                body_dict.get("metadata")
                or body_dict.get("data")
                or body_dict
            )
            if not isinstance(job_data, dict):
                job_data = {}

            # get_job 端点可能返回过期数据（receiveCount 等字段不准），
            # 用 list_jobs 获取最新数据并合并（list 数据更可靠，优先采用）
            _list_data: dict = {}
            task_id_from_job = job_data.get("taskId")
            if task_id_from_job is not None:
                try:
                    list_resp = caller.list_jobs(taskId=task_id_from_job)
                    if list_resp.status_code == 200:
                        list_items = _extract_metadata_items(list_resp.body)
                        for item in list_items:
                            if isinstance(item, dict) and item.get("id") == job_id:
                                _list_data = {k: v for k, v in item.items() if v is not None}
                                break
                except Exception:
                    pass  # list_jobs 失败时静默回退

            # 合并：list 数据优先（更可靠），get_job 数据补充 list 中缺少的字段
            job_data = {**job_data, **_list_data}

            # 筛选掉空值字段，保留有内容的字段便于查看
            non_null_data = {k: v for k, v in job_data.items() if v is not None}

            # collectStatus 状态映射
            _collect_status_map = {0: "未分配", 1: "已分配", 2: "已领取"}
            _review_status_map = {0: "未分配", 1: "已分配"}
            _collect_status_raw = job_data.get("collectStatus")
            _review_status_raw = job_data.get("reviewStatus")

            # 摘要信息
            detail = {
                "id": job_data.get("id"),
                "title": job_data.get("title"),
                "taskId": job_data.get("taskId"),
                "taskTitle": job_data.get("taskTitle"),
                "taskCategory": job_data.get("taskCategory"),
                "collectStatus": _collect_status_raw,
                "collectStatusLabel": _collect_status_map.get(_collect_status_raw, "未知"),
                "reviewStatus": _review_status_raw,
                "reviewStatusLabel": _review_status_map.get(_review_status_raw, "未知"),
                "receiveCount": job_data.get("receiveCount", 0),
                "requiredMember": job_data.get("requiredMember", 0),
            }
            return json.dumps(
                {
                    "success": True,
                    "data": non_null_data,
                    "detail": detail,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询作业详情异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    @mcp.tool()
    def task_job_details(
        task_id: int,
        page_num: int = 1,
        page_size: int = 100,
    ) -> str:
        """查询指定任务下所有作业的详细信息。

        Args:
            task_id: 任务 ID（必填，必须为数字）
            page_num: 页码，默认 1
            page_size: 每页数量，默认 100

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - total: 作业总数
            - task_id: 任务 ID
            - task_title: 任务标题
            - task_category: 任务分类
            - jobs: 作业详情列表（每个作业的完整非空字段）
        """

        try:
            # 获取任务基本信息（用于上下文）
            task_resp = caller.get_task(task_id)
            task_title = ""
            task_category = ""
            if task_resp.status_code == 200:
                body_dict = task_resp.body if isinstance(task_resp.body, dict) else {}
                task_data = (
                    body_dict.get("metadata")
                    or body_dict.get("data")
                    or body_dict
                )
                if not isinstance(task_data, dict):
                    task_data = {}
                task_title = task_data.get("title", "")
                task_category = task_data.get("taskCategory", "")

            # 获取作业列表
            resp = caller.list_jobs(
                taskId=task_id,
                pageNum=page_num,
                pageSize=page_size,
            )
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            jobs = _extract_metadata_items(resp.body)

            # 从响应元数据中获取总条数（兼容 metadata / data 两种 key）
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            metadata = body_dict.get("metadata") or body_dict.get("data") or {}
            total_count = metadata.get("total", len(jobs)) if isinstance(metadata, dict) else len(jobs)

            # 逐个获取作业详情（get_job 可能返回过期数据，list 数据优先）
            job_list = []
            for j in jobs:
                if not isinstance(j, dict):
                    continue
                job_id = j.get("id")
                if job_id is not None:
                    detail_resp = caller.get_job(job_id)
                    if detail_resp.status_code == 200:
                        detail_body = detail_resp.body if isinstance(detail_resp.body, dict) else {}
                        detail_data = (
                            detail_body.get("metadata")
                            or detail_body.get("data")
                            or detail_body
                        )
                        if not isinstance(detail_data, dict):
                            detail_data = {}
                        # 合并数据：list 数据优先（list_jobs 比 get_job 更可靠），
                        # detail 仅补充 list 中不存在的字段（如 progress）
                        merged = {**{k: v for k, v in detail_data.items() if v is not None},
                                  **{k: v for k, v in j.items() if v is not None}}
                        job_list.append({k: v for k, v in merged.items() if v is not None})
                        continue
                # 回退：直接用列表中的数据
                job_list.append({k: v for k, v in j.items() if v is not None})

            return json.dumps(
                {
                    "success": True,
                    "total": total_count,
                    "task_id": task_id,
                    "task_title": task_title,
                    "task_category": task_category,
                    "jobs": job_list,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询任务作业详情异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )


      
            



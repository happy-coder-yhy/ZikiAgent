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

    @mcp.tool()
    def task_summary(
        title: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 100,
    ) -> str:
        """查询平台任务概要——返回任务总数及分类（场景/指令/严格）统计。

        Args:
            title: 按任务标题模糊筛选（可选）
            page_num: 页码，默认 1
            page_size: 每页数量，默认 100

        Returns:
            JSON 字符串，包含:
            - success: 是否成功
            - total: 服务器返回的任务总数（从元数据中提取，若无可用的元数据总数则为返回列表长度）
            - scene_num: 场景任务数
            - instruction_num: 指令任务数
            - strict_num: 严格任务数
            - issued: 已发布任务数（status == 2）
            - tasks: 任务概要列表
        """

        try:
            resp = caller.list_tasks(
                title=title,
                pageNum=page_num,
                pageSize=page_size,
            )
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            tasks = _extract_metadata_items(resp.body)

            # 尝试从响应元数据中获取总条数（服务器返回的总量）
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            metadata = body_dict.get("metadata", {}) if isinstance(body_dict, dict) else {}
            total_count = metadata.get("total", len(tasks)) if isinstance(metadata, dict) else len(tasks)

            # 按 taskCategory 分类统计
            scene_tasks = [t for t in tasks if isinstance(t, dict) and t.get("taskCategory") == _TASK_CATEGORY_SCENE]
            instruction_tasks = [
                t for t in tasks if isinstance(t, dict) and t.get("taskCategory") == _TASK_CATEGORY_INSTRUCTION
            ]
            strict_tasks = [
                t for t in tasks if isinstance(t, dict) and t.get("taskCategory") == _TASK_CATEGORY_STRICT
            ]

            # 已发布任务（不区分分类）
            issued_tasks = [t for t in tasks if isinstance(t, dict) and t.get("status") == _STATUS_PUBLISHED]

            # 概要列表（用于展示）
            summary = [
                {
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "status": t.get("status"),
                    "taskCategory": t.get("taskCategory"),
                }
                for t in tasks
                if isinstance(t, dict)
            ]

            return json.dumps(
                {
                    "success": True,
                    "total": total_count,
                    "scene_num": len(scene_tasks),
                    "instruction_num": len(instruction_tasks),
                    "strict_num": len(strict_tasks),
                    "issued": len(issued_tasks),
                    "tasks": summary,
                },
                ensure_ascii=False,
                indent=2,
            )
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

            # 从响应体中提取任务数据（body 结构为 {"code": 0, "metadata": {task_detail}}）
            body_dict = resp.body if isinstance(resp.body, dict) else {}
            task_data = body_dict.get("metadata", {}) if isinstance(body_dict, dict) else {}

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
        page_num: int = 1,
        page_size: int = 200,
    ) -> str:
        """查询平台作业概览——返回作业总数及分类（场景/指令/严格）统计，以及每个有作业的任务的作业数。

        Args:
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
            resp = caller.list_tasks(
                pageNum=page_num,
                pageSize=page_size,
            )
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            tasks = _extract_metadata_items(resp.body)

            total_jobs = 0
            scene_jobs = 0
            instruction_jobs = 0
            strict_jobs = 0
            task_jobs = []

            for t in tasks:
                if not isinstance(t, dict):
                    continue
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

    


      
            



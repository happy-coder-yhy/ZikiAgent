"""采集员工具 — query_task_job。"""

from __future__ import annotations

import json
from typing import Any

from ApiCaller.modules.api_caller import _extract_metadata_items


# ---------------------------------------------------------------------------
# collectStatus / reviewStatus 标签映射（与 task_work.py 保持一致）
# ---------------------------------------------------------------------------
_COLLECT_STATUS_MAP = {0: "未分配", 1: "已分配", 2: "已领取"}
_REVIEW_STATUS_MAP = {0: "未分配", 1: "已分配"}

# 常见采集方式，用于 Fallback 扫描发现分配但未领取的任务
_COMMON_COLLECT_METHODS = ["web_video", "robot"]


def register_tools(mcp, caller) -> None:
    """注册采集员相关工具到 MCP 应用。"""

    @mcp.tool()
    def query_task_job(collector_id: str = "") -> str:
        """查看当前与该采集员相关的所有任务作业及情况。

        查询指定采集员的所有任务和作业信息，包括：
        - 该采集员被分配到的所有任务
        - 每个任务下的所有作业及其状态（已领取 / 已分配 / 未分配）
        - 各作业的采集进度（常规采集、异常采集、审核）
        - 已领取 vs 仅分配的汇总统计

        若不传 collector_id，则自动通过当前登录用户获取采集员身份。
        适用于采集员直接说"我的任务"而无需告知用户名的场景。

        Args:
            collector_id: 采集员用户 ID（可选）。不传则自动从当前登录用户获取。
                          可通过 search_user(name="用户名") 查询获取。
                          例如 "6e1465a8-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        """
        try:
            # ---- 自动获取当前用户身份 ----
            if not collector_id:
                info_resp = caller.userinfo()
                if info_resp.status_code != 200:
                    return json.dumps(
                        {
                            "success": False,
                            "error": (
                                "无法自动获取当前用户信息（HTTP "
                                f"{info_resp.status_code}），"
                                "请手动提供 collector_id"
                            ),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                info = (
                    info_resp.body.get("metadata") or info_resp.body
                    if isinstance(info_resp.body, dict)
                    else {}
                )
                collector_id = info.get("id") or ""
                if not collector_id:
                    return json.dumps(
                        {
                            "success": False,
                            "error": (
                                "无法从当前用户信息中提取用户 ID，"
                                "请手动提供 collector_id"
                            ),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )

            # ---------------------------------------------------------------
            # Phase 1: 主路径 — 通过 job-receives 直接发现已领取的任务/作业
            # ---------------------------------------------------------------
            # ---------------------------------------------------------------
            # Phase 1: 主路径 — 通过 job-receives 直接发现已领取的任务/作业
            # ---------------------------------------------------------------
            received_job_ids: set[int] = set()
            task_id_to_received_jobs: dict[int, set[int]] = {}
            discovered_task_ids: set[int] = set()

            resp = caller.list_job_receives(
                collectorId=collector_id,
                pageNum=1,
                pageSize=500,
            )
            if resp.status_code == 200:
                job_receives = _extract_metadata_items(resp.body) if resp.body else []
                for jr in job_receives:
                    if not isinstance(jr, dict):
                        continue
                    jid = jr.get("jobId")
                    tid = jr.get("taskId")
                    if isinstance(jid, int) and isinstance(tid, int):
                        received_job_ids.add(jid)
                        discovered_task_ids.add(tid)
                        task_id_to_received_jobs.setdefault(tid, set()).add(jid)

            # ---------------------------------------------------------------
            # Phase 2: 补充路径 — 扫描 list_tasks，发现分配但未领取的任务
            # ---------------------------------------------------------------
            assigned_task_ids: set[int] = set()

            for method in _COMMON_COLLECT_METHODS:
                resp = caller.list_tasks(
                    collectMethod=method,
                    pageNum=1,
                    pageSize=500,
                )
                if resp.status_code != 200:
                    continue
                tasks = _extract_metadata_items(resp.body) if resp.body else []
                for t in tasks:
                    if not isinstance(t, dict):
                        continue
                    tid = t.get("id")
                    if tid is None:
                        continue
                    collectors = t.get("collectors") or []
                    for c in collectors:
                        if isinstance(c, dict) and c.get("userId") == collector_id:
                            assigned_task_ids.add(tid)
                            break

            # 合并：去重后的所有相关任务 ID
            all_task_ids = discovered_task_ids | assigned_task_ids

            # ---------------------------------------------------------------
            # Phase 3: 充实 — 获取每个任务的详情和作业列表
            # ---------------------------------------------------------------
            task_list: list[dict[str, Any]] = []
            total_jobs_count = 0
            total_received_count = len(received_job_ids)
            total_assigned_not_received = 0

            # 进度汇总
            agg_normal_collect = 0
            agg_normal_collect_total = 0
            agg_normal_review = 0
            agg_abnormal_collect = 0
            agg_abnormal_collect_total = 0
            agg_abnormal_review = 0

            for tid in sorted(all_task_ids):
                # 获取任务详情
                task_resp = caller.get_task(tid)
                task_title = f"Task-{tid}"
                task_category = ""
                project_name = ""
                collect_method = ""
                if task_resp.status_code == 200:
                    body_dict = task_resp.body if isinstance(task_resp.body, dict) else {}
                    td = (
                        body_dict.get("metadata")
                        or body_dict.get("data")
                        or body_dict
                    )
                    if isinstance(td, dict):
                        task_title = td.get("title", task_title)
                        task_category = td.get("taskCategory", "")
                        project_name = td.get("projectName", "")
                        collect_method = td.get("collectMethod", "")

                # 获取任务下所有作业
                jobs_resp = caller.list_jobs(taskId=tid, pageNum=1, pageSize=500)
                all_jobs: list[dict[str, Any]] = []
                if jobs_resp.status_code == 200:
                    raw_jobs = _extract_metadata_items(jobs_resp.body) if jobs_resp.body else []
                    for j in raw_jobs:
                        if not isinstance(j, dict):
                            continue
                        jid = j.get("id")
                        if jid is None:
                            continue

                        is_received = jid in received_job_ids
                        cs_raw = j.get("collectStatus")
                        rs_raw = j.get("reviewStatus")
                        progress = j.get("progress") or {}

                        # 构建作业摘要
                        job_summary: dict[str, Any] = {
                            "id": jid,
                            "name": j.get("name"),
                            "description": j.get("description"),
                            "collectStatus": cs_raw,
                            "collectStatusLabel": _COLLECT_STATUS_MAP.get(cs_raw, "未知"),
                            "reviewStatus": rs_raw,
                            "reviewStatusLabel": _REVIEW_STATUS_MAP.get(rs_raw, "未知"),
                            "received": is_received,
                            "requiredMember": j.get("requiredMember"),
                            "requiredRepeat": j.get("requiredRepeat"),
                            "receiveCount": j.get("receiveCount"),
                        }

                        # 进度详情（只保留有效字段）
                        prog = {
                            k: v
                            for k, v in progress.items()
                            if k in (
                                "normalCollect",
                                "normalCollectTotal",
                                "normalReview",
                                "abnormalCollect",
                                "abnormalCollectTotal",
                                "abnormalReview",
                            )
                        }
                        if prog:
                            job_summary["progress"] = prog

                        # 去除 None 值
                        job_summary = {k: v for k, v in job_summary.items() if v is not None}
                        all_jobs.append(job_summary)

                        # 累加进度
                        if not is_received:
                            total_assigned_not_received += 1
                        agg_normal_collect += progress.get("normalCollect") or 0
                        agg_normal_collect_total += progress.get("normalCollectTotal") or 0
                        agg_normal_review += progress.get("normalReview") or 0
                        agg_abnormal_collect += progress.get("abnormalCollect") or 0
                        agg_abnormal_collect_total += progress.get("abnormalCollectTotal") or 0
                        agg_abnormal_review += progress.get("abnormalReview") or 0

                total_jobs_count += len(all_jobs)

                # 构建任务条目
                task_entry: dict[str, Any] = {
                    "task_id": tid,
                    "title": task_title,
                    "taskCategory": task_category,
                    "projectName": project_name,
                    "collectMethod": collect_method,
                    "jobCount": len(all_jobs),
                    "receivedJobCount": len(task_id_to_received_jobs.get(tid, set())),
                    "jobs": all_jobs,
                }
                task_entry = {k: v for k, v in task_entry.items() if v is not None}
                task_list.append(task_entry)

            # ---------------------------------------------------------------
            # Phase 4: 汇总统计与返回
            # ---------------------------------------------------------------
            overall_progress_pct = None
            if agg_normal_collect_total > 0:
                overall_progress_pct = round(
                    agg_normal_collect / agg_normal_collect_total * 100, 1
                )

            summary = {
                "total_tasks": len(task_list),
                "total_jobs": total_jobs_count,
                "received_jobs": total_received_count,
                "assigned_not_received_jobs": total_assigned_not_received,
                "overall_progress": {
                    "normalCollect": agg_normal_collect,
                    "normalCollectTotal": agg_normal_collect_total,
                    "normalCollectPct": overall_progress_pct,
                    "normalReview": agg_normal_review,
                    "abnormalCollect": agg_abnormal_collect,
                    "abnormalCollectTotal": agg_abnormal_collect_total,
                    "abnormalReview": agg_abnormal_review,
                },
            }

            return json.dumps(
                {
                    "success": True,
                    "collector_id": collector_id,
                    "summary": summary,
                    "tasks": task_list,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询采集员任务作业异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

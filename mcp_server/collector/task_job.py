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
    
    @mcp.tool()
    def claim_job(
        job_description: str = "",
        task_name: str = "",
        job_id: str = "",
        task_id: str = "",
    ) -> str:
        """采集员领取与自己相关的任务（已发布）下的作业。

        支持两种查找方式：
        1. 按作业描述 + 可选任务名（模糊匹配）— 推荐，user-friendly
        2. 按作业 ID + 任务 ID（精确匹配）

        自动识别当前采集员身份。
        只有已发布（status=2）的任务下的作业才能被领取。

        Args:
            job_description: 作业描述（模糊匹配），与 job_id 二选一
            task_name: 任务名称（可选），用于缩小查找范围
            job_id: 作业 ID（精确匹配），与 job_description 二选一
            task_id: 任务 ID，配合 job_id 使用
        """
        try:
            # ---- Step 1: 自动获取当前采集员身份 ----
            info_resp = caller.userinfo()
            if info_resp.status_code != 200:
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            "无法自动获取当前用户信息（HTTP "
                            f"{info_resp.status_code}），请稍后重试"
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
            collector_name = info.get("name") or ""
            if not collector_id:
                return json.dumps(
                    {
                        "success": False,
                        "error": "无法从当前用户信息中提取用户 ID，请稍后重试",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- Step 2: 查找目标作业及其所属任务 ----
            matched_jobs: list[dict] = []  # [{job_id, job_name, job_description, task_id, task_title, task_status}]

            if job_id:
                # --- 精确 ID 模式 ---
                if not task_id:
                    return json.dumps(
                        {
                            "success": False,
                            "error": "使用 job_id 查找时必须同时提供 task_id",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                jid = int(job_id)
                tid = int(task_id)
                job_resp = caller.get_job(jobId=jid)
                if job_resp.status_code != 200:
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"未找到作业 ID={jid}",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                jdata = (
                    job_resp.body.get("metadata") or job_resp.body
                    if isinstance(job_resp.body, dict)
                    else {}
                )
                matched_jobs.append({
                    "job_id": jid,
                    "job_name": jdata.get("name") or "",
                    "job_description": jdata.get("description") or "",
                    "task_id": tid,
                    "task_title": "",
                    "task_status": None,
                })
            elif job_description:
                # --- 模糊匹配模式 ---
                jd_lower = job_description.strip().lower()
                if not jd_lower:
                    return json.dumps(
                        {
                            "success": False,
                            "error": "作业描述不能为空",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )

                # Phase A: 发现采集员相关的所有任务 ID
                related_task_ids: set[int] = set()

                # 通过 job-receives
                resp = caller.list_job_receives(
                    collectorId=collector_id,
                    pageNum=1,
                    pageSize=500,
                )
                if resp.status_code == 200:
                    for jr in _extract_metadata_items(resp.body) if resp.body else []:
                        if isinstance(jr, dict) and isinstance(jr.get("taskId"), int):
                            related_task_ids.add(jr["taskId"])

                # 通过 list_tasks（分配但未领取）
                for method in _COMMON_COLLECT_METHODS:
                    resp = caller.list_tasks(
                        collectMethod=method,
                        pageNum=1,
                        pageSize=500,
                    )
                    if resp.status_code != 200:
                        continue
                    for t in _extract_metadata_items(resp.body) if resp.body else []:
                        if not isinstance(t, dict):
                            continue
                        collectors = t.get("collectors") or []
                        for c in collectors:
                            if isinstance(c, dict) and c.get("userId") == collector_id:
                                tid = t.get("id")
                                if isinstance(tid, int):
                                    related_task_ids.add(tid)
                                break

                # 若指定了 task_name，只保留匹配的任务
                tn_lower = task_name.strip().lower() if task_name else ""

                # Phase B: 在每个相关任务下搜索匹配的作业
                for tid in sorted(related_task_ids):
                    # 获取任务信息（用于 title 和 status）
                    task_resp = caller.get_task(tid)
                    task_data: dict = {}
                    task_title = f"Task-{tid}"
                    task_status = None
                    if task_resp.status_code == 200:
                        body_dict = task_resp.body if isinstance(task_resp.body, dict) else {}
                        td = (
                            body_dict.get("metadata")
                            or body_dict.get("data")
                            or body_dict
                        )
                        if isinstance(td, dict):
                            task_data = td
                            task_title = td.get("title", task_title)
                            task_status = td.get("status")

                    # 若指定了 task_name，检查任务名是否匹配
                    if tn_lower and tn_lower not in task_title.lower():
                        continue

                    # 获取任务下所有作业
                    jobs_resp = caller.list_jobs(taskId=tid, pageNum=1, pageSize=500)
                    if jobs_resp.status_code != 200:
                        continue

                    for j in _extract_metadata_items(jobs_resp.body) if jobs_resp.body else []:
                        if not isinstance(j, dict):
                            continue
                        j_desc = (j.get("description") or "").lower()
                        if jd_lower in j_desc:
                            jid_val = j.get("id")
                            if jid_val is None:
                                continue
                            matched_jobs.append({
                                "job_id": jid_val,
                                "job_name": j.get("name") or "",
                                "job_description": j.get("description") or "",
                                "task_id": tid,
                                "task_title": task_title,
                                "task_status": task_status,
                            })
            else:
                return json.dumps(
                    {
                        "success": False,
                        "error": "请提供 job_description（作业描述）或 job_id + task_id",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- Step 3: 处理匹配结果 ----
            if not matched_jobs:
                hint = ""
                if task_name:
                    hint = f"（已限定任务名「{task_name}」）"
                return json.dumps(
                    {
                        "success": False,
                        "error": f"未找到与「{job_description or job_id}」匹配的作业{hint}，请确认作业描述或 ID 是否正确",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if len(matched_jobs) > 1:
                # 返回候选列表供用户选择
                candidates = []
                for mj in matched_jobs:
                    candidates.append({
                        "job_id": mj["job_id"],
                        "task_id": mj["task_id"],
                        "job_description": mj["job_description"],
                        "job_name": mj["job_name"],
                        "task_title": mj["task_title"],
                    })
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"匹配到 {len(matched_jobs)} 个作业，请指定更精确的条件"
                        ),
                        "candidates": candidates,
                        "hint": "请从中选择一个作业，使用 job_id + task_id 精确指定",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            target = matched_jobs[0]
            target_job_id = target["job_id"]
            target_task_id = target["task_id"]

            # ---- Step 4: 检查任务是否已发布 ----
            # 若 task_status 还未获取，重新获取
            task_status = target["task_status"]
            if task_status is None:
                task_resp = caller.get_task(target_task_id)
                if task_resp.status_code == 200:
                    body_dict = task_resp.body if isinstance(task_resp.body, dict) else {}
                    td = (
                        body_dict.get("metadata")
                        or body_dict.get("data")
                        or body_dict
                    )
                    if isinstance(td, dict):
                        task_status = td.get("status")
                        target["task_title"] = td.get("title", target["task_title"])

            if task_status != 2:
                status_label = {1: "未发布", 2: "已发布"}.get(task_status, f"未知({task_status})")
                return json.dumps(
                    {
                        "success": False,
                        "error": (
                            f"该任务（{target['task_title']}）尚未发布（状态：{status_label}），"
                            "无法领取作业。只有已发布的任务才能领取作业。"
                        ),
                        "task_id": target_task_id,
                        "task_title": target["task_title"],
                        "task_status": task_status,
                        "job_id": target_job_id,
                        "job_description": target["job_description"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- Step 5: 幂等检查 — 是否已领取 ----
            existing_resp = caller.list_job_receives(
                collectorId=collector_id,
                jobId=target_job_id,
                taskId=target_task_id,
            )
            if existing_resp.status_code == 200:
                existing_records = (
                    _extract_metadata_items(existing_resp.body)
                    if existing_resp.body
                    else []
                )
                if existing_records:
                    return json.dumps(
                        {
                            "success": True,
                            "already_claimed": True,
                            "message": "该作业已被您领取，无需重复操作",
                            "job_id": target_job_id,
                            "task_id": target_task_id,
                            "job_description": target["job_description"],
                            "task_title": target["task_title"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )

            # ---- Step 6: 领取作业 ----
            claim_resp = caller.create_job_receives(
                collectorId=collector_id,
                jobId=target_job_id,
                taskId=target_task_id,
            )

            if claim_resp.status_code in (200, 201):
                return json.dumps(
                    {
                        "success": True,
                        "message": (
                            f"已成功领取作业「{target['job_description']}」"
                            f"（任务：{target['task_title']}）"
                        ),
                        "collector_id": collector_id,
                        "collector_name": collector_name,
                        "job_id": target_job_id,
                        "task_id": target_task_id,
                        "job_description": target["job_description"],
                        "job_name": target["job_name"],
                        "task_title": target["task_title"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                error_msg = ""
                if isinstance(claim_resp.body, dict):
                    error_msg = (
                        claim_resp.body.get("message")
                        or claim_resp.body.get("reason")
                        or str(claim_resp.body)
                    )
                return json.dumps(
                    {
                        "success": False,
                        "error": f"领取失败（HTTP {claim_resp.status_code}）: {error_msg}",
                        "job_id": target_job_id,
                        "task_id": target_task_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"领取作业异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )


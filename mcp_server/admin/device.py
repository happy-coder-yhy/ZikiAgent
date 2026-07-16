"""设备管理工具 — device_summary。"""

from __future__ import annotations

import json

from ApiCaller.modules.api_caller import _extract_metadata_items


def register_tools(mcp, caller) -> None:
    """注册设备相关工具到 MCP 应用。"""

    @mcp.tool()
    def device_summary() -> str:
        """查询平台设备概要信息。

        返回设备总数、在线/离线设备数、真机/视频设备数，
        以及各设备型号（deviceBodyName）对应的设备数量。

        用于快速了解平台设备整体状况，无需翻页查询。
        """
        try:
            # 一次拉取全部设备（上限 500，覆盖绝大多数场景）
            resp = caller.list_devices(pageNum=1, pageSize=500)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询设备列表失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )

            devices: list[dict] = _extract_metadata_items(resp.body) if resp.body else []

            if not devices:
                return json.dumps(
                    {
                        "success": True,
                        "total": 0,
                        "online": 0,
                        "offline": 0,
                        "real_device": 0,
                        "video_device": 0,
                        "by_model": {},
                        "devices": [],
                    },
                    ensure_ascii=False, indent=2,
                )

            # ---------- 聚合统计 ----------
            total = len(devices)
            online = 0
            offline = 0
            real_device = 0
            video_device = 0
            by_model: dict[str, int] = {}

            for d in devices:
                if not isinstance(d, dict):
                    continue

                # 在线状态：1 = 在线，其他 = 离线
                status = d.get("status")
                if status == 1:
                    online += 1
                else:
                    offline += 1

                # 设备类别
                category = str(d.get("category") or "").lower()
                if category == "robot":
                    real_device += 1
                elif category == "video":
                    video_device += 1

                # 按型号统计（优先 deviceBodyName，其次 deviceTypeName）
                model = d.get("deviceBodyName") or d.get("deviceTypeName") or "未知型号"
                by_model[model] = by_model.get(model, 0) + 1

            return json.dumps(
                {
                    "success": True,
                    "total": total,
                    "online": online,
                    "offline": offline,
                    "real_device": real_device,
                    "video_device": video_device,
                    "by_model": by_model,
                },
                ensure_ascii=False, indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询设备异常: {e}"},
                ensure_ascii=False, indent=2,
            )
        
    @mcp.tool()
    def device_detail(name: str = "", device_code: str = "") -> str:
        """查询设备详细信息（含绑定的采集员和作业）。

        先通过设备名称搜索匹配设备，获取设备编码后再查询完整详情。
        若匹配到多台同名设备，则列出所有匹配项供用户选择。
        也可直接传入 device_code 跳过搜索，直接获取详情。

        返回的设备信息含绑定的采集员（displayName, name, createdAt）和
        作业（description, planCollectCount）。

        Args:
            name: 设备名称（支持模糊匹配），如 "agentTest"、"dunjia"
            device_code: 设备编码，传入后直接查询详情，跳过名称搜索
        """

        # ---- 内部：充实绑定的采集员和作业信息 ----
        def _enrich_device(device: dict) -> dict:
            """为设备补充绑定的采集员和作业信息。"""
            result = {
                "id": device.get("id"),
                "deviceCode": device.get("deviceCode"),
                "deviceName": device.get("deviceName"),
                "deviceTypeName": device.get("deviceTypeName"),
                "deviceBodyName": device.get("deviceBodyName"),
                "category": device.get("category"),
                "categoryLabel": (
                    "真机" if str(device.get("category") or "").lower() == "robot"
                    else "视频" if str(device.get("category") or "").lower() == "video"
                    else str(device.get("category") or "")
                ),
                "status": device.get("status"),
                "statusLabel": "在线" if device.get("status") == 1 else "离线",
                "lastOnlineTime": device.get("lastOnlineTime"),
                "createdAt": device.get("createdAt"),
                "updatedAt": device.get("updatedAt"),
                "collector": None,
                "job": None,
            }

            # ---- 充实采集员（仅返回 displayName, name, createTime） ----
            cid = device.get("collectorId")
            if cid:
                collector_info = caller.resolve_user_info(cid)
                if collector_info:
                    result["collector"] = {
                        "displayName": collector_info["displayName"],
                        "name": collector_info["name"],
                        "createdAt": collector_info["createTime"],
                    }

            # ---- 充实作业信息 ----
            jid = device.get("jobId")
            if jid is not None:
                try:
                    job_resp = caller.get_job(jobId=int(jid))
                    if job_resp.status_code == 200:
                        jbody = job_resp.body
                        job = (
                            jbody.get("metadata") or jbody
                            if isinstance(jbody, dict)
                            else {}
                        )
                        if isinstance(job, dict):
                            raw_cs = job.get("collectStatus")
                            raw_rs = job.get("reviewStatus")
                            progress = job.get("progress") or {}
                            result["job"] = {
                                "description": job.get("description"),
                                "planCollectCount": job.get("requiredRepeat"),
                                "collectStatus": raw_cs,
                                "collectStatusLabel": (
                                    {0: "未分配", 1: "已分配", 2: "已领取"}.get(raw_cs, "未知")
                                ),
                                "reviewStatus": raw_rs,
                                "reviewStatusLabel": (
                                    {0: "未分配", 1: "已分配"}.get(raw_rs, "未知")
                                ),
                                "progress": {
                                    k: v
                                    for k, v in progress.items()
                                    if k in (
                                        "normalCollect", "normalCollectTotal",
                                        "normalReview",
                                        "abnormalCollect", "abnormalCollectTotal",
                                        "abnormalReview",
                                    )
                                },
                            }
                except Exception:
                    pass

            return result

        try:
            # ---- 模式 1：直接通过 device_code 查询 ----
            if device_code:
                resp = caller.get_device_by_code(deviceCode=device_code)
                if resp.status_code != 200:
                    return json.dumps(
                        {"success": False, "error": f"查询设备详情失败: HTTP {resp.status_code}"},
                        ensure_ascii=False, indent=2,
                    )
                body = resp.body
                if isinstance(body, dict):
                    detail = body.get("metadata") or body
                else:
                    detail = body
                enriched = _enrich_device(detail) if isinstance(detail, dict) else detail
                return json.dumps(
                    {"success": True, "found": True, "device": enriched},
                    ensure_ascii=False, indent=2,
                )

            # ---- 模式 2：通过 name 搜索 ----
            if not name:
                return json.dumps(
                    {"success": False, "error": "请提供设备名称（name）或设备编码（device_code）"},
                    ensure_ascii=False, indent=2,
                )

            # 先按 deviceName 搜索
            resp = caller.list_devices(deviceName=name, pageNum=1, pageSize=50)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"搜索设备失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )

            devices: list[dict] = _extract_metadata_items(resp.body) if resp.body else []

            # 若 deviceName 搜不到，尝试按 deviceCode 搜索
            if not devices:
                resp = caller.list_devices(deviceCode=name, pageNum=1, pageSize=50)
                if resp.status_code != 200:
                    return json.dumps(
                        {"success": False, "error": f"搜索设备失败: HTTP {resp.status_code}"},
                        ensure_ascii=False, indent=2,
                    )
                devices = _extract_metadata_items(resp.body) if resp.body else []

            # ---- 无匹配 ----
            if not devices:
                return json.dumps(
                    {
                        "success": True,
                        "found": False,
                        "message": f"未找到名称或编码包含「{name}」的设备",
                        "devices": [],
                    },
                    ensure_ascii=False, indent=2,
                )

            # ---- 唯一匹配：返回详情 ----
            if len(devices) == 1:
                code = devices[0].get("deviceCode") or ""
                if not code:
                    return json.dumps(
                        {"success": False, "error": "匹配到的设备缺少 deviceCode，无法查询详情"},
                        ensure_ascii=False, indent=2,
                    )
                resp = caller.get_device_by_code(deviceCode=code)
                if resp.status_code != 200:
                    return json.dumps(
                        {"success": False, "error": f"查询设备详情失败: HTTP {resp.status_code}"},
                        ensure_ascii=False, indent=2,
                    )
                body = resp.body
                if isinstance(body, dict):
                    detail = body.get("metadata") or body
                else:
                    detail = body
                enriched = _enrich_device(detail) if isinstance(detail, dict) else detail
                return json.dumps(
                    {"success": True, "found": True, "device": enriched},
                    ensure_ascii=False, indent=2,
                )

            # ---- 多个匹配：列出所有，让用户选择 ----
            match_list = [
                {
                    "deviceCode": d.get("deviceCode"),
                    "deviceName": d.get("deviceName"),
                    "deviceTypeName": d.get("deviceTypeName"),
                    "category": d.get("category"),
                    "status": "在线" if d.get("status") == 1 else "离线",
                }
                for d in devices if isinstance(d, dict)
            ]

            return json.dumps(
                {
                    "success": True,
                    "found": True,
                    "multiple": True,
                    "count": len(devices),
                    "message": (
                        f"找到 {len(devices)} 台匹配「{name}」的设备，"
                        f"请根据 deviceCode 指定要查询的设备："
                        f"device_detail(device_code=\"<deviceCode>\")"
                    ),
                    "devices": match_list,
                },
                ensure_ascii=False, indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询设备异常: {e}"},
                ensure_ascii=False, indent=2,
            )
    
    @mcp.tool()
    def bind_collector_or_job(
        device_code: str,
        collector_id: str = "",
        job_id: str = "",
    ) -> str:
        """绑定采集员或作业到设备。

        未传 collector_id / job_id 时自动保留设备现有的绑定值，
        因此分多次分别绑定采集员和作业不会互相覆盖。

        采集员 ID 请通过 search_user(name="用户名") 查询获取。
        作业 ID 请通过 job_summary 或 job_detail 查询获取。

        Args:
            device_code: 设备编码（必填），如 "dunjia_device001"
            collector_id: 采集员用户 ID 字符串，与 job_id 至少提供一个
            job_id: 作业 ID 字符串，与 collector_id 至少提供一个
        """
        if not device_code:
            return json.dumps(
                {"success": False, "error": "请提供设备编码（device_code）"},
                ensure_ascii=False, indent=2,
            )
        if not collector_id and not job_id:
            return json.dumps(
                {"success": False, "error": "请提供采集员 ID（collector_id）或作业 ID（job_id）"},
                ensure_ascii=False, indent=2,
            )

        try:
            # 1. 通过 device_code 查询设备
            resp = caller.get_device_by_code(deviceCode=device_code)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询设备失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )
            body = resp.body
            device = (body.get("metadata") or body) if isinstance(body, dict) else {}
            if not device:
                return json.dumps(
                    {"success": False, "error": f"未找到设备编码为「{device_code}」的设备"},
                    ensure_ascii=False, indent=2,
                )
            device_id = device.get("id")
            if not device_id:
                return json.dumps(
                    {"success": False, "error": "设备数据中缺少 id 字段"},
                    ensure_ascii=False, indent=2,
                )

            # 2. 读取当前绑定状态，未传的字段保留现有值，防止覆盖丢失
            current_collector = device.get("collectorId")
            current_job = device.get("jobId")

            final_collector = collector_id if collector_id else (current_collector or None)
            final_job = job_id if job_id else (str(current_job) if current_job else None)

            # 3. 调用设备绑定接口
            resp = caller.bind_device(
                deviceId=device_id,
                collectorId=final_collector,
                jobId=final_job,
            )
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"绑定失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )

            bound_items = []
            if final_collector:
                bound_items.append(f"采集员 {final_collector}")
            if final_job:
                bound_items.append(f"作业 {final_job}")

            return json.dumps(
                {
                    "success": True,
                    "message": f"已为设备「{device_code}」绑定{'、'.join(bound_items)}",
                    "device_code": device_code,
                    "bound": {
                        "collector_id": final_collector,
                        "job_id": final_job,
                    },
                },
                ensure_ascii=False, indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"绑定异常: {e}"},
                ensure_ascii=False, indent=2,
            )

    @mcp.tool()
    def change_bind(
        device_code: str,
        collector_id: str = "",
        job_id: str = "",
    ) -> str:
        """重新绑定设备采集员或作业。先解绑当前的，再绑定新的。

        只解绑并替换用户明确提供的字段，未传的字段保留现有值，
        因此仅更换采集员时不会影响已绑定的作业（反之亦然）。

        采集员 ID 请通过 search_user(name="用户名") 查询获取。
        作业 ID 请通过 job_summary 或 job_detail 查询获取。

        Args:
            device_code: 设备编码（必填），如 "dunjia_device001"
            collector_id: 新采集员用户 ID 字符串，与 job_id 至少提供一个
            job_id: 新作业 ID 字符串，与 collector_id 至少提供一个
        """
        if not device_code:
            return json.dumps(
                {"success": False, "error": "请提供设备编码（device_code）"},
                ensure_ascii=False, indent=2,
            )
        if not collector_id and not job_id:
            return json.dumps(
                {"success": False, "error": "请提供采集员 ID（collector_id）或作业 ID（job_id）"},
                ensure_ascii=False, indent=2,
            )

        try:
            # 1. 查询设备当前状态
            resp = caller.get_device_by_code(deviceCode=device_code)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询设备失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )
            body = resp.body
            device = (body.get("metadata") or body) if isinstance(body, dict) else {}
            if not device:
                return json.dumps(
                    {"success": False, "error": f"未找到设备编码为「{device_code}」的设备"},
                    ensure_ascii=False, indent=2,
                )
            device_id = device.get("id")
            if not device_id:
                return json.dumps(
                    {"success": False, "error": "设备数据中缺少 id 字段"},
                    ensure_ascii=False, indent=2,
                )

            current_collector = device.get("collectorId")
            current_job = device.get("jobId")

            # 2. 解绑：若当前已有绑定，先解绑
            unbound_items = []
            if collector_id and current_collector:
                resp = caller.unbind_device(deviceId=device_id, collectorId=current_collector)
                if resp.status_code != 200:
                    return json.dumps(
                        {"success": False, "error": f"解绑采集员失败: HTTP {resp.status_code}"},
                        ensure_ascii=False, indent=2,
                    )
                unbound_items.append(f"采集员 {current_collector}")
            if job_id and current_job:
                resp = caller.unbind_device(deviceId=device_id, jobId=str(current_job))
                if resp.status_code != 200:
                    return json.dumps(
                        {"success": False, "error": f"解绑作业失败: HTTP {resp.status_code}"},
                        ensure_ascii=False, indent=2,
                    )
                unbound_items.append(f"作业 {current_job}")

            # 3. 绑定新值（未传的字段保留现有值，防止覆盖丢失）
            final_collector = collector_id if collector_id else (current_collector or None)
            final_job = job_id if job_id else (str(current_job) if current_job else None)

            resp = caller.bind_device(
                deviceId=device_id,
                collectorId=final_collector,
                jobId=final_job,
            )
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"绑定失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )

            bound_items = []
            if final_collector:
                bound_items.append(f"采集员 {final_collector}")
            if final_job:
                bound_items.append(f"作业 {final_job}")

            parts = []
            if unbound_items:
                parts.append(f"已解绑{'、'.join(unbound_items)}")
            parts.append(f"已绑定{'、'.join(bound_items)}")

            return json.dumps(
                {
                    "success": True,
                    "message": "；".join(parts),
                    "device_code": device_code,
                    "unbound": {
                        "collector_id": current_collector if collector_id and current_collector else None,
                        "job_id": current_job if job_id and current_job else None,
                    },
                    "bound": {
                        "collector_id": final_collector,
                        "job_id": final_job,
                    },
                },
                ensure_ascii=False, indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"重新绑定异常: {e}"},
                ensure_ascii=False, indent=2,
            )

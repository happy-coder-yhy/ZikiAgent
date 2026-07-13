"""采集员工具 — query_my_device。"""

from __future__ import annotations

import json

from ApiCaller.modules.api_caller import _extract_metadata_items


# 设备状态映射
_STATUS_MAP = {0: "离线", 1: "在线"}
# 设备类别中文标签
_CATEGORY_MAP = {"robot": "真机", "video": "视频"}
# 采集状态映射（与 task_job.py 保持一致）
_COLLECT_STATUS_MAP = {0: "未分配", 1: "已分配", 2: "已领取"}
_REVIEW_STATUS_MAP = {0: "未分配", 1: "已分配"}


def register_tools(mcp, caller) -> None:
    """注册采集员设备相关工具到 MCP 应用。"""

    @mcp.tool()
    def query_my_device(collector_id: str = "") -> str:
        """查询当前登录采集员是否已被绑定设备。

        自动通过 .env 中配置的登录账号获取当前采集员身份，
        查询平台中是否有设备已绑定到该采集员。

        - 若有绑定：返回设备详细信息（设备编码、名称、型号、状态等）
        - 若无绑定：返回提示信息，告知暂未绑定设备

        也可显式传入 collector_id 查询指定采集员的设备绑定情况。

        Args:
            collector_id: 采集员用户 ID（可选）。不传则自动从当前登录用户获取。
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

            # ---- 查询绑定到该采集员的设备 ----
            resp = caller.list_devices(collectorId=collector_id, pageNum=1, pageSize=500)
            if resp.status_code != 200:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"查询设备列表失败: HTTP {resp.status_code}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            devices: list[dict] = _extract_metadata_items(resp.body) if resp.body else []

            # ---- 若 API 未过滤，客户端兜底筛选 ----
            if devices:
                first = devices[0]
                if isinstance(first, dict) and "collectorId" not in first:
                    # API 未按 collectorId 过滤，手动筛选
                    devices = [
                        d for d in devices
                        if isinstance(d, dict) and d.get("collectorId") == collector_id
                    ]

            # ---- 无绑定设备 ----
            if not devices:
                return json.dumps(
                    {
                        "success": True,
                        "bound": False,
                        "collector_id": collector_id,
                        "message": "当前采集员暂未绑定任何设备",
                        "devices": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- 构建设备信息列表 ----
            device_list = []
            for d in devices:
                if not isinstance(d, dict):
                    continue
                status_raw = d.get("status")
                category_raw = str(d.get("category") or "").lower()
                device_list.append(
                    {
                        "id": d.get("id"),
                        "deviceCode": d.get("deviceCode"),
                        "deviceName": d.get("deviceName"),
                        "deviceTypeName": d.get("deviceTypeName"),
                        "deviceBodyName": d.get("deviceBodyName"),
                        "category": category_raw,
                        "categoryLabel": _CATEGORY_MAP.get(category_raw, category_raw),
                        "status": status_raw,
                        "statusLabel": _STATUS_MAP.get(status_raw, "未知"),
                        "collectorId": d.get("collectorId"),
                        "jobId": d.get("jobId"),
                    }
                )

            return json.dumps(
                {
                    "success": True,
                    "bound": True,
                    "collector_id": collector_id,
                    "count": len(device_list),
                    "message": f"当前采集员已绑定 {len(device_list)} 台设备",
                    "devices": device_list,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询设备绑定异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    @mcp.tool()
    def query_device_binding(
        device_name: str = "",
        device_code: str = "",
    ) -> str:
        """查询指定设备的绑定情况 — 被绑了哪些采集员和作业。

        通过设备名称或设备编码查找设备，返回该设备当前绑定的采集员信息
        （含用户名）和作业信息（含作业名称、状态）。

        Args:
            device_name: 设备名称（支持模糊匹配），如 "agentTest"、"dunjia"
            device_code: 设备编码（精确匹配），如 "dunjia_device001"
                         与 device_name 至少提供一个；同时提供时优先使用 device_code
        """
        try:
            # ---- 参数校验 ----
            if not device_name and not device_code:
                return json.dumps(
                    {
                        "success": False,
                        "error": "请提供设备名称（device_name）或设备编码（device_code）",
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- 查找设备 ----
            device: dict | None = None

            if device_code:
                resp = caller.get_device_by_code(deviceCode=device_code)
                if resp.status_code != 200:
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"查询设备失败: HTTP {resp.status_code}",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                body = resp.body
                device = (body.get("metadata") or body) if isinstance(body, dict) else {}
            else:
                # 按名称模糊搜索
                resp = caller.list_devices(deviceName=device_name, pageNum=1, pageSize=50)
                if resp.status_code != 200:
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"搜索设备失败: HTTP {resp.status_code}",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                devices = _extract_metadata_items(resp.body) if resp.body else []

                # 若 deviceName 搜不到，尝试按 deviceCode 搜索
                if not devices:
                    resp = caller.list_devices(deviceCode=device_name, pageNum=1, pageSize=50)
                    if resp.status_code != 200:
                        return json.dumps(
                            {
                                "success": False,
                                "error": f"搜索设备失败: HTTP {resp.status_code}",
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    devices = _extract_metadata_items(resp.body) if resp.body else []

                if not devices:
                    return json.dumps(
                        {
                            "success": True,
                            "found": False,
                            "message": f"未找到名称或编码包含「{device_name}」的设备",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )

                if len(devices) > 1:
                    # 多匹配：列出选项让用户选择
                    match_list = [
                        {
                            "deviceCode": d.get("deviceCode"),
                            "deviceName": d.get("deviceName"),
                            "deviceTypeName": d.get("deviceTypeName"),
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
                                f"找到 {len(devices)} 台匹配「{device_name}」的设备，"
                                f"请用 device_code 指定要查询的设备"
                            ),
                            "devices": match_list,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )

                # 唯一匹配：获取详情
                code = devices[0].get("deviceCode") or ""
                if not code:
                    return json.dumps(
                        {"success": False, "error": "匹配到的设备缺少 deviceCode，无法查询详情"},
                        ensure_ascii=False,
                        indent=2,
                    )
                resp = caller.get_device_by_code(deviceCode=code)
                if resp.status_code != 200:
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"查询设备详情失败: HTTP {resp.status_code}",
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                body = resp.body
                device = (body.get("metadata") or body) if isinstance(body, dict) else {}

            if not device:
                return json.dumps(
                    {"success": False, "error": "未找到指定设备"},
                    ensure_ascii=False,
                    indent=2,
                )

            # ---- 构建设备基本信息 ----
            status_raw = device.get("status")
            category_raw = str(device.get("category") or "").lower()
            device_info = {
                "id": device.get("id"),
                "deviceCode": device.get("deviceCode"),
                "deviceName": device.get("deviceName"),
                "deviceTypeName": device.get("deviceTypeName"),
                "deviceBodyName": device.get("deviceBodyName"),
                "category": category_raw,
                "categoryLabel": _CATEGORY_MAP.get(category_raw, category_raw),
                "status": status_raw,
                "statusLabel": _STATUS_MAP.get(status_raw, "未知"),
            }

            # ---- 充实采集员信息 ----
            collector_info = None
            cid = device.get("collectorId")
            if cid:
                collector_info = {"id": cid}
                # 策略 1：通过 RBAC 用户列表查找（需要管理员权限）
                try:
                    users_resp = caller.list_users(pageNum=1, pageSize=500)
                    if users_resp.status_code == 200:
                        # RBAC 响应格式不同于 data-manager，需要从 message 字段解析
                        msg = users_resp.body.get("message") if isinstance(users_resp.body, dict) else None
                        if isinstance(msg, str):
                            import json as _json
                            try:
                                parsed = _json.loads(msg)
                                if isinstance(parsed, dict):
                                    users = parsed.get("users") or parsed.get("data") or parsed.get("rows") or []
                                elif isinstance(parsed, list):
                                    users = parsed
                                else:
                                    users = []
                            except Exception:
                                users = []
                        elif isinstance(msg, list):
                            users = msg
                        elif isinstance(msg, dict):
                            users = msg.get("users") or msg.get("data") or msg.get("rows") or []
                        else:
                            users = []
                        for u in users:
                            if isinstance(u, dict) and u.get("id") == cid:
                                collector_info["name"] = u.get("username") or u.get("name")
                                collector_info["displayName"] = u.get("displayName")
                                break
                except Exception:
                    pass

                # 策略 2：RBAC 失败时，尝试匹配当前登录用户
                if not collector_info.get("name"):
                    try:
                        me_resp = caller.userinfo()
                        if me_resp.status_code == 200:
                            me_body = me_resp.body
                            me = (
                                me_body.get("metadata") or me_body
                                if isinstance(me_body, dict)
                                else {}
                            )
                            if me.get("id") == cid:
                                collector_info["name"] = me.get("name") or me.get("username")
                                collector_info["displayName"] = me.get("displayName")
                    except Exception:
                        pass

            # ---- 充实作业信息 ----
            job_info = None
            jid = device.get("jobId")
            if jid is not None:
                job_info = {"id": jid}
                try:
                    job_resp = caller.get_job(jobId=int(jid))
                    if job_resp.status_code == 200:
                        job_body = job_resp.body
                        job = (
                            job_body.get("metadata") or job_body
                            if isinstance(job_body, dict)
                            else {}
                        )
                        if isinstance(job, dict):
                            raw_cs = job.get("collectStatus")
                            raw_rs = job.get("reviewStatus")
                            # name 可能为空，使用 taskTitle 兜底
                            job_name = job.get("name") or job.get("taskTitle") or ""
                            job_info["name"] = job_name
                            job_info["description"] = job.get("description")
                            job_info["taskId"] = job.get("taskId")
                            job_info["collectStatus"] = raw_cs
                            job_info["collectStatusLabel"] = _COLLECT_STATUS_MAP.get(raw_cs, "未知")
                            job_info["reviewStatus"] = raw_rs
                            job_info["reviewStatusLabel"] = _REVIEW_STATUS_MAP.get(raw_rs, "未知")
                            progress = job.get("progress") or {}
                            if progress:
                                job_info["progress"] = {
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
                except Exception:
                    pass  # 作业查找失败不影响主流程

            # ---- 判断绑定状态 ----
            has_binding = bool(collector_info or job_info)
            binding_parts = []
            if collector_info:
                name = collector_info.get("name") or collector_info["id"]
                binding_parts.append(f"采集员 {name}")
            if job_info:
                job_name = job_info.get("name") or f"作业#{job_info['id']}"
                binding_parts.append(f"作业「{job_name}」")

            message = (
                f"设备「{device_info.get('deviceName') or device_info.get('deviceCode')}」"
                f"当前绑定：{'、'.join(binding_parts)}"
                if has_binding
                else f"设备「{device_info.get('deviceName') or device_info.get('deviceCode')}」当前未绑定任何采集员或作业"
            )

            return json.dumps(
                {
                    "success": True,
                    "found": True,
                    "device": device_info,
                    "binding": {
                        "collector": collector_info,
                        "job": job_info,
                    },
                    "has_binding": has_binding,
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询设备绑定情况异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

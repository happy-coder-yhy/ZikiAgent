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
        """查询设备详细信息。

        先通过设备名称搜索匹配设备，获取设备编码后再查询完整详情。
        若匹配到多台同名设备，则列出所有匹配项供用户选择。
        也可直接传入 device_code 跳过搜索，直接获取详情。

        Args:
            name: 设备名称（支持模糊匹配），如 "agentTest"、"dunjia"
            device_code: 设备编码，传入后直接查询详情，跳过名称搜索
        """
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
                return json.dumps(
                    {"success": True, "found": True, "device": detail},
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

            # ---- 唯一匹配：直接返回详情 ----
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
                return json.dumps(
                    {"success": True, "found": True, "device": detail},
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


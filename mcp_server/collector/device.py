"""采集员工具 — query_my_device。"""

from __future__ import annotations

import json

from ApiCaller.modules.api_caller import _extract_metadata_items


# 设备状态映射
_STATUS_MAP = {0: "离线", 1: "在线"}
# 设备类别中文标签
_CATEGORY_MAP = {"robot": "真机", "video": "视频"}


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

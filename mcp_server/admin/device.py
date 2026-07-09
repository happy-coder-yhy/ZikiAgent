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

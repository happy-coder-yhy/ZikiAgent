"""项目管理工具 — get_projects, create_project。"""

from __future__ import annotations

import json
from typing import Optional

from ApiCaller.modules.api_caller import _extract_metadata_items


# ---------------------------------------------------------------------------
# 工具注册
# ---------------------------------------------------------------------------

def register_tools(mcp, caller) -> None:
    """注册项目相关工具到 MCP 应用。"""

    @mcp.tool()
    def get_projects(
        name: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 100,
    ) -> str:
        """查询平台项目列表。

        获取当前登录用户可访问的所有项目。
        当用户询问"有哪些项目"、"显示项目列表"等时调用此工具。

        Args:
            name: 按项目名称筛选（可选）
            page_num: 页码，默认 1
            page_size: 每页数量，默认 100
        """
        try:
            resp = caller.list_projects(name=name, pageNum=page_num, pageSize=page_size)
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询失败: HTTP {resp.status_code}"},
                    ensure_ascii=False,
                    indent=2,
                )

            projects = _extract_metadata_items(resp.body)
            summary = [
                {"id": p.get("id"), "name": p.get("name"), "description": p.get("description")}
                for p in projects if isinstance(p, dict)
            ]

            return json.dumps(
                {
                    "success": True,
                    "total": len(projects),
                    "projects": summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询项目列表异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

    @mcp.tool()
    def create_project(
        name: str,
        description: Optional[str] = None,
    ) -> str:
        """创建新项目。

        在平台上创建一个新项目。调用此工具前请先确认：
        - name（项目名称）为必填字段，用户未提供时必须先询问用户
        - description（项目描述）为选填字段，用户未提供时也先询问一下，
          若用户明确表示不需要描述则跳过

        Args:
            name: 项目名称（必填）
            description: 项目描述（选填）
        """
        try:
            resp = caller.create_project(
                name=name,
                description=description,
            )

            data = resp.body
            success = resp.status_code == 200

            return json.dumps(
                {
                    "success": success,
                    "status_code": resp.status_code,
                    "data": data if isinstance(data, dict) else {"message": str(data)},
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"创建项目异常: {e}"},
                ensure_ascii=False,
                indent=2,
            )

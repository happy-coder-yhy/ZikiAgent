"""平台配置查询工具 — get_platform_config。"""

from __future__ import annotations

import json
from typing import Any

from ApiCaller.modules.api_caller import _extract_metadata_items


# ---------------------------------------------------------------------------
# 工具函数：_flatten_tree
# ---------------------------------------------------------------------------

def _flatten_tree(node: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
    """将标签树节点展开为扁平列表。"""
    items: list[dict[str, Any]] = []
    if node.get("name"):
        items.append({
            "id": node.get("id"),
            "name": node.get("name"),
            "parentId": node.get("parentId"),
            "depth": depth,
        })
    for child in (node.get("children") or []):
        if isinstance(child, dict):
            items.extend(_flatten_tree(child, depth + 1))
    return items


# ---------------------------------------------------------------------------
# 工具注册
# ---------------------------------------------------------------------------

def register_tools(mcp, caller) -> None:
    """注册 get_platform_config 工具到 MCP 应用。"""

    @mcp.tool()
    def get_platform_config(page_size: int = 200) -> str:
        """获取平台完整配置信息。

        返回当前登录用户可访问的项目列表、场景标签、设备类型等参考数据。
        在创建任务之前调用此工具，了解可用的项目和场景 ID。

        Args:
            page_size: 分页查询每页数量（默认 200）
        """
        result: dict[str, Any] = {}
        errors: list[str] = []

        def _safe_extract(key: str, fn, *args, **kwargs) -> None:
            try:
                resp = fn(*args, **kwargs)
                if resp.status_code == 200:
                    result[key] = _extract_metadata_items(resp.body)
                else:
                    errors.append(f"{key}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{key}: {e}")

        def _safe_get(key: str, fn, *args, **kwargs) -> None:
            try:
                resp = fn(*args, **kwargs)
                if resp.status_code == 200:
                    result[key] = resp.body
                else:
                    errors.append(f"{key}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{key}: {e}")

        # 获取项目列表
        _safe_extract("projects", caller.list_projects, pageNum=1, pageSize=page_size)
        # 获取任务列表
        _safe_extract("tasks", caller.list_tasks, pageNum=1, pageSize=page_size)
        # 获取场景标签树
        _safe_extract("scene_labels_response", caller.list_scene_labels)
        # 获取设备类型
        _safe_extract("device_types", caller.list_device_types, pageNum=1, pageSize=page_size)
        # 获取 task 分类标签树（含任务用途、任务类型等）
        _safe_extract("task_label_tree", caller.get_label_tree, categoryCode="task")

        # 解析场景标签树为扁平列表
        scene_labels: list[dict[str, Any]] = []
        scene_response = result.get("scene_labels_response", {})
        if isinstance(scene_response, dict):
            scene_labels = _flatten_tree(scene_response)
        elif isinstance(scene_response, list):
            scene_labels = scene_response
            if scene_labels and isinstance(scene_labels[0], dict) and "children" in scene_labels[0]:
                flat: list[dict[str, Any]] = []
                for item in scene_labels:
                    flat.extend(_flatten_tree(item))
                scene_labels = flat
        result.pop("scene_labels_response", None)

        # 从 task 标签树中提取任务用途和任务类型
        task_purposes: list[dict[str, Any]] = []
        task_type_options: list[dict[str, Any]] = []
        task_tree = result.get("task_label_tree", [])
        if isinstance(task_tree, list):
            for node in task_tree:
                if not isinstance(node, dict):
                    continue
                children = node.get("children") or []
                if node.get("code") == "task_stage":
                    task_purposes = [
                        {"id": c.get("id"), "name": c.get("name")}
                        for c in children if isinstance(c, dict) and c.get("name")
                    ]
                elif node.get("code") == "task_type":
                    task_type_options = [
                        {"id": c.get("id"), "name": c.get("name")}
                        for c in children if isinstance(c, dict) and c.get("name")
                    ]
        result.pop("task_label_tree", None)

        output: dict[str, Any] = {
            "projects": result.get("projects", []),
            "tasks": result.get("tasks", []),
            "scene_labels": scene_labels,
            "device_types": result.get("device_types", []),
            "task_purposes": task_purposes,
            "task_type_options": task_type_options,
        }
        if errors:
            output["_warnings"] = errors

        # 提供便捷摘要
        if output["projects"]:
            output["_project_summary"] = [
                {"id": p.get("id"), "name": p.get("name")}
                for p in output["projects"] if isinstance(p, dict)
            ]
        if scene_labels:
            output["_scene_summary"] = [
                {"id": l.get("id"), "name": l.get("name"), "parentId": l.get("parentId")}
                for l in scene_labels if l.get("name")
            ]

        return json.dumps(output, ensure_ascii=False, indent=2)

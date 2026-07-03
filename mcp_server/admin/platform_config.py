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

def _extract_task_purposes(task_tree: list) -> tuple[list[dict], dict[str, int]]:
    """从标签树中提取任务用途列表和 name→ID 快捷映射。"""
    purposes: list[dict] = []
    purpose_map: dict[str, int] = {}
    if isinstance(task_tree, list):
        for node in task_tree:
            if not isinstance(node, dict):
                continue
            children = node.get("children") or []
            if node.get("code") == "task_stage":
                for c in children:
                    if isinstance(c, dict) and c.get("name"):
                        cid = c.get("id")
                        cname = c.get("name")
                        purposes.append({"id": cid, "name": cname})
                        purpose_map[cname] = cid
    return purposes, purpose_map


def register_tools(mcp, caller) -> None:
    """注册平台配置相关工具到 MCP 应用。"""

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
        task_type_options: list[dict[str, Any]] = []
        task_tree = result.get("task_label_tree", [])
        task_purposes, purpose_map = _extract_task_purposes(task_tree)
        if isinstance(task_tree, list):
            for node in task_tree:
                if not isinstance(node, dict):
                    continue
                children = node.get("children") or []
                if node.get("code") == "task_type":
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
        if purpose_map:
            output["_purpose_summary"] = purpose_map  # {"仿真评测": 209, "正式采集": 206, ...}

        return json.dumps(output, ensure_ascii=False, indent=2)

    @mcp.tool()
    def get_scene(name: str) -> str:
        """根据名称快速查询场景 ID（主场景或子场景）。

        通过一次 API 调用获取场景标签树，按名称匹配并返回场景 ID。
        支持查询主场景（如"居家"）和子场景（如"整理"）。
        如果子场景在多个主场景下存在同名，会全部列出并注明所属主场景。

        Args:
            name: 场景名称，如 "居家"、"超市"、"整理"、"厨房" 等
        """
        try:
            resp = caller.list_scene_labels()
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询场景标签失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )

            body = resp.body
            tree = body
            if isinstance(body, dict):
                tree = body.get("metadata") or body.get("data") or body
            if isinstance(tree, dict):
                tree = [tree]

            # Build flat list with parent context
            all_scenes: list[dict] = []
            main_scene_map: dict[str, int] = {}

            def walk_nodes(nodes, parent_name=None, parent_id=None) -> None:
                if not isinstance(nodes, list):
                    return
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    node_id = node.get("id")
                    node_name = node.get("name")
                    children = node.get("children") or []

                    if node_name:
                        all_scenes.append({
                            "id": node_id,
                            "name": node_name,
                            "parentId": parent_id,
                            "parentName": parent_name,
                            "depth": 0 if parent_id is None else (1 if parent_name else 0),
                        })
                        if parent_id is None and node_id is not None:
                            main_scene_map[node_name] = node_id

                    if children:
                        walk_nodes(children, parent_name=node_name, parent_id=node_id)

            walk_nodes(tree)

            # Match by name
            matches = [s for s in all_scenes if s.get("name") == name]

            if not matches:
                similar = sorted(set(
                    s["name"] for s in all_scenes
                    if s.get("name") and (name in s["name"] or s["name"] in name)
                ))
                return json.dumps({
                    "success": False,
                    "error": f"未找到场景「{name}」",
                    "main_scenes": main_scene_map,
                    "similar": similar[:20],
                }, ensure_ascii=False, indent=2)

            result: dict = {
                "success": True,
                "name": name,
                "count": len(matches),
                "matches": matches,
                "main_scenes": main_scene_map,
            }
            if len(matches) > 1:
                result["ambiguous"] = True
                result["message"] = (
                    f"找到 {len(matches)} 个同名场景，请根据 parentName 确定正确的场景 ID"
                )

            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询异常: {e}"},
                ensure_ascii=False, indent=2,
            )

    @mcp.tool()
    def get_task_purpose(name: str) -> str:
        """根据名称查询任务用途 ID。

        快速查询任务用途对应的数字 ID，只需一次 API 调用。
        例如 get_task_purpose("仿真评测") 返回 {"仿真评测": 209}。

        Args:
            name: 任务用途名称，如 "仿真评测"、"正式采集"、"开发测试"
        """
        try:
            resp = caller.get_label_tree(categoryCode="task")
            if resp.status_code != 200:
                return json.dumps(
                    {"success": False, "error": f"查询标签树失败: HTTP {resp.status_code}"},
                    ensure_ascii=False, indent=2,
                )
            tree = resp.body
            if isinstance(tree, dict):
                tree = tree.get("metadata") or tree
            if not isinstance(tree, list):
                tree = [tree]

            _, purpose_map = _extract_task_purposes(tree)

            if name in purpose_map:
                return json.dumps(
                    {
                        "success": True,
                        "name": name,
                        "id": purpose_map[name],
                        "summary": purpose_map,  # 附上全量映射方便参考
                    },
                    ensure_ascii=False, indent=2,
                )

            # 模糊匹配提示
            similar = [k for k in purpose_map if name in k or k in name]
            result = {
                "success": False,
                "error": f"未找到用途名称「{name}」",
                "available_purposes": purpose_map,
            }
            if similar:
                result["similar"] = similar
            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"查询异常: {e}"},
                ensure_ascii=False, indent=2,
            )

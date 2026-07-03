"""Ziki MCP Server — FastMCP 应用创建与工具注册。

通过 MCP 协议向 LLM 暴露 Zata 平台工具，让模型能够：
1. 查询平台配置信息（项目、场景标签等）
2. 创建场景采集任务
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 加载 .env 文件
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    # 从项目根目录加载 .env
    _project_root = Path(__file__).parent.parent
    _env_file = _project_root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv 未安装，使用系统环境变量

# ---------------------------------------------------------------------------
# 检查 MCP SDK 是否可用
# ---------------------------------------------------------------------------
_MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP

    _MCP_AVAILABLE = True
except ImportError:
    FastMCP = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 导入 Zata API 调用器
# ---------------------------------------------------------------------------
from ApiCaller.modules.api_caller import (
    APICallerConfig,
    ZataAPICaller,
)


# ---------------------------------------------------------------------------
# 凭证与调用器初始化
# ---------------------------------------------------------------------------

def _get_env_or_exit(key: str) -> str:
    """获取环境变量，缺失则退出。"""
    value = os.environ.get(key)
    if not value:
        print(f"FATAL: 环境变量 {key} 未设置", file=sys.stderr)
        sys.exit(1)
    return value


def _build_caller() -> ZataAPICaller:
    """从环境变量构建并认证 ZataAPICaller。"""
    base_url = os.environ.get("ZATA_BASE_URL")
    username = os.environ.get("ZATA_USERNAME")
    password = os.environ.get("ZATA_PASSWORD")
    organization = os.environ.get("ZATA_ORGANIZATION", "agent")

    if not base_url:
        print("FATAL: 环境变量 ZATA_BASE_URL 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    if not username:
        print("FATAL: 环境变量 ZATA_USERNAME 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("FATAL: 环境变量 ZATA_PASSWORD 未设置，请检查 .env 文件", file=sys.stderr)
        sys.exit(1)

    config = APICallerConfig(base_url=base_url)
    caller = ZataAPICaller(config)
    caller.login(
        username=username,
        password=password,
        organization=organization,
    )
    return caller


def _flatten_tree(node: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
    """将标签树节点展开为扁平列表。"""
    items = []
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
# 枚举值映射（短程/长程 → int、简单/普通/困难 → int）
# ---------------------------------------------------------------------------

_TASK_TYPE_MAP: dict[str, int] = {
    "短程": 305,
    "长程": 304,
}

_DIFFICULTY_MAP: dict[str, int] = {
    "简单": 1,
    "普通": 2,
    "困难": 3,
}

# ---------------------------------------------------------------------------
# FastMCP 应用工厂
# ---------------------------------------------------------------------------

def create_app(caller: Optional[ZataAPICaller] = None) -> "FastMCP":
    """创建 FastMCP 实例并注册所有工具。

    Args:
        caller: 可选，已经认证的 ZataAPICaller。为 None 时从环境变量创建。

    Returns:
        FastMCP: 配置好的 MCP 应用实例。
    """
    if not _MCP_AVAILABLE:
        raise ImportError(
            "MCP server 需要 'mcp' 包。\n"
            f"安装命令: {sys.executable} -m pip install 'mcp'"
        )

    if caller is None:
        caller = _build_caller()

    mcp = FastMCP(
        "ziki-platform",
        instructions=(
            "Ziki 数据采集平台工具。请严格按照以下流程操作：\n\n"
            "1. 创建任务前，先调用 get_platform_config 获取可用的项目、场景、设备类型等参考信息。\n"
            "2. 调用 create_scene_task 创建场景采集任务，该工具有以下必填字段：\n"
            "   - project_id / scene_id / title（基本字段）\n"
            "   - task_type（任务类型：短程 / 长程，通过 get_platform_config 返回的 task_type_options 查看可用的类型及其ID）\n"
            "   - task_purpose_id（任务用途ID：通过 get_platform_config 返回的 task_purposes 列表查看用途名称及对应ID）\n"
            "   - difficulty（难度：简单 / 普通 / 困难）\n"
            "   - device_type_id（设备类型ID：通过 get_platform_config 返回的 device_types 列表查看）\n"
            "3. 重要：当用户指令缺少上述必填字段的值时，你必须主动逐一向用户询问缺失的字段值，"
            "直至所有必填字段信息完整，再调用 create_scene_task 创建任务。\n"
            "   例如用户只说\"创建场景任务\"而不提供任何细节，你需要逐一询问：项目、场景、"
            "任务标题、任务类型（短程/长程）、任务用途、难度、设备类型。\n"
        ),
    )

    # -------------------------------------------------------------------
    # 工具: get_platform_config
    # -------------------------------------------------------------------

    @mcp.tool()
    def get_platform_config(page_size: int = 200) -> str:
        """获取平台完整配置信息。

        返回当前登录用户可访问的项目列表、场景标签、设备类型等参考数据。
        在创建任务之前调用此工具，了解可用的项目和场景 ID。

        Args:
            page_size: 分页查询每页数量（默认 200）
        """
        from ApiCaller.modules.api_caller import _extract_metadata_items

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
        scene_labels = []
        scene_response = result.get("scene_labels_response", {})
        if isinstance(scene_response, dict):
            scene_labels = _flatten_tree(scene_response)
        elif isinstance(scene_response, list):
            scene_labels = scene_response
            if scene_labels and isinstance(scene_labels[0], dict) and "children" in scene_labels[0]:
                flat = []
                for item in scene_labels:
                    flat.extend(_flatten_tree(item))
                scene_labels = flat
        if "scene_labels_response" in result:
            del result["scene_labels_response"]

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
        if "task_label_tree" in result:
            del result["task_label_tree"]

        output = {
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

    # -------------------------------------------------------------------
    # 工具: create_scene_task
    # -------------------------------------------------------------------

    @mcp.tool()
    def create_scene_task(
        project_id: int,
        scene_id: int,
        title: str,
        task_type: str,
        task_purpose_id: int,
        difficulty: str,
        device_type_id: int,
        description: Optional[str] = None,
        collect_method: str = "web_video",
        collect_mode_id: Optional[int] = None,
        collect_scheme_id: Optional[int] = None,
        space_ids: Optional[list[int]] = None,
        custom_label_ids: Optional[list[int]] = None,
        recognition_enabled: Optional[bool] = None,
        video_quality: Optional[int] = None,
    ) -> str:
        """创建场景采集任务。

        在指定项目的指定场景下创建一个场景视频采集任务。
        先调用 get_platform_config 获取可用的 project_id、scene_id、device_type_id 和 task_purpose_id。
        当用户没有提供以下必填信息时，请逐一询问用户，直至全部填写完整再调用此工具：

        **必填字段说明：**
        - task_type (str): 任务类型。"短程" 或 "长程"
        - task_purpose_id (int): 任务用途ID。可通过 get_platform_config 获取可用的任务用途标签列表及其ID
        - difficulty (str): 任务难度。"简单"、"普通" 或 "困难"
        - device_type_id (int): 设备类型ID。可通过 get_platform_config 获取可用的设备类型列表及其ID

        Args:
            project_id: 项目 ID（通过 get_platform_config 获取）
            scene_id: 场景标签 ID（通过 get_platform_config 获取）
            title: 任务标题
            task_type: 任务类型 — "短程" 或 "长程"
            task_purpose_id: 任务用途ID — 通过 get_platform_config 的 task_purposes 列表获取
            difficulty: 任务难度 — "简单"、"普通" 或 "困难"
            device_type_id: 设备类型ID — 通过 get_platform_config 的 device_types 列表获取
            description: 任务描述（可选）
            collect_method: 采集方式，默认 "web_video"
            collect_mode_id: 采集模式标签 ID（可选）
            collect_scheme_id: 采集方案标签 ID（可选）
            space_ids: 空间标签 ID 列表（可选）
            custom_label_ids: 自定义标签 ID 列表（可选）
            recognition_enabled: 是否启用 AI 识别（可选）
            video_quality: 视频画质设置（可选）
        """
        # 校验并映射 task_type
        task_type_val = _TASK_TYPE_MAP.get(task_type)
        if task_type_val is None:
            return json.dumps(
                {
                    "success": False,
                    "error": f"无效的任务类型：'{task_type}'，请选择 '短程' 或 '长程'",
                },
                ensure_ascii=False,
                indent=2,
            )

        # 校验并映射 difficulty
        difficulty_val = _DIFFICULTY_MAP.get(difficulty)
        if difficulty_val is None:
            return json.dumps(
                {
                    "success": False,
                    "error": f"无效的难度：'{difficulty}'，请选择 '简单'、'普通' 或 '困难'",
                },
                ensure_ascii=False,
                indent=2,
            )

        try:
            response = caller.create_scene_task(
                projectId=project_id,
                sceneId=scene_id,
                title=title,
                description=description,
                collectMethod=collect_method,
                taskPurposeId=task_purpose_id,
                taskType=task_type_val,
                difficulty=difficulty_val,
                deviceTypeId=device_type_id,
                collectModeId=collect_mode_id,
                collectSchemeId=collect_scheme_id,
                spaceIds=space_ids,
                customLabelIds=custom_label_ids,
                recognitionEnabled=recognition_enabled,
                videoQuality=video_quality,
            )

            return json.dumps(
                {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.body,
                },
                ensure_ascii=False,
                indent=2,
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": str(e)},
                ensure_ascii=False,
                indent=2,
            )

    return mcp


# 模块级单例（供 __main__.py 和外部导入使用）
mcp = create_app()

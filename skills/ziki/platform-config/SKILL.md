---
name: platform-config
description: >
  Queries Zata platform live configuration — projects, scene labels, device types,
  task purposes, and task type options — via the `get_platform_config` MCP tool.
  Always invoke this before creating tasks to discover the correct IDs.
tags: [zata, ziki, platform, discovery, reference]
triggers:
  - user asks "有哪些项目/场景/设备" / "show projects/scenes/devices"
  - user wants to see platform configuration or available options
  - before creating a scene task, to look up project IDs, scene IDs, etc.
  - user asks about task purposes or task type options
---

# Platform Config / 平台配置查询

## 用途

查询 Zata 平台的完整配置信息，包括：

- **项目列表** — 当前登录用户可访问的项目（id + name）
- **场景标签** — 可用的场景标签及其层级关系
- **设备类型** — 可用的采集设备类型
- **任务用途** — 正式采集、开发测试等
- **任务类型选项** — 短程 / 长程

## 调用方式

通过 MCP 工具 `get_platform_config` 获取：

```
Tool: get_platform_config
Params:
  page_size: int (optional, default 200)
```

### 返回结果示例

```json
{
  "projects": [{"id": 1, "name": "项目A"}, ...],
  "scene_labels": [{"id": 10, "name": "超市", "parentId": null, "depth": 0}, ...],
  "device_types": [...],
  "task_purposes": [{"id": 206, "name": "正式采集"}, ...],
  "task_type_options": [{"id": 304, "name": "长程"}, {"id": 305, "name": "短程"}],
  "_project_summary": [{"id": 1, "name": "项目A"}, ...],
  "_scene_summary": [{"id": 10, "name": "超市", "parentId": null}, ...]
}
```

## 使用场景

- 用户问"现在平台上有哪些项目？" → 调用 `get_platform_config`，返回 `_project_summary`
- 用户想创建任务但不确定 scene_id → 先调用 `get_platform_config` 查看 `scene_labels`
- 用户说"帮我看看有哪些设备类型" → 调用 `get_platform_config`，返回 `device_types`

## 注意

- 此工具是**只读查询**，不会修改任何数据
- 创建任务前**务必**调用此工具获取最新的平台数据，不要依赖缓存
- 如果部分接口失败（如标签树接口异常），结果中会包含 `_warnings` 数组，不影响其他数据

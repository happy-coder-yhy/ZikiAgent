---
name: scene-task
description: >
  Creates scene collection tasks (场景采集任务) on the Zata platform via the
  `create_scene_task` MCP tool. Always query platform config first via
  `get_platform_config` to discover required IDs (project_id, scene_id, etc.).
tags: [zata, ziki, scene-task, collection, task-creation]
triggers:
  - user says "创建场景采集任务" / "create a scene task"
  - user says "创建采集任务" / "create a collection task"
  - user wants to add a collection task under a project
  - user mentions a scene and project together for task creation
---

# Scene Task / 场景采集任务创建

## 用途

在 Zata 平台的指定项目下创建场景采集任务。使用 `create_scene_task` MCP 工具完成。

## 前置步骤

**在执行创建前，必须先调用 `get_platform_config` 获取以下 ID：**

| 参数 | 来源 | 说明 |
|------|------|------|
| `project_id` | `get_platform_config` → `projects` | 目标项目的数字 ID |
| `scene_id` | `get_platform_config` → `scene_labels` | 场景标签的数字 ID |
| `task_purpose_id` | `get_platform_config` → `task_purposes` | 任务用途 ID |
| `device_type_id` | `get_platform_config` → `device_types` | 设备类型 ID |
| `task_type` | 直接由用户指定 | "短程" 或 "长程" |
| `difficulty` | 直接由用户指定 | "简单"、"普通" 或 "困难" |

## 调用方式

```
Tool: create_scene_task
Required Params:
  - project_id: int       — 项目 ID（来自 get_platform_config）
  - scene_id: int         — 场景标签 ID（来自 get_platform_config）
  - title: string         — 任务标题
  - task_type: string     — "短程" 或 "长程"
  - task_purpose_id: int  — 任务用途 ID（来自 get_platform_config）
  - difficulty: string    — "简单"、"普通" 或 "困难"
  - device_type_id: int   — 设备类型 ID（来自 get_platform_config）
Optional Params:
  - description: string           — 任务描述
  - collect_method: string        — 采集方式，默认 "web_video"
  - collect_mode_id: int          — 采集模式标签 ID
  - collect_scheme_id: int        — 采集方案标签 ID
  - space_ids: int[]              — 空间标签 ID 列表
  - custom_label_ids: int[]       — 自定义标签 ID 列表
  - recognition_enabled: bool     — 是否启用 AI 识别
  - video_quality: int            — 视频画质
```

## 工作流

1. 用户表达创建意图（如"在项目X下创建场景采集任务"）
2. 调用 `get_platform_config` 获取项目列表、场景标签等参考数据
3. 逐一确认必填字段：
   - 用户未提供项目名 → 展示可用项目列表，询问用户选择哪个
   - 用户未提供场景 → 展示可用场景列表，询问用户
   - 用户未提供标题 → 根据场景自动生成或询问用户
   - 用户未提供 task_type → 询问"短程还是长程？"
   - 用户未提供 task_purpose → 展示可用用途列表，询问用户
   - 用户未提供 difficulty → 询问"简单、普通还是困难？"
   - 用户未提供 device_type → 展示可用设备类型列表，询问用户
4. 组装参数后调用 `create_scene_task`
5. 返回创建结果给用户

## 注意

- **所有 ID 必须从 `get_platform_config` 获取**，不要硬编码或猜测
- task_type 只接受 "短程" 或 "长程"，其他值会报错
- difficulty 只接受 "简单"、"普通" 或 "困难"，其他值会报错
- 创建成功后返回的 data 中包含新任务的 id

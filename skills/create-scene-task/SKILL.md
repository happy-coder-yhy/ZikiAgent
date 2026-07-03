---
name: "create-scene-task"
description: "Creates a scene collection task on the Zata platform. Invoke when the user asks to create a scene task, scene collection task, or a lightweight task with collectMethod=web_video and taskCategory=scene."
---

# Create Scene Task

This skill creates a **scene collection task** (`taskCategory=scene`, `collectMethod=web_video`) via `ZataAPICaller.create_scene_task(...)`.

## Input Schema

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `sceneId` | `integer` | 场景标签 ID。如用户提供场景名称，需先通过 `sync_platform_configuration()` 快照将名称解析为 ID。 |
| `title` | `string` | 任务标题。 |
| `projectId` | `integer` | 项目 ID。如用户未提供，需尝试从平台配置快照中获取默认/首个项目。 |

### Optional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `description` | `string` | 任务描述。 |
| `taskPurposeId` | `integer` | 任务用途标签 ID。 |
| `collectModeId` | `integer` | 采集模式标签 ID。 |
| `collectSchemeId` | `integer` | 采集方案标签 ID。 |
| `spaceIds` | `integer[]` | 空间标签 ID 列表。 |
| `customLabelIds` | `integer[]` | 自定义标签 ID 列表。 |
| `collectors` | `TaskUserReq[]` | 采集员列表。 |
| `auditors` | `TaskUserReq[]` | 审核员列表。 |
| `planCollectCount` | `integer` | 计划采集数量。 |
| `videoQuality` | `integer` | 视频质量：1 无损（默认），2 超清，3 高清，4 流畅。 |

### Fixed Parameters (Set by Code)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `collectMethod` | `"web_video"` | 采集方式，由 `create_scene_task` 默认传入。 |
| `taskCategory` | `"scene"` | 任务分类，由 `create_scene_task` 固定传入。 |

## Execution Steps

1. **Receive user input** (natural language or structured params).
2. **Validate required params**: `sceneId`, `title`, `projectId` must be present after resolution.
3. **Name → ID resolution** (if names are provided instead of IDs):
   - Call `caller.sync_platform_configuration()` to get platform snapshot.
   - Resolve `sceneName` → `sceneId` from `labels` where `categoryCode == "scene"`.
   - Resolve `projectName` → `projectId` from `projects`.
   - Resolve `spaceNames` → `spaceIds` from `labels` where `categoryCode == "space"`.
4. **Build request body** using `_build_json_body(...)` with all provided optional params.
5. **Call API**: `ZataAPICaller.create_scene_task(sceneId, title, projectId, **kwargs)`.
6. **Parse response**:
   - Success: extract `taskId` from response body.
   - Failure: return error code and message.
7. **Return formatted result** to the agent.

## Output Schema

### Success

```yaml
taskId: integer
title: string
taskCategory: "scene"
projectId: integer
collectMethod: "web_video"
message: "Scene task created successfully"
```

### Failure

```yaml
error_code: string
error_message: string
missing_params: string[]   # List of missing required parameters, if any
```

## Examples

### Example 1: Minimal Scene Task

**User Input:**
> 创建一个商超收银区的场景任务，标题叫"收银区视频采集"

**Resolved Params:**
- `sceneId`: 45 (resolved from "商超收银区")
- `title`: "收银区视频采集"
- `projectId`: 123 (default project)

**API Call:**
```python
caller.create_scene_task(
    sceneId=45,
    title="收银区视频采集",
    projectId=123
)
```

### Example 2: Full Scene Task

**User Input:**
> 在项目"测试项目"下创建一个场景任务，场景是"商超收银区"，标题"收银区多角度采集"，计划采集100条，空间包含"收银台"和"货架区"，视频质量高清

**Resolved Params:**
- `projectId`: 123 (resolved from "测试项目")
- `sceneId`: 45 (resolved from "商超收银区")
- `title`: "收银区多角度采集"
- `planCollectCount`: 100
- `spaceIds`: [12, 15] (resolved from "收银台" and "货架区")
- `videoQuality`: 3

**API Call:**
```python
caller.create_scene_task(
    sceneId=45,
    title="收银区多角度采集",
    projectId=123,
    planCollectCount=100,
    spaceIds=[12, 15],
    videoQuality=3
)
```

## Notes

- Scene tasks do **not** send `actionSteps`, `initialState`, or `objectBindings`. These fields are ignored by the platform for non-strict tasks.
- After task creation, jobs may need to be created separately via `create_jobs(...)` if the workflow requires them.
- All API calls must be serialized with >2s gap between consecutive requests.
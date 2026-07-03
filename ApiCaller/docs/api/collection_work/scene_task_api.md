# Scene Task API / 场景采集任务 API

场景采集任务（Scene Collection Task）只约束采集场景等少量配置，不要求完整动作步骤和严格任务定义。场景任务使用 `collectMethod=web_video` 和 `taskCategory=scene`。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询 Task 列表 | `GET` | `/api/zata-manager/tasks` 或 `/api/zata-manager/projects/{id}/tasks` | `list_tasks(...)` |
| 查询 Task 详情 | `GET` | `/api/zata-manager/tasks/{id}` | `get_task(taskId)` |
| 创建场景 Task | `POST` | `/api/zata-manager/projects/{projectId}/tasks` | `create_scene_task(...)` |
| 更新 Task | `PUT` | `/api/zata-manager/tasks/{id}` | `update_task(...)` |
| 更新 Task 并保留 Job | `PUT` | `/api/zata-manager/tasks/{id}/keep-jobs` | `update_task_keep_jobs(...)` |
| 删除 Task | `DELETE` | `/api/zata-manager/tasks/{id}` | `delete_task(taskId)` |
| 发布/取消发布 Task | `POST` | `/api/zata-manager/tasks/{id}/publish`, `/unpublish` | `publish_task(...)`, `unpublish_task(...)` |
| 归档/取消归档 Task | `POST` | `/api/zata-manager/tasks/{id}/archive`, `/unarchive` | `archive_task(...)`, `unarchive_task(...)` |

## Fields / 字段

场景任务的输入应比严格任务更轻量。当前 OpenAPI 将 `collectMethod`、`sceneId`、`taskCategory` 和 `title` 标记为创建 Task 的必填字段。`create_scene_task(...)` 会固定发送 `taskCategory="scene"`，默认发送 `collectMethod="web_video"`。

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `projectId` | `integer` | Project 范围创建时必填 | 已验证的 Collection Project | 已创建或已选择的 Project ID。 |
| `collectMethod` | `string` | 是 | wrapper 默认值 | `create_scene_task(...)` 默认发送 `web_video`。 |
| `taskCategory` | `string` | 是 | wrapper 固定值 | `create_scene_task(...)` 固定发送 `scene`。 |
| `sceneId` | `integer` | 是 | 标签池 | 核心场景标签 ID。 |
| `title` | `string` | 是 | 调用方输入或命名模板 | 任务标题。 |
| `description` | `string` | 否 | 调用方输入或模板 | 任务描述。 |
| `taskPurposeId`, `collectModeId`, `collectSchemeId` | `integer` | 按业务需要 | 标签池 | 任务用途、采集模式、采集方案。 |
| `spaceIds`, `customLabelIds` | `integer[]` | 否 | 标签池 | 空间和自定义标签。 |
| `collectors`, `auditors` | `TaskUserReq[]` | 否 | RBAC 用户候选 | 采集员和审核员。 |
| `planCollectCount` | `integer` | 按业务需要 | 本地计划 | 计划采集数量。 |

场景任务通常不要求 `initialState`、`actionSteps` 和完整 `objectBindings`。根据 OpenAPI 说明，非 strict 任务不会保存动作步骤；这些字段不应由 `create_scene_task(...)` 发送。

场景任务创建后通常还需要额外创建 Job，详见 [job_api.md](job_api.md)。

## Examples / 示例

创建场景采集任务：

- Request: [examples/create_scene_task.request.example.json](examples/create_scene_task.request.example.json)
- Response: [examples/create_scene_task.response.example.json](examples/create_scene_task.response.example.json)

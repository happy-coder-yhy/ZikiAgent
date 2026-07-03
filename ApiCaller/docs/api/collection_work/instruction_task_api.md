# Instruction Task API / 指令采集任务 API

指令采集任务（Instruction Collection Task）使用 `collectMethod=web_video` 和 `taskCategory=instruction`。它面向互联网视频或其他 ego 设备采集流程，通过 `promptInstruction` 指定采集提示，不保存严格任务的动作步骤。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询 Task 列表 | `GET` | `/api/zata-manager/tasks` 或 `/api/zata-manager/projects/{id}/tasks` | `list_tasks(...)` |
| 查询 Task 详情 | `GET` | `/api/zata-manager/tasks/{id}` | `get_task(taskId)` |
| 创建指令 Task | `POST` | `/api/zata-manager/projects/{projectId}/tasks` | `create_instruction_task(...)` |
| 更新 Task | `PUT` | `/api/zata-manager/tasks/{id}` | `update_task(...)` |
| 更新 Task 并保留 Job | `PUT` | `/api/zata-manager/tasks/{id}/keep-jobs` | `update_task_keep_jobs(...)` |
| 删除 Task | `DELETE` | `/api/zata-manager/tasks/{id}` | `delete_task(taskId)` |
| 发布/取消发布 Task | `POST` | `/api/zata-manager/tasks/{id}/publish`, `/unpublish` | `publish_task(...)`, `unpublish_task(...)` |
| 归档/取消归档 Task | `POST` | `/api/zata-manager/tasks/{id}/archive`, `/unarchive` | `archive_task(...)`, `unarchive_task(...)` |

## Fields / 字段

当前 OpenAPI 将 `collectMethod`、`sceneId`、`taskCategory` 和 `title` 标记为创建 Task 的必填字段。`create_instruction_task(...)` 固定发送 `taskCategory="instruction"` 和 `collectMethod="web_video"`。

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `projectId` | `integer` | Project 范围创建时必填 | 已验证的 Collection Project | 已创建或已选择的 Project ID。 |
| `collectMethod` | `string` | 是 | wrapper 固定值 | `create_instruction_task(...)` 固定发送 `web_video`。 |
| `taskCategory` | `string` | 是 | wrapper 固定值 | `create_instruction_task(...)` 固定发送 `instruction`。 |
| `sceneId` | `integer` | 是 | 标签池 | 核心场景标签 ID。 |
| `title` | `string` | 是 | 调用方输入或命名模板 | 任务标题。 |
| `promptInstruction` | `string` | 是 | 调用方输入或模板 | 指令任务提示文本。 |
| `description` | `string` | 否 | 调用方输入或模板 | 任务描述。 |
| `taskPurposeId`, `collectModeId`, `collectSchemeId` | `integer` | 按业务需要 | 标签池 | 任务用途、采集模式、采集方案。 |
| `spaceId`, `spaceIds`, `customLabelIds` | integer / `integer[]` | 否 | 标签池或空间资产 | 空间和自定义标签。 |
| `collectors`, `auditors` | `TaskUserReq[]` | 否 | RBAC 用户候选 | 采集员和审核员。 |
| `planCollectCount` | `integer` | 按业务需要 | 本地计划 | 计划采集数量。 |
| `recognitionEnabled`, `aiCapabilities` | boolean / `string[]` | 按业务需要 | 本地计划 | 启用模型处理时需要提供 AI 能力配置。 |

Instruction 任务不发送 `initialState`、`actionSteps` 和完整 `objectBindings`。根据 OpenAPI 说明，非 strict 任务不会保存动作步骤。

## Examples / 示例

创建指令采集任务：

- Request: [examples/create_instruction_task.request.example.json](examples/create_instruction_task.request.example.json)
- Response: [examples/create_instruction_task.response.example.json](examples/create_instruction_task.response.example.json)

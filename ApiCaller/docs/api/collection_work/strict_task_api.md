# Strict Task API / 严格采集任务 API

严格采集任务（Strict Collection Task）会明确设备类型、初始状态、动作步骤、物品绑定和采集约束。`collectMethod=robot` 表示真机采集，只允许创建严格任务；`collectMethod=web_video` 也可以创建严格任务。

## Creation Modes / 创建方式

严格任务有两种创建方式：

1. 模板创建：通过场景任务库模板创建，调用方额外提供项目、采集用途、设备、数量等配置。
2. 直接创建：调用方完整提供严格任务定义，包括场景、设备、初始状态、动作步骤和物品绑定。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 | 当前状态 |
| --- | --- | --- | --- | --- |
| 查询 Task 列表 | `GET` | `/api/zata-manager/tasks` 或 `/api/zata-manager/projects/{id}/tasks` | `list_tasks(...)` | 已封装 |
| 查询 Task 详情 | `GET` | `/api/zata-manager/tasks/{id}` | `get_task(taskId)` | 已封装 |
| 直接创建 Task | `POST` | `/api/zata-manager/projects/{projectId}/tasks` | `create_strict_task(...)` | 已封装 |
| 模板创建严格 Task | `POST` | `/api/zata-manager/projects/{projectId}/tasks/from-template` | `create_strict_task_from_template(...)` | 已封装 |
| 更新 Task | `PUT` | `/api/zata-manager/tasks/{id}` | `update_task(...)` | 已封装 |
| 更新 Task 并保留 Job | `PUT` | `/api/zata-manager/tasks/{id}/keep-jobs` | `update_task_keep_jobs(...)` | 已封装 |
| 删除 Task | `DELETE` | `/api/zata-manager/tasks/{id}` | `delete_task(taskId)` | 已封装 |
| 发布/取消发布 Task | `POST` | `/api/zata-manager/tasks/{id}/publish`, `/unpublish` | `publish_task(...)`, `unpublish_task(...)` | 已封装 |
| 归档/取消归档 Task | `POST` | `/api/zata-manager/tasks/{id}/archive`, `/unarchive` | `archive_task(...)`, `unarchive_task(...)` | 已封装 |

## Direct Creation Fields / 直接创建字段

当前 OpenAPI 将 `collectMethod`、`sceneId`、`taskCategory` 和 `title` 标记为创建 Task 的必填字段。`create_strict_task(...)` 会固定发送 `taskCategory="strict"`，默认发送 `collectMethod="robot"`。严格任务通常还需要更多配置项。

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `projectId` | `integer` | Project 范围创建时必填 | 已验证的 Collection Project | 已创建或已选择的 Project ID。 |
| `collectMethod` | `string` | 是 | wrapper 默认值或调用方输入 | `create_strict_task(...)` 默认发送 `robot`；OpenAPI 也允许 `web_video` 创建 strict。 |
| `taskCategory` | `string` | 是 | wrapper 固定值 | `create_strict_task(...)` 固定发送 `strict`。 |
| `sceneId` | `integer` | 是 | 标签池 | 核心场景标签 ID。 |
| `title` | `string` | 是 | 调用方输入或命名模板 | 任务标题。 |
| `deviceTypeId` | `integer` | 通常需要 | 设备配置 | 设备类型 ID。 |
| `taskPurposeId`, `collectModeId`, `collectSchemeId`, `taskType` | `integer` | 按业务需要 | 标签池 | 任务用途、采集模式、采集方案、任务类型。 |
| `initialState` | `string` | 通常需要 | 本地模板 | 初始状态，可包含物品占位符。 |
| `actionSteps` | `TaskActionStepReq[]` | 通常需要 | 本地模板和标签池 | 动作步骤。 |
| `objectBindings` | `TaskObjectBindingReq[]` | 通常需要 | 物品目录/物品池 | 物品占位符绑定。 |
| `collectors`, `auditors` | `TaskUserReq[]` | 否 | RBAC 用户候选 | 采集员和审核员。 |
| `planCollectCount`, `normalPlanCount`, `abnormalPlanCount`, `abnormalRatio` | number | 按业务需要 | 本地计划 | 计划采集数量与比例。 |
| `duration`, `minDuration`, `countdownSeconds`, `difficulty`, `videoQuality` | number | 按业务需要 | 本地计划 | 时长、倒计时、难度和视频质量。 |

## Template Creation Fields / 模板创建字段

模板创建严格任务时，场景、初始状态、动作步骤和物品绑定主要来自场景任务库模板。调用方仍需提供项目、采集用途、采集设备、计划数量等运行参数。

典型字段包括：

- `projectId`
- `collectMethod`
- `taskPurposeId`
- `collectModeId`
- `collectSchemeId`
- `deviceTypeId`
- `collectors`
- `auditors`
- `duration`
- `minDuration`
- `planCollectCount`
- `templateItems[].templateId`
- `templateItems[].jobCount`
- `templateItems[].jobPlanCollectCount`

模板创建可能自动生成对应 Job，因此调用方不能假设所有严格任务都需要后续手动创建 Job。创建后应查询 Task 下 Job 列表确认结果。

## Examples / 示例

直接创建严格采集任务：

- Request: [examples/create_strict_task_direct.request.example.json](examples/create_strict_task_direct.request.example.json)
- Response: [examples/create_strict_task_direct.response.example.json](examples/create_strict_task_direct.response.example.json)

从场景任务库模板创建严格采集任务：

- Request: [examples/create_strict_task_from_template.request.example.json](examples/create_strict_task_from_template.request.example.json)
- Response: [examples/create_strict_task_from_template.response.example.json](examples/create_strict_task_from_template.response.example.json)

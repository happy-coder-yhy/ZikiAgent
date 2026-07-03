# Job API / 采集作业 API

采集作业（Collection Job）是 Task 下可被采集员领取和完成的原子作业。Job 不能脱离 Task 单独创建。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询 Task 下的 Job | `GET` | `/api/zata-manager/tasks/{id}/jobs` | `list_jobs(taskId, pageNum, pageSize)` |
| 在 Task 下创建 Job | `POST` | `/api/zata-manager/tasks/{id}/jobs` | `create_jobs(taskId, jobs)` |
| 查询 Job 详情 | `GET` | `/api/zata-manager/jobs/{id}` | `get_job(jobId)` |
| 更新 Job | `PUT` | `/api/zata-manager/jobs/{id}` | `update_job(...)` |
| 批量删除 Job | `POST` | `/api/zata-manager/jobs/batch-delete` | `delete_jobs(ids)` |

## Fields / 字段

Job 创建接口是批量接口：`create_jobs(taskId, jobs)` 会发送 `jobs` 数组。OpenAPI 将 `requiredRepeat` 标记为 `CreateJobReq` 的最小必填字段。

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `taskId` | `integer` | 是 | 已创建或已选择的 Task | 路径参数，不应手写硬编码。 |
| `jobs[].requiredRepeat` | `integer` | 是 | 本地计划或模板 | 需要完成的采集次数。 |
| `jobs[].name` | `string` | 否 | 本地计划或模板 | 面向用户展示的 Job 名称。 |
| `jobs[].description` | `string` | 否 | 本地计划或模板 | Job 描述。 |
| `jobs[].requiredMember` | `integer` | 否 | 本地计划或模板 | 参与人数。 |
| `jobs[].type` | `integer` | 否 | 本地计划或模板 | 不要静默补默认值。 |
| `jobs[].items` | `JobItemReq[]` | 否 | 本地模板和物品池 | 仅在具体流程需要 Job 子项时提供。 |

如果提供 `JobItemReq`，则需要包含 `displayName`、`img`、`name`、`type`、`value`、`valueName`；`id` 可选。

## Relationship With Task Types / 与任务类型的关系

- 严格任务通过模板创建时，平台可能自动生成 Job；创建后应查询 Task 下 Job 列表确认。
- 严格任务直接创建后是否需要额外创建 Job，取决于调用方提供的计划和平台行为。
- 场景任务通常需要额外创建 Job。

Job 创建不应引入新的平台配置冲突；它依赖已经校验通过的 Task 和本地 Job 结构。

## Examples / 示例

批量创建采集作业：

- Request: [examples/create_jobs.request.example.json](examples/create_jobs.request.example.json)
- Response: [examples/create_jobs.response.example.json](examples/create_jobs.response.example.json)

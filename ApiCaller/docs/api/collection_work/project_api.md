# Project API / 采集项目 API

采集项目（Collection Project）是一次数据采集需求来源的顶层集合。Project 主要通过项目名称和描述定义。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询 Project 列表 | `GET` | `/api/zata-manager/projects` | `list_projects(...)` |
| 查询 Project 详情 | `GET` | `/api/zata-manager/projects/{id}` | `get_project(projectId)` |
| 创建 Project | `POST` | `/api/zata-manager/projects` | `create_project(name, description, sceneIds, status)` |
| 更新 Project | `PUT` | `/api/zata-manager/projects/{id}` | `update_project(projectId, name, description, sceneIds, status)` |
| 删除 Project | `DELETE` | `/api/zata-manager/projects/{id}` | `delete_project(projectId)` |

## Fields / 字段

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 是 | 调用方输入或上层计划 | 不能与已有 Collection Project 名称冲突。 |
| `description` | `string` | 否 | 调用方输入或上层计划 | 描述采集需求来源。 |
| `sceneIds` | `integer[]` | 否 | 平台配置快照 | 可选的场景标签 ID。 |
| `status` | `integer` | 否 | 调用方或平台策略 | 除非平台契约要求，否则不要自行补默认值。 |

Project 层面的主要冲突是项目重名。verifier 应在调用 `create_project(...)` 前完成检测。

## Examples / 示例

创建采集项目：

- Request: [examples/create_project.request.example.json](examples/create_project.request.example.json)
- Response: [examples/create_project.response.example.json](examples/create_project.response.example.json)

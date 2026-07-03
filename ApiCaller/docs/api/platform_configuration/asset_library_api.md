# Asset Library API / 资产库 API

资产库包含物品库和场景任务库。实际应用中，资产库是最可能频繁变动的平台配置项，尤其是物品目录、具体物品和场景任务模板。

## Object Library / 物品库

物品库由物品目录（Object Category）和具体物品（Object Item）组成。目录是树形结构；具体物品挂在某个目录下。

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询物品目录树 | `GET` | `/api/zata-manager/object-categories` | `list_object_categories(name)` |
| 创建物品目录 | `POST` | `/api/zata-manager/object-categories` | `create_object_category(...)` |
| 更新物品目录 | `PUT` | `/api/zata-manager/object-categories/{id}` | `update_object_category(...)` |
| 删除物品目录 | `DELETE` | `/api/zata-manager/object-categories/{id}` | `delete_object_category(objectCategoryId)` |
| 查询物品项 | `GET` | `/api/zata-manager/object-items` | `list_object_items(...)` |
| 创建物品项 | `POST` | `/api/zata-manager/object-items` | `create_object_item(...)` |
| 更新物品项 | `PUT` | `/api/zata-manager/object-items/{id}` | `update_object_item(...)` |
| 删除物品项 | `DELETE` | `/api/zata-manager/object-items/{id}` | `delete_object_item(objectItemId)` |

读取物品项时，不应把无 `categoryId` 的 `GET /object-items` 当作可靠全量查询。真实平台联调中，根级查询可能返回空。可靠策略是先读取 `object-categories`，展开所有目录 ID，再按每个 `categoryId` 查询 `object-items`。

verifier 常用的物品目录字段包括 `id`、`name`、`path`、`level` 和 `children`。常用的物品项字段包括 `id`、`categoryId`、`categoryName`、`code` 和 `name`。

## Examples / 示例

创建物品目录：

- Request: [examples/create_object_category.request.example.json](examples/create_object_category.request.example.json)
- Response: [examples/create_object_category.response.example.json](examples/create_object_category.response.example.json)

创建物品项：

- Request: [examples/create_object_item.request.example.json](examples/create_object_item.request.example.json)
- Response: [examples/create_object_item.response.example.json](examples/create_object_item.response.example.json)

## Scene Task Library / 场景任务库

场景任务库用于维护可复用的严格任务模板。模板通常包含任务标题、描述、场景、空间、任务类型、初始状态、动作步骤和物品绑定。

当前版本先提供模板读取能力，用于支持严格任务的模板创建流程。

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 | 当前状态 |
| --- | --- | --- | --- | --- |
| 查询模板列表 | `GET` | `/api/zata-manager/templates` | `list_scene_task_templates(...)` | 已封装 |
| 查询模板详情 | `GET` | `/api/zata-manager/templates/{id}` | `get_scene_task_template(templateId)` | 已封装 |

OpenAPI 中还存在 `POST /api/zata-manager/templates`、导入、导出、更新和删除等模板维护接口。当前项目暂不把这些写入能力作为稳定公开方法；当运行时代码需要模板维护能力时，应先在本页补全接口字段和行为契约。

严格任务可以通过场景任务库模板创建，详见 [../collection_work/strict_task_api.md](../collection_work/strict_task_api.md)。

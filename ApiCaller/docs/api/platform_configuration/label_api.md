# Label API / 标签管理 API

标签管理包括标签分类、标签项和标签树。标签通常在平台初始化阶段配置，后续变化较少；本项目仍保留对应读写能力。

## Category Codes / 标签分类编码

| 分类编码 | 含义 |
| --- | --- |
| `scene` | 场景标签 |
| `space` | 空间标签 |
| `task` | 任务/动作标签 |
| `device` | 设备标签 |

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询标签分类 | `GET` | `/api/zata-manager/label-categories` | `list_label_categories(name)` |
| 查询标签分类详情 | `GET` | `/api/zata-manager/label-categories/{code}` | `get_label_category(categoryCode)` |
| 创建标签分类 | `POST` | `/api/zata-manager/label-categories` | `create_label_category(...)` |
| 更新标签分类 | `PUT` | `/api/zata-manager/label-categories/{code}` | `update_label_category(...)` |
| 删除标签分类 | `DELETE` | `/api/zata-manager/label-categories/{code}` | `delete_label_category(categoryCode)` |
| 查询标签 | `GET` | `/api/zata-manager/labels` | `list_labels(...)`, `list_labels_by_category(...)` |
| 查询标签详情 | `GET` | `/api/zata-manager/labels/{id}` | `get_label(labelId)` |
| 创建标签 | `POST` | `/api/zata-manager/labels` | `create_label(...)` |
| 更新标签 | `PUT` | `/api/zata-manager/labels/{id}` | `update_label(...)` |
| 删除标签 | `DELETE` | `/api/zata-manager/labels/{id}` | `delete_label(labelId)` |
| 查询标签树 | `GET` | `/api/zata-manager/labels/tree` | `get_label_tree(...)`, `list_scene_labels(...)` |

## Snapshot Fields / 快照字段

`sync_platform_configuration()` 会把标签树展开为扁平标签索引。常用字段：

| 字段 | 含义 |
| --- | --- |
| `categoryCode` | 标签分类编码，如 `scene`、`space`、`task`、`device`。 |
| `id` | 平台标签 ID，用于 `sceneId`、`taskPurposeId` 等 Task 字段。 |
| `code` | 业务标签编码，用于创建或更新标签时识别业务含义。 |
| `name` | 标签名称，用于展示和人工选择。 |
| `parentId` | 父标签 ID。 |

严格任务和场景任务都可能引用标签，但严格任务通常引用更多标签类型和动作能力标签。

## Examples / 示例

创建标签分类：

- Request: [examples/create_label_category.request.example.json](examples/create_label_category.request.example.json)
- Response: [examples/create_label_category.response.example.json](examples/create_label_category.response.example.json)

创建标签：

- Request: [examples/create_label.request.example.json](examples/create_label.request.example.json)
- Response: [examples/create_label.response.example.json](examples/create_label.response.example.json)

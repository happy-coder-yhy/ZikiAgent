# Platform Configuration API / 平台配置 API

平台配置是制订采集工作时引用的既有平台选项。当前版本中，最常需要维护的是资产库；标签库通常在初始化后较少变动；设备管理保留读写能力；数据管理暂不属于当前版本开发重点。

本目录只说明平台配置能力本身。创建 `Collection Project`、`Collection Task`、`Collection Job` 时，不应自动补建缺失配置；缺失项应由 verifier 统一列出，再由调用方决定是否进入独立配置维护流程。

## 文档入口

- [asset_library_api.md](asset_library_api.md): 资产库 API，包括物品库和场景任务库。
- [label_api.md](label_api.md): 标签管理 API，包括标签分类、标签和标签树。
- [device_api.md](device_api.md): 设备管理 API，包括设备类型和设备列表。
- [data_management_api.md](data_management_api.md): 数据管理 API，占位说明，当前版本暂不展开。

## 配置快照

`sync_platform_configuration(pageSize=200)` 会聚合当前用户可见的平台配置和采集工作状态：

1. `GET /api/zata-manager/projects?pageNum=1&pageSize=<pageSize>`
2. `GET /api/zata-manager/tasks?pageNum=1&pageSize=<pageSize>`
3. `GET /api/zata-manager/label-categories`
4. `GET /api/zata-manager/labels/tree?categoryCode=<code>` for each label category.
5. `GET /api/zata-manager/object-categories`
6. `GET /api/zata-manager/object-items?categoryId=<id>&pageNum=1&pageSize=<pageSize>` for each flattened object category.
7. `GET /api/zata-manager/device-types?pageNum=1&pageSize=<pageSize>`
8. `GET /api/zata-manager/devices?pageNum=1&pageSize=<pageSize>`

快照字段包括 `projects`、`tasks`、`label_categories`、`label_trees`、`labels`、`object_category_tree`、`object_categories`、`object_items`、`device_types`、`devices` 和 `raw`。

数据管理相关信息暂不纳入当前版本快照；后续版本如需要，应先更新本页和对应测试，再扩展 `sync_platform_configuration(...)`。

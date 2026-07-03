# API Index / API 能力索引

本文档是 Zata Platform API 文档的顶层导航页。它只提供渐进式披露入口，不重复下级文档中的 endpoint 表格和字段细节。

`ZataAPICaller` 内部会自动补充服务前缀：

- RBAC 相关路径使用 `/api/zata-rbac`。
- data-manager 相关路径使用 `/api/zata-manager`。

## Platform Configuration / 平台配置项

平台配置项是制订采集工作时引用的既有选项。当前版本最常维护的是资产库；标签库通常初始化后少变；设备管理保留读写能力；数据管理暂不属于当前版本开发重点。

- [platform_configuration/index.md](platform_configuration/index.md): 平台配置 API 总览。
- [platform_configuration/asset_library_api.md](platform_configuration/asset_library_api.md): 资产库 API，包括物品库和场景任务库。
- [platform_configuration/label_api.md](platform_configuration/label_api.md): 标签管理 API。
- [platform_configuration/device_api.md](platform_configuration/device_api.md): 设备管理 API。
- [platform_configuration/data_management_api.md](platform_configuration/data_management_api.md): 数据管理 API，占位说明。

## User Management / 用户管理

用户管理 API 提供登录、当前用户信息和人员候选查询，是采集工作制订前的基础能力。

- [user_management_api.md](user_management_api.md): 登录、当前用户信息和 RBAC 用户候选查询。

## Collection Work / 采集工作管理

采集工作管理覆盖 `Collection Project`、`Collection Task`、`Collection Job` 的查询、创建、编辑与删除。采集任务按 `taskCategory` 分为严格采集任务、指令采集任务和场景采集任务三类。

- [collection_work/index.md](collection_work/index.md): 采集工作 API 总览。
- [collection_work/project_api.md](collection_work/project_api.md): 采集项目 API。
- [collection_work/strict_task_api.md](collection_work/strict_task_api.md): 严格采集任务 API。
- [collection_work/instruction_task_api.md](collection_work/instruction_task_api.md): 指令采集任务 API。
- [collection_work/scene_task_api.md](collection_work/scene_task_api.md): 场景采集任务 API。
- [collection_work/job_api.md](collection_work/job_api.md): 采集作业 API。

## Deferred Capabilities / 暂缓能力

以下能力已有 OpenAPI 线索，但当前版本不是主要开发重点。

- [collector_api.md](collector_api.md): 采集员操作 API。
- [audit_archive_api.md](audit_archive_api.md): 审核归档 API。

## Supporting Documents / 支撑文档

- [../verifier.md](../verifier.md): 写入前校验器行为契约。
- [../development/testing.md](../development/testing.md): 本地检查和真实平台联调规则。
- [../../CONTEXT.md](../../CONTEXT.md): 项目领域术语。

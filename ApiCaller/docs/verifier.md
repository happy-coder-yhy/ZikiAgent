# Verifier / 创建前校验器

本文档定义采集工作创建前校验器的行为契约，用于支撑未来的 `verifier.py`。校验逻辑不应耦合到 `APICaller` 或 `ZataAPICaller` 中，因为匹配规则可能频繁变化。

## Scope / 适用范围

verifier 负责基于平台配置快照校验计划中的 `Collection Project`、`Collection Task` 和 `Collection Job` 是否可以创建。

Verifier 应运行在 `ZataAPICaller` 写接口之前。它可以依赖 `ZataAPICaller` 的读接口或 `sync_platform_configuration(...)` 获取平台配置快照，但不应在校验内部调用任何写接口。

verifier 负责：

- 判断计划中的采集工作是否可以创建。
- 将业务名称或别名解析为平台真实 ID/code。
- 列出所有缺失或冲突的平台配置项。
- 返回结构化结果，供调用方在写接口前使用。

verifier 不负责：

- 调用平台写接口。
- 创建标签、设备、物品、Project、Task 或 Job。
- 删除或回滚平台资源。
- 发布 Task。
- 静默补充平台默认值。

如果未来增加 `create_scene_task_checked(...)`、`create_strict_task_checked(...)` 这类“校验后写入” helper，应放在独立 workflow/service 层中组合 Verifier 与 `ZataAPICaller`，不应放入 `ZataAPICaller`。`ZataAPICaller` 应继续保持稳定的 API wrapper 边界。

## Inputs / 输入

| 输入 | 类型 | 含义 |
| --- | --- | --- |
| Planned Collection Project | 结构化对象或 mapping | 待创建的项目名称、描述和可选场景引用。 |
| Planned Collection Task | 结构化对象或 mapping | 待创建的任务字段、标签、用户、设备、物品、动作步骤和数量。 |
| Planned Collection Jobs | 结构化列表 | Task 下待创建的作业，包括重复次数和可选 Job 子项。 |
| Platform Configuration Snapshot | `dict` | `ZataAPICaller.sync_platform_configuration(pageSize=...)` 的输出。 |

verifier 只使用传入的快照进行判断，不负责决定何时刷新平台状态。

## Public Functions / 公开函数

Verifier 应支持单接口写入前校验，而不只支持完整 Project/Task/Job 流程。

| 函数 | 适用写接口 | 说明 |
| --- | --- | --- |
| `verify_project_creation(...)` | `create_project(...)` | 校验 Project 名称和可选场景引用。 |
| `verify_strict_task_creation(...)` | `create_strict_task(...)` | 校验严格任务直接创建字段和引用。 |
| `verify_instruction_task_creation(...)` | `create_instruction_task(...)` | 校验指令任务创建字段和引用。 |
| `verify_scene_task_creation(...)` | `create_scene_task(...)` | 校验场景任务创建字段和引用。 |
| `verify_strict_task_from_template_creation(...)` | `create_strict_task_from_template(...)` | 校验严格任务模板创建字段和模板项引用。 |
| `verify_jobs_creation(...)` | `create_jobs(...)` | 校验 Job 创建结构。 |
| `verify_collection_work(...)` | 组合流程 | 组合调用上述能力级 verifier。 |

## Outputs / 输出

推荐的结果结构：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `can_create` | `bool` | 只有不存在阻塞性缺失或冲突时才为 `True`。 |
| `configuration_gaps` | `list[dict]` | 完整的缺失配置项列表。 |
| `conflicts` | `list[dict]` | 完整的多匹配或冲突列表，包括项目重名冲突。 |
| `resolved` | `dict` | 从快照中解析出的平台 ID/code 映射。 |
| `warnings` | `list[dict]` | 需要时记录非阻塞提示。 |

`Configuration Gap` 应足够明确，使人工或上层流程能在创建流程之外修复平台配置。

推荐的 gap 字段：

| 字段 | 含义 |
| --- | --- |
| `scope` | `project`, `task`, or `job`. |
| `field` | 校验失败的计划字段，例如 `sceneId` 或 `objectBindings[].objectCategoryId`。 |
| `expected` | 预期的业务名称、别名、编码或规则。 |
| `reason` | `missing`, `ambiguous`, `conflicting`, or `invalid`. |
| `candidates` | 可选字段，用于列出导致多匹配的平台候选项。 |
| `message` | 面向人的说明。 |

## Validation Order / 校验顺序

1. Check `Collection Project` name conflicts against existing projects.
2. Match `Collection Task` platform configuration requirements.
3. Validate `Collection Job` structure.

这个顺序是刻意设计的。绝大多数配置冲突发生在 Task 准备阶段；Project 冲突主要是项目重名；Job 校验不应产生新的平台配置冲突，只校验结构和已在 Task 阶段解析好的引用。

## Project Checks / Project 校验

verifier 应检查：

- 计划中的项目名称存在。
- 项目名称不与已有 Collection Project 重名。
- 如果使用可选 `sceneIds`，应能解析到已有场景标签。

如果项目名称冲突，应写入 `conflicts`，并在任何写入前停止流程。

## Task Checks / Task 校验

Task 校验应在失败前枚举所有缺失或多匹配的平台配置引用。

Task 校验分为三类 profile：

| Profile | OpenAPI required blocking errors | Business-profile blocking errors | Notes |
| --- | --- | --- | --- |
| `scene_task` | `collectMethod`, `sceneId`, `taskCategory`, `title` | `projectId` | `create_scene_task(...)` 固定补齐 `taskCategory=scene`，默认补齐 `collectMethod=web_video`；场景任务保持轻量，不要求动作步骤或物品绑定。 |
| `instruction_task` | `collectMethod`, `sceneId`, `taskCategory`, `title` | `projectId`, `promptInstruction` | `create_instruction_task(...)` 固定补齐 `taskCategory=instruction` 和 `collectMethod=web_video`；指令任务要求提示文本，不保存动作步骤。 |
| `strict_task` | `collectMethod`, `sceneId`, `taskCategory`, `title` | `projectId`, `deviceTypeId`, `initialState`, `actionSteps`, `objectBindings` | `create_strict_task(...)` 固定补齐 `taskCategory=strict`，默认补齐 `collectMethod=robot`；严格任务直接创建需要完整任务定义。 |
| `strict_task_from_template` | `templateItems`, `templateItems[].templateId` | `projectId`, `collectMethod`, `deviceTypeId` | `create_strict_task_from_template(...)` 默认补齐 `collectMethod=robot`；场景、任务分类、初始状态、动作和物品绑定主要来自模板。 |

OpenAPI required 字段应通过 verifier 中集中维护的显式 profile 管理，而不是散落在多个函数分支里。运行时 verifier 使用这些显式 profile；测试阶段应读取 `docs/data-manager.openapi.json`，确认 profile 覆盖相关 OpenAPI schema 的 required 字段。

尚未确认的平台数值范围、枚举完整取值等规则不应直接阻塞写入，应进入 `warnings`。例如当 `duration`、`minDuration`、`difficulty`、`abnormalRatio` 等字段存在但平台约束尚未确认时，可以返回非阻塞 warning，提醒调用方后续补充规则。

Fields commonly resolved from platform state:

| Task Field | Source |
| --- | --- |
| `sceneId` | Label pool, usually `categoryCode=scene`. |
| `taskPurposeId` | Label pool. |
| `collectModeId` | Label pool. |
| `collectSchemeId` | Label pool. |
| `deviceTypeId` | Device type list or device-related configuration. |
| `sensorTypeId` | Label pool when used. |
| `taskType` | Label pool when used. |
| `customLabelIds` | Label pool. |
| `spaceIds` | Label pool, usually `categoryCode=space`. |
| `collectors[*].userId` | RBAC user candidates. |
| `auditors[*].userId` | RBAC user candidates. |
| `actionSteps[*].atomicAbilityId` | Label pool, usually task/action labels. |
| `objectBindings[*].objectCategoryId` | Object category pool. |
| `objectBindings[*].objectItemIds` | Object item pool. |

Fields commonly validated from local rules or templates:

| Task Field | Validation Guidance |
| --- | --- |
| `title` | Required by OpenAPI. |
| `collectMethod` | Required by OpenAPI. Known platform examples include `robot` and `web_video`; `robot` only allows strict. |
| `taskCategory` | Required by OpenAPI. Known platform examples include `strict`, `instruction`, and `scene`; current wrappers cover all three categories. |
| `difficulty` | Validate allowed range only after the range is confirmed. |
| `duration`, `minDuration` | Validate numeric constraints only after platform rules are confirmed. |
| `countdownSeconds` | Should be non-negative if provided. |
| `abnormalRatio` | Validate range only after platform rules are confirmed. |
| `initialState` | If placeholders are used, ensure bindings exist for them. |

## Job Checks / Job 校验

Job 校验主要关注结构：

- At least one job is provided when the workflow intends to create jobs.
- `requiredRepeat` is present for each `CreateJobReq`.
- `requiredRepeat` is a positive integer when local rules require positive counts.
- `requiredMember` is positive if provided.
- `items` are complete if provided.

`JobItemReq` requires these fields when a job item is present:

- `displayName`
- `img`
- `name`
- `type`
- `value`
- `valueName`

## Failure Behavior / 失败行为

如果校验失败：

1. 返回所有发现的 gap 和 conflict。
2. 停止当前流程。
3. 不创建 Project、Task 或 Job 资源。
4. 不尝试删除或远程回滚。

这依赖“先校验、后写入”的调用顺序。如果调用方在校验前已经写入资源，清理不属于 verifier 职责，必须遵守显式删除确认规则。

## Successful Behavior / 成功行为

如果校验通过：

- 返回 `can_create=True`。
- 返回直接 API 调用所需的平台 ID/code。
- 将所有写入决策留给调用方。

校验成功后的预期写入顺序见 [api/collection_work/index.md](api/collection_work/index.md)。

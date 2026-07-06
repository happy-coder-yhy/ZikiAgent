---
name: scene-task
description: >
  Creates, queries, updates, and publishes scene collection tasks (场景采集任务) on
  the Zata platform via MCP tools. Use `create_scene_task` to create,
  `get_scene_task` to query by name, `update_scene_task` to modify (only
  unpublished tasks), `publish_scene_task` to publish. Always query platform
  config first via `get_platform_config`.
tags: [zata, ziki, scene-task, collection, task-creation, task-update, task-publish]
triggers:
  - user says "创建场景采集任务" / "create a scene task"
  - user says "创建采集任务" / "create a collection task"
  - user says "修改场景任务" / "modify / update a scene task"
  - user says "编辑任务" / "edit a task"
  - user wants to change a task's title, description, difficulty, etc.
  - user mentions modifying/changing a collection task's fields
  - user wants to add a collection task under a project
  - user mentions a scene and project together for task creation
  - user says "发布场景任务" / "publish a scene task"
  - user wants to release or publish a collection task
---

# Scene Task / 场景采集任务

## 用途

在 Zata 平台上**创建**、**修改**和**发布**场景采集任务。

| 操作 | MCP 工具 | 说明 |
|------|----------|------|
| **创建** | `create_scene_task` | 在指定项目下创建新的场景采集任务 |
| **查询** | `get_scene_task` | 根据任务名称查询任务，返回完整 JSON 信息 |
| **修改** | `update_scene_task` | 修改任务字段值。**仅限未发布（status=1）的任务**，已发布（status=2）的任务会被 API 拒绝 |
| **发布** | `publish_scene_task` | 将任务发布上线（status → 2），发布后采集员可领取 |
| **查场景 ID** | `get_scene` | 快速查询场景 ID，1 次 API 调用，支持主场景/子场景 |

---

## 一、创建场景采集任务

### 前置步骤

**尽可能用快速查询工具（只需 1 次 API 调用），避免每次都拉取全量配置：**

| 要查什么 | 用哪个工具 | 调用次数 |
|----------|-----------|---------|
| 任务用途 ID（如"仿真评测"） | `get_task_purpose(name="仿真评测")` | **1 次** |
| 场景 ID（主场景如"居家"，子场景如"整理"） | `get_scene(name="居家")` | **1 次** |
| 项目列表 | `get_platform_config` → `_project_summary` | 5 次 |
| 场景标签、设备类型等全量信息 | `get_platform_config` | 5 次 |

| 参数 | 来源 | 说明 |
|------|------|------|
| `project_id` | `get_platform_config` → `projects` | 目标项目的数字 ID |
| `scene_id` | `get_scene(name="...")` 或 `get_platform_config` → `scene_labels` | 场景标签的数字 ID，优先用 `get_scene`（1 次调用） |
| `task_purpose_id` | `get_task_purpose(name="...")` 或 `get_platform_config` → `task_purposes` | 任务用途 ID，优先用 `get_task_purpose`（1 次调用） |
| `device_type_id` | `get_platform_config` → `device_types` | 设备类型 ID |
| `task_type` | 直接由用户指定 | "短程" 或 "长程" |
| `difficulty` | 直接由用户指定 | "简单"、"普通" 或 "困难" |

### 调用方式

```
Tool: create_scene_task
Required Params:
  - project_id: int       — 项目 ID（来自 get_platform_config）
  - scene_id: int         — 场景标签 ID（来自 get_platform_config）
  - title: string         — 任务标题
  - task_type: string     — "短程" 或 "长程"
  - task_purpose_id: int  — 任务用途 ID（来自 get_platform_config）
  - difficulty: string    — "简单"、"普通" 或 "困难"
  - device_type_id: int   — 设备类型 ID（来自 get_platform_config）
Optional Params:
  - description: string           — 任务描述
  - collect_method: string        — 采集方式，默认 "web_video"
  - collect_mode_id: int          — 采集模式标签 ID
  - collect_scheme_id: int        — 采集方案标签 ID
  - space_ids: int[]              — 空间标签 ID 列表
  - custom_label_ids: int[]       — 自定义标签 ID 列表
  - recognition_enabled: bool     — 是否启用 AI 识别
  - video_quality: int            — 视频画质
  - remark: string                — 任务备注
```

### 创建工作流

1. 用户表达创建意图（如"在项目X下创建场景采集任务"）
2. 调用 `get_platform_config` 获取项目列表、场景标签等参考数据
3. 逐一确认必填字段：
   - 用户未提供项目名 → 展示可用项目列表，询问用户选择哪个
   - 用户未提供场景 → 展示可用场景列表，询问用户
   - 用户未提供标题 → 根据场景自动生成或询问用户
   - 用户未提供 task_type → 询问"短程还是长程？"
   - 用户未提供 task_purpose → 展示可用用途列表，询问用户
   - 用户未提供 difficulty → 询问"简单、普通还是困难？"
   - 用户未提供 device_type → 展示可用设备类型列表，询问用户
4. 组装参数后调用 `create_scene_task`
5. 返回创建结果给用户

---

## 二、修改场景采集任务

### 调用方式

```
Tool: update_scene_task
Required Params:
  - task_id: int          — 要修改的任务 ID（必填）
Optional Params（至少传一个）:
  - title: string           — 新的任务标题
  - scene_id: int           — 新的场景标签 ID
  - description: string     — 新的任务描述
  - task_type: string       — 新的任务类型："短程" 或 "长程"
  - task_purpose_id: int    — 新的任务用途 ID
  - difficulty: string      — 新的难度："简单"、"普通" 或 "困难"
  - device_type_id: int     — 新的设备类型 ID
  - project_id: int         — 新的项目 ID（修改任务所属项目）
  - collect_method: string  — 新的采集方式
  - collect_mode_id: int    — 新的采集模式标签 ID
  - collect_scheme_id: int  — 新的采集方案标签 ID
  - space_ids: int[]        — 新的空间标签 ID 列表
  - custom_label_ids: int[] — 新的自定义标签 ID 列表
  - recognition_enabled: bool — 是否启用 AI 识别
  - video_quality: int      — 新的视频画质
  - remark: string          — 新的任务备注
```

### 查询工作流

1. 用户想查看某个场景任务的详细信息
2. 调用 `get_scene_task(title="<任务名>")` 查询
3. 如果 `found: false`，告知用户该任务不存在
4. 如果 `count == 1`，`task` 字段包含任务的完整 JSON 信息
5. 如果 `count > 1`，`tasks` 字段列出多个匹配项，让用户指定具体 ID

### 修改工作流

1. 用户提出修改意图（如"帮我改一下任务XX的标题"）
2. 如果用户没说要改哪个字段 → **先询问用户**"您想修改哪个字段？"
3. 确定 `task_id`：
   - **首选**：调用 `get_scene_task(title="<任务名>")` 查询任务，获取 `task.id` 和当前状态
   - **备选**：用 `session_search(query="<任务名>")` 从历史会话中查找任务 ID
4. 如果修改涉及 scene_id，优先用 `get_scene(name="...")`，涉及 task_purpose_id，优先用 `get_task_purpose(name="...")` 查询（1 次 API 调用）；涉及 device_type_id 等其他 ID 字段则调用 `get_platform_config`
5. 调用 `update_scene_task` 传入 task_id 和需要修改的字段
6. 检查返回结果：`success: true` + `updated_fields` 列出实际变更的字段

### 限制条件与已知行为

- **仅限未发布（status=1）的任务** — 已发布任务（status=2）会被 API 拒绝修改
- 修改前先调 `get_scene_task` 查看任务状态
- **至少指定一个要修改的字段**，不能空调用
- task_type 只接受 "短程" 或 "长程"
- difficulty 只接受 "简单"、"普通" 或 "困难"

### ⚠️ 子场景修改：同名场景 ID 解析

`get_platform_config` 返回的 `scene_labels` 是扁平列表（所有 `parentId=None`），同一个子场景名可能出现在多个主场景下。例如：

| 子场景"整理" | 主场景 |
|---|---|
| ID=182 | 居家 |
| ID=192 | 工厂 |

**修改 scene_id 时，必须根据任务的 `mainSceneId`（或 `mainSceneName`）来确定正确的子场景 ID。** 不能仅凭名称匹配——同名不同父有多种可能。

**推荐工作流（首选 `get_scene`，1 次 API 调用）：**
1. 调用 `get_scene_task(title="...")` 获取任务的当前 `mainSceneId` 或 `mainSceneName`
2. 调用 `get_scene(name="整理")` — 如果同名子场景返回多个 matches，根据 `parentName` 选择正确的那个
3. 传入正确的 scene_id 调用 `update_scene_task`

**备用工作流（仅当需要全量配置时才用 `get_platform_config`）：**
1. 调用 `get_scene_task(title="...")` 获取任务的当前 `mainSceneId`
2. 调用 `get_platform_config` 获取 `scene_labels` 列表
3. 从任务已知的主场景名称（如"工厂"），找到其下对应的子场景 ID（如 工厂→整理=192）
4. 传入正确的 scene_id 调用 `update_scene_task`

---

## 三、发布场景采集任务

### 调用方式

```
Tool: publish_scene_task
Required Params:
  - task_id: int          — 任务 ID（必填）
```

### 发布工作流

1. 用户提出发布意图（如"帮我发布XX任务"）
2. 调用 `get_scene_task(title="<任务名>")` 查询任务，获取 `task.id` 和当前状态
3. **检查任务状态**：
   - `status=1`（未发布）→ 可以发布
   - `status=2`（已发布）→ 提示用户"该任务已是发布状态，无需重复发布"
   - 其他已归档/删除状态 → 告知用户当前状态，无法发布
4. 调用 `publish_scene_task(task_id=...)` 发布任务
5. 检查返回结果：`success: true` 表示发布成功，`data` 中任务 `status` 变为 `2`

### 限制条件

- **仅限未发布（status=1）的任务** — 已发布（status=2）的任务再次发布会被 API 拒绝
- 发布后任务将可以被采集员领取执行
- 发布前建议先确认任务的所有必填字段已填写完整（标题、场景、设备类型、采集员等）
- 如果发布后需要修改，必须先取消发布（目前暂未封装 unpublish 工具，后续可扩展）

---

## 四、通用注意

- **所有 ID 必须从 `get_platform_config` 获取**，不要硬编码或猜测
- task_type 只接受 "短程" 或 "长程"，其他值会报错
- difficulty 只接受 "简单"、"普通" 或 "困难"，其他值会报错
- 创建成功后返回的 data 中包含新任务的 id
- 修改成功后返回的 `updated_fields` 中列出实际变更的字段，以此判断是否生效
- `get_platform_config` 输出可能超过 100KB 被截断，优先用 `session_search` 查找历史任务 ID

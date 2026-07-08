---
name: scene-task-job
description: >
  Creates, updates, and deletes jobs (作业) under a specified scene task (场景任务)
  on the Zata platform via MCP tools. Use `create_job` to create a job with
  plan_collect_count and description; use `update_job` to modify an existing job
  located by its description; use `delete_job` to remove a job located by its
  description. All operations validate the scene task exists and is of type "scene".
tags: [zata, ziki, scene-task, job, create-job, update-job, delete-job]
triggers:
  - user says "创建一个作业" / "create a job"
  - user says "在xxx任务下创建作业" / "create a job under task xxx"
  - user says "添加一个采集作业" / "add a collection job"
  - user says "修改作业" / "update a job" / "edit a job"
  - user says "删除作业" / "delete a job" / "remove a job"
  - user says "帮我修改xxx作业的描述" / "change job description"
  - user wants to create / modify / delete a job under a scene task
---

# Scene Task Job / 场景任务作业管理

## 用途

在 Zata 平台上**创建**、**修改**和**删除**指定场景任务下的作业（Job）。

| 操作 | MCP 工具 | 说明 |
|------|----------|------|
| **创建** | `create_job` | 在指定场景任务下创建作业 |
| **修改** | `update_job` | 根据作业描述查找并修改作业 |
| **删除** | `delete_job` | 根据作业描述查找并删除作业 |

---

## 通用前置步骤：场景任务校验

**所有操作（创建/修改/删除）都必须先校验场景任务是否存在：**

1. Tool 根据 `scene_task_name` 查询场景任务
2. 仅匹配 `taskCategory == "scene"` 的任务
3. 如果不存在 → 返回 `"当前不存在该场景任务「xxx」，暂不支持创建/编辑/删除作业。"`
4. 如果存在多条匹配 → 返回候选列表，要求用户确认
5. 如果唯一匹配但 `taskCategory` 不是 `"scene"` → 拒绝操作

---

## 一、创建作业

### 调用方式

```
Tool: create_job
Required Params:
  - scene_task_name: str    — 场景任务名称（必填）
  - plan_collect_count: int — 计划采集数（必填，对应 requiredRepeat）
  - description: str        — 作业描述（必填）
Optional Params:
  - collect_method: str     — 采集方式，默认 "web_video"
  - project_id: int         — 项目 ID（选填，缩小场景任务搜索范围）
  - name: str               — 作业名称（选填）
  - required_member: int    — 需求人数（选填）
  - job_type: int           — 作业类型（选填）
```

### 创建工作流

1. 用户表达创建意图（如"在 xxx 场景任务下创建一个采集作业"）
2. **检查必填字段**：
   - 用户未提供 `plan_collect_count`（计划采集数）→ 询问"请提供该作业的计划采集数。"
   - 用户未提供 `description`（描述）→ 询问"请提供该作业的描述。"
   - **只有在字段完整后才调用 `create_job`**
3. 调用 `create_job`，Tool 内部自动校验场景任务存在性
4. 返回创建结果给用户

### 示例

用户：在测试场景任务创建一个作业

→ Agent 发现缺少 plan_collect_count 和 description

→ 回复：**请提供该作业的计划采集数和描述。**

用户：计划采集 100 个，描述是"采集首页视频"

→ Agent 调用 `create_job(scene_task_name="测试场景任务", plan_collect_count=100, description="采集首页视频")`

---

## 二、修改作业

### 定位规则

用户**不会直接提供 job_id**，而是通过**作业描述（description）**来定位作业：

1. 查场景任务 → 获取 task_id
2. 根据 `job_description` 在该任务下查找作业
3. 根据匹配情况处理（见下方）

### 匹配情况处理

#### 情况 1：未找到匹配作业

返回：`"未找到描述为「xxx」的作业，请确认作业描述。"`

Agent 应向用户确认描述是否正确。

#### 情况 2：多个匹配

返回 candidates 列表，包含每个作业的 `id`、`title`、`description`、`createdAt`、`requiredRepeat`。

**禁止自动选择**。Agent 必须展示候选列表给用户，让用户确认具体要修改哪一个。

Agent 应展示格式：
```
找到 3 个描述相同的作业，请确认需要修改哪一个：
1. ID: 42, 标题: xxx, 创建时间: 2025-01-01
2. ID: 43, 标题: yyy, 创建时间: 2025-01-02
3. ID: 44, 标题: zzz, 创建时间: 2025-01-03
```

用户确认后，需要在后续迭代中通过 job_id 直接定位（此时需额外提供 job_id 参数... 但工具设计为基于描述查找）。

> 实际处理：当出现多条匹配时，Agent 应记录用户选择的 job_id，然后通过 `update_job` 再次尝试（此时唯一匹配）。

#### 情况 3：唯一匹配

获取 job_id 后执行修改。

### 调用方式

```
Tool: update_job
Required Params:
  - scene_task_name: str    — 场景任务名称（必填）
  - job_description: str    — 要修改的作业描述，用于查找（必填）
Optional Params（至少传一个）:
  - plan_collect_count: int — 新的计划采集数（对应 requiredRepeat）
  - new_description: str    — 新的作业描述
  - name: str               — 新的作业名称
  - required_member: int    — 新的需求人数
  - job_type: int           — 新的作业类型
  - collect_method: str     — 采集方式，默认 "web_video"
  - project_id: int         — 项目 ID（选填）
```

### 修改工作流

1. 用户提出修改意图（如"帮我改一下 xxx 任务下描述为 yyy 的作业"）
2. 确认要修改的字段，至少指定一个
3. 调用 `update_job`：
   - 传入 `scene_task_name` 和 `job_description`
   - 传入要修改的字段值
4. 处理返回结果：
   - 唯一匹配 → 直接修改成功
   - 多条匹配 → 展示候选列表让用户选择
   - 未匹配 → 告知用户确认描述
5. 检查返回的 `updated_fields` 确认修改生效

---

## 三、删除作业

### 定位规则

与修改相同，通过 `job_description` 定位。

### 匹配情况处理

| 匹配数 | 处理方式 |
|--------|----------|
| 0 | 提示用户未找到对应作业 |
| >1 | **禁止删除**，展示候选列表询问用户确认 |
| 1 | 唯一匹配，执行删除 |

### 调用方式

```
Tool: delete_job
Required Params:
  - scene_task_name: str  — 场景任务名称（必填）
  - job_description: str  — 要删除的作业描述，用于查找（必填）
Optional Params:
  - collect_method: str   — 采集方式，默认 "web_video"
  - project_id: int       — 项目 ID（选填）
```

### 删除工作流

1. 用户提出删除意图（如"删除 xxx 任务下描述为 yyy 的作业"）
2. 调用 `delete_job`：
   - 传入 `scene_task_name` 和 `job_description`
3. 处理返回结果：
   - 唯一匹配 → 直接删除，返回 `deleted_job_id`
   - 多条匹配 → 展示候选列表让用户选择
   - 未匹配 → 告知用户确认描述

---

## 四、必填字段说明

### 创建作业必填字段

| 字段 | 参数名 | 说明 |
|------|--------|------|
| 场景任务名称 | `scene_task_name` | 指定在哪个场景任务下操作 |
| 计划采集数 | `plan_collect_count` | 对应 API 的 `requiredRepeat`，必须提供才能创建 |
| 描述 | `description` | 作业描述，同时用于后续修改/删除时的查找 |

### 修改作业必填字段

| 字段 | 参数名 | 说明 |
|------|--------|------|
| 场景任务名称 | `scene_task_name` | 指定在哪个场景任务下操作 |
| 作业描述 | `job_description` | 用于查找要修改的作业 |
| 至少一个修改字段 | — | 如 plan_collect_count、new_description 等 |

---

## 五、异常情况处理

| 异常 | 返回信息 | Agent 行为 |
|------|---------|-----------|
| 场景任务不存在 | `当前不存在该场景任务「xxx」，暂不支持创建/编辑/删除作业。` | 告知用户，停止操作 |
| 非场景任务 | `「xxx」不是场景任务（taskCategory=xxx），暂不支持...` | 告知用户该任务是其他类型，不支持 |
| 多个场景任务同名 | candidates 列表 | 展示候选列表让用户选择 |
| 缺少计划采集数 | `请提供该作业的计划采集数（plan_collect_count）。` | 追问用户 |
| 缺少描述 | `请提供该作业的描述（description）。` | 追问用户 |
| 未找到匹配作业 | `未找到描述为「xxx」的作业，请确认作业描述。` | 让用户确认描述 |
| 多个相同描述作业 | candidates 列表（含 id、title、createdAt 等） | 展示候选列表，禁止自动选择 |
| 修改时未指定字段 | `请指定要修改的字段...` | 询问用户要改什么 |

---

## 六、与已有工具的关系

- **场景任务查询**：复用 `get_scene_task`（来自 `scene_task` 模块），所有操作先通过它校验场景任务存在性。
- **作业列表查询**：复用 `caller.list_jobs`（同 `task_job_details` 的模式），用于根据描述查找作业。
- **作业详情**：如需查看作业详情，使用已有的 `job_detail` 工具。
- **任务下所有作业**：如需查看某任务下的所有作业，使用已有的 `task_job_details` 工具。

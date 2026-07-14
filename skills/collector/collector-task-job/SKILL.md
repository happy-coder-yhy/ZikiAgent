---
name: collector-task-job
description: >
  Query all tasks and jobs related to a specific collector on the Zata platform
  via the `query_task_job` MCP tool. Shows which tasks the collector is assigned
  to, all jobs within those tasks with their status and progress, and summary
  statistics (total tasks, received vs assigned jobs, overall progress).
tags: [zata, ziki, collector, query-task-job]
triggers:
  - user identifies as 采集员 / collector / data collector
  - user says "我是采集员" / "I'm a collector"
  - user says "我的任务" / "my tasks"
  - user says "查询我的作业" / "query my jobs"
  - user says "查看我的采集进度" / "check my collection progress"
  - user asks "我有哪些任务" / "what tasks do I have"
  - user asks "我有哪些作业" / "what jobs do I have"
  - user asks "我的采集情况怎么样" / "how's my collection going"
  - user says "查看我领取的作业" / "show my received jobs"
  - user wants to know which jobs they have received vs just assigned
  - user wants a summary of their work status
---

# Collector Task & Job / 采集员任务作业查询

## ⚠️ 角色隔离

**当用户声明自己是采集员时，本 skill 是唯一应被使用的 skill 文档。** 采集员只能使用 `mcp_server/collector/` 模块下的工具，不得使用管理员工具（`task_summary`、`task_detail` 等）。参见 [总规则](../../SKILL.md)。

## 用途

查询指定采集员在 Zata 平台上的**所有相关任务与作业**，包括任务分配情况、作业领取状态、采集进度等。

| 工具 | 用途 |
|------|------|
| `query_task_job` | 查询采集员的所有任务和作业（含状态、进度） |

---

## 调用方式

```
Tool: query_task_job
Params:
  - collector_id: string  — 采集员用户 ID（可选）。不传则自动获取当前登录用户。
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collector_id` | string | 否 | 采集员的用户 ID。**不传则自动通过当前登录用户获取**，适用于采集员直接说"我的任务"的场景。 |

> **自动身份识别**：MCP 服务器已通过 `.env` 配置的账号密码登录。调用 `query_task_job()`（不传参）时，工具会自动调用 `userinfo` 接口获取当前登录用户的 ID，无需 agent 手动查找。只有在需要查询**其他**采集员的任务时才需显式传入 `collector_id`。

---

## 返回字段

### 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `collector_id` | string | 采集员 ID |
| `summary` | object | 汇总统计（见下方） |
| `tasks` | array | 任务列表（见下方） |

### summary（汇总统计）

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_tasks` | int | 相关任务总数 |
| `total_jobs` | int | 所有任务下的作业总数 |
| `received_jobs` | int | 已领取的作业数 |
| `assigned_not_received_jobs` | int | 已分配但未领取的作业数 |
| `overall_progress` | object | 汇总进度 |

### summary.overall_progress（汇总进度）

| 字段 | 类型 | 说明 |
|------|------|------|
| `normalCollect` | int | 常规采集已完成数 |
| `normalCollectTotal` | int | 常规采集总数 |
| `normalCollectPct` | float\|null | 常规采集完成百分比 |
| `normalReview` | int | 常规审核已完成数 |
| `abnormalCollect` | int | 异常采集已完成数 |
| `abnormalCollectTotal` | int | 异常采集总数 |
| `abnormalReview` | int | 异常审核已完成数 |

### tasks[]（任务条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | int | 任务 ID |
| `title` | string | 任务标题 |
| `taskCategory` | string | 任务分类（strict/instruction/scene） |
| `projectName` | string | 所属项目名称 |
| `collectMethod` | string | 采集方式（robot/web_video） |
| `jobCount` | int | 该任务下作业总数 |
| `receivedJobCount` | int | 该任务下已领取的作业数 |
| `jobs` | array | 作业列表（见下方） |

### tasks[].jobs[]（作业条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 作业 ID |
| `name` | string | 作业名称 |
| `description` | string | 作业描述 |
| `collectStatus` | int | 采集状态码（0=未分配, 1=已分配, 2=已领取） |
| `collectStatusLabel` | string | 采集状态中文标签 |
| `reviewStatus` | int | 审核状态码（0=未分配, 1=已分配） |
| `reviewStatusLabel` | string | 审核状态中文标签 |
| `received` | bool | 当前采集员是否已领取该作业 |
| `requiredMember` | int | 要求的采集员数量 |
| `requiredRepeat` | int | 要求重复次数 |
| `receiveCount` | int | 已领取的采集员数 |
| `progress` | object | 作业进度（normalCollect, normalCollectTotal 等） |

---

## 查询工作流

1. 用户表达查看自己任务作业的意图（如"帮我看看我的任务作业"）
2. **无需查找 collector_id** — 直接调用 `query_task_job()`（不传参），工具自动获取当前用户身份
3. 解读返回结果，向用户汇报：
   - 先说明汇总：总共几个任务、几个作业、几个已领取
   - 再逐一列出任务和作业详情
   - 重点突出：哪些作业已领取、哪些还没领取、整体进度

> **仅在查询其他采集员时**才需要显式传入 `collector_id`：先通过 `search_user(name="用户名")` 查询 ID，再调用 `query_task_job(collector_id="...")`。

---

## 场景示例

### 示例 1：查看我的任务作业（自动识别）

用户："帮我看看我的任务和作业情况"

→ 直接调用 `query_task_job()`（不传参，自动获取当前用户）
→ 返回：
```json
{
  "success": true,
  "collector_id": "6e1465a8-...",
  "summary": {
    "total_tasks": 2,
    "total_jobs": 5,
    "received_jobs": 3,
    "assigned_not_received_jobs": 2,
    "overall_progress": {
      "normalCollect": 45,
      "normalCollectTotal": 100,
      "normalCollectPct": 45.0
    }
  },
  "tasks": [...]
}
```

### 示例 2：查看我的采集进度

用户："我的采集进度怎么样？"

→ 同上流程，重点关注 `summary.overall_progress`：
  - `normalCollectPct: 45.0` → 常规采集完成 45%（45/100）
  - `received_jobs: 3, assigned_not_received_jobs: 2` → 已领取 3 个作业，还有 2 个待领取

### 示例 3：无相关任务

用户："看看我的任务"（该采集员尚无任何分配或领取）

→ 返回 `total_tasks: 0, tasks: []` → 告知用户"目前没有与你相关的任务或作业"

---

## 注意事项

- `collector_id` 必须是用户 ID（UUID 格式），不是用户名或显示名称
- 通过 `search_user(name="用户名")` 获取 collector_id
- `received=true` 表示该作业已被当前采集员领取；`received=false` 表示仅分配未领取
- `collectStatus=2（已领取）` 是作业级别的聚合状态，`received` 是当前采集员维度的状态
- 进度百分比 `normalCollectPct` 仅在 `normalCollectTotal > 0` 时有值，否则为 `null`
- 若 `total_tasks=0`，说明该采集员可能尚未被分配任何任务，或尚未领取任何作业

---

## 工具二：claim_job — 领取作业

### 用途

采集员领取与自己相关的**已发布**任务下的作业。只有状态为"已发布"（status=2）的任务下的作业才能被领取。

| 工具 | 用途 |
|------|------|
| `claim_job` | 采集员领取已发布任务下的作业 |

### 调用方式

```
Tool: claim_job
Params:
  - job_description: string  — 作业描述（模糊匹配），与 job_id 二选一
  - task_name: string        — 任务名称（可选），用于缩小查找范围
  - job_id: string           — 作业 ID（精确匹配），与 job_description 二选一
  - task_id: string          — 任务 ID，配合 job_id 使用
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `job_description` | string | 条件必填 | 作业描述（模糊匹配，含判断）。与 `job_id` 二选一。 |
| `task_name` | string | 否 | 任务名称（模糊匹配），用于缩小查找范围。仅在 `job_description` 模式下有效。 |
| `job_id` | string | 条件必填 | 作业 ID（精确匹配）。与 `job_description` 二选一，需同时提供 `task_id`。 |
| `task_id` | string | 条件必填 | 任务 ID，配合 `job_id` 使用。 |

> **自动身份识别**：无需传入采集员 ID，工具会自动通过 `userinfo` 获取当前登录用户身份。

### 返回字段

#### 成功（领取成功）

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | `true` |
| `message` | string | 成功提示信息 |
| `collector_id` | string | 采集员 ID |
| `collector_name` | string | 采集员用户名 |
| `job_id` | int | 已领取的作业 ID |
| `task_id` | int | 作业所属任务 ID |
| `job_description` | string | 作业描述 |
| `job_name` | string | 作业名称 |
| `task_title` | string | 任务标题 |

#### 已领取（幂等）

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | `true` |
| `already_claimed` | bool | `true` — 无需重复操作 |
| `message` | string | "该作业已被您领取，无需重复操作" |

#### 任务未发布

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | `false` |
| `error` | string | 拒绝原因（含任务状态） |
| `task_status` | int | 任务当前状态码 |

#### 匹配到多个作业

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | `false` |
| `error` | string | "匹配到 N 个作业，请指定更精确的条件" |
| `candidates` | array | 候选作业列表（含 job_id, task_id, job_description, task_title） |

### 工作流

1. 用户表达领取意图（如"帮我领取居家整理任务下的作业维护测试作业"）
2. **无需查找 collector_id** — 工具自动获取当前用户身份
3. 工具按 `job_description` + 可选 `task_name` 查找匹配的作业
4. 检查作业所属任务是否已发布（status=2）
   - 未发布 → 返回拒绝信息，告知用户该任务尚未发布
   - 已发布 → 继续
5. 检查该作业是否已被领取（幂等）
   - 已领取 → 返回 `already_claimed: true`
   - 未领取 → 调用 API 领取
6. 返回领取结果

### 场景示例

#### 示例 1：模糊匹配领取（推荐方式）

用户："帮我领取居家整理任务下的作业维护测试作业"

→ 调用 `claim_job(job_description="作业维护测试", task_name="居家整理")`
→ 返回：
```json
{
  "success": true,
  "message": "已成功领取作业「作业维护测试」（任务：居家整理）",
  "collector_id": "27b5f00f-...",
  "collector_name": "collector",
  "job_id": 134,
  "task_id": 261,
  "job_description": "作业维护测试",
  "task_title": "居家整理"
}
```

#### 示例 2：不指定任务名（全局搜索）

用户："帮我领取111作业"

→ 调用 `claim_job(job_description="111")`
→ 扫描采集员所有相关任务，匹配到 jobId=154（任务"hhh"）→ 领取成功

#### 示例 3：任务未发布 — 拒绝

用户："帮我领取未发布任务下的xxx作业"

→ 工具发现该任务 status=1（未发布）
→ 返回：
```json
{
  "success": false,
  "error": "该任务（xxx任务）尚未发布（状态：未发布），无法领取作业。只有已发布的任务才能领取作业。",
  "task_status": 1
}
```

#### 示例 4：已领取（幂等）

用户再次说："帮我领取作业维护测试作业"

→ 工具检测到该作业已被当前采集员领取
→ 返回：
```json
{
  "success": true,
  "already_claimed": true,
  "message": "该作业已被您领取，无需重复操作"
}
```

#### 示例 5：匹配到多个作业

用户："帮我领取测试作业"

→ 匹配到多个含"测试"的作业
→ 返回 candidates 列表，让用户选择后使用 `job_id` + `task_id` 精确指定

#### 示例 6：精确 ID 领取

用户明确知道 ID 时："帮我领取 taskId=262 下的 jobId=154"

→ 调用 `claim_job(job_id="154", task_id="262")`
→ 直接精确查找并领取

### 注意事项

- `job_description` 和 `job_id` 必须提供其中之一
- 使用 `job_id` 时必须同时提供 `task_id`
- 只有已发布（status=2）的任务下的作业才能被领取
- 重复领取同一作业会返回 `already_claimed: true`（幂等安全）
- `task_name` 参数可帮助在多个任务中有同名作业时缩小范围
- 若匹配到多个作业，建议提供更精确的描述或使用 ID 模式

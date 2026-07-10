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

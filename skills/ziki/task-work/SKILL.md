---
name: task-work
description: >
  Provides task overview statistics via `task_summary`, single-task detail
  query via `task_detail`, and platform-wide job overview via `job_summary`
  on the Ziki platform. Use `task_summary` when the user asks "how many tasks"
  or wants a platform-wide overview; use `task_detail` when the user asks about
  a specific task's full details; use `job_summary` for platform job overview.
tags: [zata, ziki, task-work, summary, statistics, detail]
triggers:
  # 任务概览
  - user asks "平台有多少任务" / "how many tasks on the platform"
  - user asks "当前平台任务概要" / "task overview / task summary"
  - user asks "任务统计" / "task statistics"
  - user says "帮我看看平台的任务情况"
  - user asks about total / scene / instruction / strict / published task counts
  - user wants to know the distribution of task categories
  # 任务详情
  - user asks "帮我看看xx任务" / "show me the details of task xxx"
  - user says "查一下xx任务的详情" / "query task xxx details"
  - user says "xx任务是什么情况" / "what's the status of task xxx"
  - user wants to see a specific task's full info (fields, published status, jobs)
  - user asks whether a task has assignments / jobs / 作业
  - user asks whether a task is published / 已发布
  # 作业概览
  - user asks "平台作业概览" / "platform job overview"
  - user asks "平台有多少作业" / "how many jobs on the platform"
  - user says "帮我看看平台的作业情况"
  - user wants to know job distribution across task categories
  - user asks "哪些任务有作业" / "which tasks have jobs"
---

# Task Work / 任务概览与详情查询

## 概述

本 skill 覆盖三个任务查询工具：

| 工具 | 用途 |
|------|------|
| `task_summary` | 平台任务概要统计（总数、分类统计） |
| `task_detail` | 单个任务的完整详情查询 |
| `job_summary` | 平台作业概览（总数、分类统计、各任务作业数） |

---

## 一、任务概要统计（task_summary）

详见下方「任务概览」板块。适用于用户询问"平台有多少任务"等全局统计场景。

## 二、任务详情查询（task_detail）

### 用途

查询平台上**指定任务的完整详细信息**，包括：

- 任务基本信息（标题、ID、状态、分类、所属项目）
- 任务配置信息（场景、设备类型、采集方式、任务用途、难度等）
- **发布状态**（status == 2 表示已发布）
- **作业数量**（jobCount > 0 表示已有作业）
- 审核员、采集员列表
- 其他字段（创建时间、创建人、备注等）

### 调用方式

```
Tool: task_detail
Required Params:
  task_id: int  — 任务 ID（必填，必须为数字）
```

> **注意：** `task_id` 必须是数字类型。如果只知道任务名称，需要先用 `task_summary(title="任务名")` 查询出任务 ID。

### 返回示例

```json
{
  "success": true,
  "data": {
    "id": 42,
    "title": "商超收银场景采集",
    "status": 2,
    "taskCategory": "scene",
    "projectId": 1,
    "projectName": "项目A",
    "sceneId": 182,
    "sceneName": "整理",
    "mainSceneId": 10,
    "mainSceneName": "居家",
    "taskType": 305,
    "taskTypeName": "短程",
    "taskPurposeId": 209,
    "taskPurposeName": "仿真评测",
    "difficulty": 2,
    "collectMethod": "web_video",
    "description": "采集居家整理场景的视频数据",
    "remark": "优先采集白天数据",
    "deviceTypeId": 15,
    "deviceTypeName": "手机",
    "jobCount": 12,
    "collectors": [{"id": 1, "displayName": "采集员A"}],
    "auditors": [{"id": 2, "displayName": "审核员B"}],
    "createdAt": "2024-03-15 10:30:00",
    "createdBy": "admin",
    "updatedAt": "2024-03-16 14:20:00"
  },
  "detail": {
    "id": 42,
    "title": "商超收银场景采集",
    "status": 2,
    "published": true,
    "taskCategory": "scene",
    "jobCount": 12
  }
}
```

### 工作流

**查询某个任务的详情（完整步骤）：**

1. 用户提出查看任务详情的意图：
   - "帮我看看xx任务"
   - "查一下xx任务的详情"
   - "xx任务是什么情况？"
   - "xx任务发布了吗？"
   - "xx任务有作业了吗？"

2. **获取任务 ID：**
   - **首选方式：** 调用 `task_summary(title="<任务名>")`，从返回的 `tasks` 列表中找到目标任务的 `id`
   - **备选方式：** 如果用户直接给出了任务 ID（如"看看任务42的详情"），直接使用

3. **获取任务详情：**
   - 调用 `task_detail(task_id=<id>)`

4. **向用户汇报完整信息**（用自然语言风格，不要用表格或结构化列表，像聊天一样自然地组织）：

   **基本原则：**
   - 🚫 **不要使用表格、markdown 列表或结构化字段列表**来罗列字段
   - ✅ 用完整的句子串联信息，像跟朋友聊天一样自然但严谨地组织信息。

   **关键信息需自然带出，不要遗漏：**
   - 任务名称 + ID → 开篇一句话点明
   - 分类（场景/指令/严格）→ 这是最重要的属性，紧跟其后
   - 发布状态 → 视情况用"已发布"、"还未发布"、"已上线"等自然表述
   - 是否有作业 → 用"有没有作业"、"已有 X 个作业"等口语表达
   - 所属项目、场景配置等 → 串联成句子
   - 非空字段才汇报，null/空字段直接忽略

### 场景示例

| 用户提问 | AI 执行步骤 | 回复要点 |
|----------|------------|----------|
| "帮我看看 '整理房间' 任务" | 1. `task_summary(title="整理房间")` → 查到 task_id=42<br>2. `task_detail(task_id=42)` | 展示名称、分类、是否发布、作业数、场景、难度等 |
| "查一下 42 号任务的详情" | `task_detail(task_id=42)` | 直接展示完整详情 |
| "'商超收银'这个任务发布了吗？" | 1. `task_summary(title="商超收银")` → task_id<br>2. `task_detail(task_id=..)` → 看 detail.published | "✅ 已发布" 或 "❌ 未发布" |
| "'整理房间'任务有作业了吗？" | 1. 查 task_id<br>2. `task_detail(task_id=..)` → 看 detail.jobCount | "已有 12 个作业" 或 "暂无作业" |
| "'工厂巡检'任务是什么情况？" | 1. 查 task_id<br>2. `task_detail` | 完整汇报所有非空字段 |

---

## 三、任务概览（task_summary）

### 用途

查询 Ziki 平台上当前任务的**概要统计信息**，包括：

- **任务总数（total）** — 平台上的任务总数量
- **场景任务数（scene_num）** — 分类为"场景"的任务数量（taskCategory = "scene"）
- **指令任务数（instruction_num）** — 分类为"指令"的任务数量（taskCategory = "instruction"）
- **严格任务数（strict_num）** — 分类为"严格"的任务数量（taskCategory = "strict"）
- **已发布任务数（issued）** — 已发布状态的任务数量（status = 2）

### 调用方式

```
Tool: task_summary
Optional Params:
  title: string      — 按任务标题模糊筛选（可选）
  page_num: int      — 页码，默认 1
  page_size: int     — 每页数量，默认 100
```

### 返回示例

```json
{
  "success": true,
  "total": 128,
  "scene_num": 65,
  "instruction_num": 42,
  "strict_num": 21,
  "issued": 80,
  "tasks": [
    {"id": 1, "title": "整理房间", "status": 2, "taskCategory": "scene"},
    {"id": 2, "title": "指令任务A", "status": 1, "taskCategory": "instruction"}
  ]
}
```

### 工作流

1. 用户提出查看任务概要的意图（"平台现在有多少任务？"、"帮我看看任务情况"）
2. 直接调用 `task_summary` 获取统计
3. 将结果以易于阅读的形式返回给用户，例如：
   > 当前平台共有 **128** 个任务，其中：
   > - 场景任务：**65** 个
   > - 指令任务：**42** 个
   > - 严格任务：**21** 个
   > - 已发布：**80** 个
4. 如果用户想看具体任务列表，也一并返回 `tasks` 数组中的概要信息

### 按标题筛选

如果用户想了解某个特定名称的任务统计，或通过名称查找任务 ID：

```
task_summary(title="整理")
```

返回中 `tasks` 数组包含匹配任务的 `id`，可用于后续的 `task_detail` 调用。

---

## 四、平台作业概览（job_summary）

### 用途

查询 Ziki 平台上所有任务的**作业（job）概览信息**，包括：

- **作业总数（total_jobs）** — 平台所有任务下作业的总数（各任务 jobCount 之和）
- **场景任务作业数（scene_jobs）** — 分类为"场景"的任务下的作业总数
- **指令任务作业数（instruction_jobs）** — 分类为"指令"的任务下的作业总数
- **严格任务作业数（strict_jobs）** — 分类为"严格"的任务下的作业总数
- **有作业的任务数（task_count）** — jobCount > 0 的任务数量
- **各任务作业明细（task_jobs）** — 每个有作业的任务 ID、名称、分类及作业数（按作业数降序排列）

### 调用方式

```
Tool: job_summary
Optional Params:
  page_num: int      — 页码，默认 1
  page_size: int     — 每页数量，默认 200
```

### 返回示例

```json
{
  "success": true,
  "total_jobs": 156,
  "scene_jobs": 89,
  "instruction_jobs": 42,
  "strict_jobs": 25,
  "task_count": 12,
  "task_jobs": [
    {"id": 42, "title": "商超收银场景采集", "taskCategory": "scene", "jobCount": 30},
    {"id": 18, "title": "居家整理采集", "taskCategory": "scene", "jobCount": 25},
    {"id": 7,  "title": "指令任务A", "taskCategory": "instruction", "jobCount": 18},
    {"id": 35, "title": "严格质检任务", "taskCategory": "strict", "jobCount": 10}
  ]
}
```

### 工作流

1. 用户提出查看平台作业概览的意图：
   - "平台现在有多少作业？"
   - "帮我看看平台的作业情况"
   - "哪些任务有作业？"

2. 直接调用 `job_summary` 获取统计

3. 向用户汇报作业概览信息（用自然语言风格）：

   **汇报要点：**
   - 平台作业总数 → 开头点明
   - 分类统计 → 场景/指令/严格各有多少作业
   - 有作业的任务 → 提到有几个任务有作业，按数量从多到少列出
   - 按 `task_jobs` 中的 `jobCount` 降序排列汇报

   **推荐的口语化风格示例：**

   > 当前平台一共有 **156** 个作业，分布在 12 个任务中。
   >
   > 按任务分类来看：**场景任务**有 89 个作业，**指令任务**有 42 个，**严格任务**有 25 个。
   >
   > 作业量最多的任务是 **商超收银场景采集**（30 个作业），其次是 **居家整理采集**（25 个），**指令任务A** 有 18 个，**严格质检任务**有 10 个。

4. 如果用户想进一步了解某个有作业的任务详情，可结合 `task_detail` 或 `task_summary` 提供更详细的信息。

### 注意事项

- `job_summary` 基于任务列表接口返回的 `jobCount` 字段聚合，**不逐一查询每个作业的明细**
- 默认返回 200 条任务数据，覆盖绝大部分场景；若平台任务超过 200，可通过调整 `page_size` 扩展
- 统计口径：每个任务的 `jobCount` 由服务端维护，反映任务当前的作业数量
- 若需要查看**某个具体任务的作业详情**（如作业数、采集进度等），可结合 `task_detail` 进一步查询

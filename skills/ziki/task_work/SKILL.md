---
name: task-work
description: >
  Queries the Ziki platform task summary — total tasks, scene tasks, instruction
  tasks, strict tasks, and published task counts — via the `task_summary` MCP tool.
  Use when the user asks "how many tasks" or wants a platform-wide task overview.
tags: [zata, ziki, task-work, summary, statistics]
triggers:
  - user asks "平台有多少任务" / "how many tasks on the platform"
  - user asks "当前平台任务概要" / "task overview / task summary"
  - user asks "任务统计" / "task statistics"
  - user says "帮我看看平台的任务情况"
  - user asks about total / scene / instruction / strict / published task counts
  - user wants to know the distribution of task categories
---

# Task Work / 任务概览

## 用途

查询 Ziki 平台上当前任务的**概要统计信息**，包括：

- **任务总数（total）** — 平台上的任务总数量
- **场景任务数（scene_num）** — 分类为"场景"的任务数量（taskCategory = "scene"）
- **指令任务数（instruction_num）** — 分类为"指令"的任务数量（taskCategory = "instruction"）
- **严格任务数（strict_num）** — 分类为"严格"的任务数量（taskCategory = "strict"）
- **已发布任务数（issued）** — 已发布状态的任务数量（status = 2）

## 调用方式

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
    {"id": 2, "title": "指令任务A", "status": 1, "taskCategory": "instruction"},
    ...
  ]
}
```

## 工作流

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

如果用户想了解某个特定名称的任务统计：

```
task_summary(title="整理")
```

## 场景示例

| 用户提问 | 操作 | 回复要点 |
|----------|------|----------|
| "平台现在有多少任务？" | `task_summary()` | 显示总数及各分类统计 |
| "场景任务有多少？" | `task_summary()` → 取 `scene_num` | "当前有 65 个场景任务" |
| "已发布的任务有几个？" | `task_summary()` → 取 `issued` | "已发布 80 个任务" |
| "帮我查一下标题带'测试'的任务" | `task_summary(title="测试")` | 展示筛选后的统计及任务列表 |

## 注意事项

- 此工具为**只读查询**，不会修改任何数据
- `total` 取自服务器返回的元数据总量，若总量不可用则回退为返回列表长度
- 分类依据为 `taskCategory` 字段：`"scene"`=场景任务、`"instruction"`=指令任务、`"strict"`=严格任务
- 已发布状态判定依据 `status == 2`
- 默认返回 100 条任务概要，可通过 `page_size` 调整

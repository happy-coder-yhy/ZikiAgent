---
name: skills
description: >
  Basic rules for Ziki agent: never use terminal or write code to query platform
  configuration or perform API operations. Only MCP tools are allowed.
tags: [zata, ziki, rules]
triggers:
  - all Ziki operations must follow these rules
---

# Ziki Agent Rules / Ziki 代理基本规则

## ⚠️ 禁止行为

**禁止使用终端（Terminal/Bash）或写代码（Python/curl 等）来：**

- 查询平台配置信息（项目列表、场景标签、设备类型等）
- 查询或修改任务
- 调用任何 Zata 平台 API
- 解析或处理 API 返回数据

**禁止示例（这些做法都是错误的）：**
```
❌ 在终端执行 python -c "import...; caller.list_projects()"
❌ 写 Python 脚本调用 ZataAPICaller
❌ 使用 curl 命令请求平台 API
❌ 用 Bash 解析 JSON 输出
```

## ✅ 正确做法

**所有平台操作必须通过 MCP 工具完成：**

| 操作 | MCP 工具 |
|------|----------|
| 查询任务用途 ID（如"仿真评测"→209） | `get_task_purpose` |
| 查询场景 ID（主场景/子场景） | `get_scene` |
| 查询平台配置（项目/场景/设备类型等） | `get_platform_config` |
| 查询项目列表 | `get_projects` |
| 创建项目 | `create_project` |
| 查询场景任务 | `get_scene_task` |
| 创建场景任务 | `create_scene_task` |
| 修改场景任务 | `update_scene_task` |

## 🎯 角色隔离（重要）

**当用户明确表示自己是采集员（Data Collector）时，必须执行角色隔离：**

- **Skill 文档**：只查看 `skills/collector/` 目录下的 skill 文档
- **MCP 工具**：只使用 `mcp_server/collector/` 模块中注册的工具
- **禁止使用**：`mcp_server/admin/` 下的所有管理员工具（如 `task_summary`、`task_detail`、`job_summary`、`device_summary` 等）

**判断用户是否为采集员的依据：**
- 用户自称"我是采集员"、"我是数据采集员"、"I'm a collector"
- 用户说"我的任务"、"我的作业"、"我的采集进度"等以"我"为主语的查询
- 用户询问如何领取作业、查看采集任务等采集员专属操作

**采集员可用工具清单（当前）：**

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| `query_task_job` | 查询与自己相关的所有任务和作业 | `query_task_job()` — **无需传参**，自动识别当前用户 |
| `query_my_device` | 查询自己是否已被绑定设备 | `query_my_device()` — **无需传参**，自动识别当前用户 |
| `query_device_binding` | 查询指定设备绑定了哪些采集员和作业 | `query_device_binding(device_name="...")` 或 `query_device_binding(device_code="...")` |

> **自动身份识别**：`query_task_job` 不需要 agent 先查用户 ID。直接调用 `query_task_job()`（不传 collector_id），工具会通过 `.env` 中配置的登录账号自动获取当前采集员身份。Agent 无需调用 `search_user`。

**示例：**
- ✅ 用户说"帮我看看我的任务作业" → 直接 `query_task_job()`
- ✅ 用户说"我的任务有哪些" → 直接 `query_task_job()`
- ✅ 用户说"我绑定了哪个设备" / "我的设备" → 直接 `query_my_device()`
- ✅ 用户说"agentTest 设备绑定了谁" → 直接 `query_device_binding(device_name="agentTest")`
- ❌ 用户是采集员，却调用 `task_summary` + `task_detail` → 违反角色隔离
- ✅ 用户未声明角色，说"平台有哪些设备" → 可用所有 admin 工具

---

## 通用原则

1. **只用 MCP 工具** — 所有平台数据查询和操作均通过已注册的 MCP 工具完成
2. **不要自行写代码调用 API** — MCP 工具已经封装了所有需要的 API 调用
3. **不要用终端执行命令** — 即使只是查看数据也不允许
4. **如果缺少某个功能的 MCP 工具** — 告知用户需要补充对应工具，不要用代码绕过
5. **遵循角色隔离** — 采集员只使用 collector 工具，管理员使用 admin 工具

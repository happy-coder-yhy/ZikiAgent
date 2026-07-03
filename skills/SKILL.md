---
name: ziki-rules
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

## 通用原则

1. **只用 MCP 工具** — 所有平台数据查询和操作均通过已注册的 MCP 工具完成
2. **不要自行写代码调用 API** — MCP 工具已经封装了所有需要的 API 调用
3. **不要用终端执行命令** — 即使只是查看数据也不允许
4. **如果缺少某个功能的 MCP 工具** — 告知用户需要补充对应工具，不要用代码绕过

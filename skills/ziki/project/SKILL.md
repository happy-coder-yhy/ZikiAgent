---
name: project
description: >
  Manages Zata platform projects — list all projects with `get_projects`,
  or create new ones with `create_project`. 项目名称为必填，描述为选填。
tags: [zata, ziki, project, management]
triggers:
  - user asks "有哪些项目" / "show projects" / "list projects"
  - user wants to create a new project
  - user says "创建项目" / "create a project"
---

# Project / 项目管理

## 用途

管理 Zata 平台上的项目：
- **查询项目列表** — 查看当前账号下所有项目
- **创建新项目** — 在平台上创建新的项目

## 调用方式

### 查询项目列表

```
Tool: get_projects
Params:
  name: string      (optional)  — 按项目名称筛选
  page_num: int     (optional, default 1)
  page_size: int    (optional, default 100)
```

返回示例：
```json
{
  "success": true,
  "total": 2,
  "projects": [
    {"id": 1, "name": "项目A", "description": "描述"},
    {"id": 2, "name": "项目B", "description": null}
  ]
}
```

### 创建新项目

```
Tool: create_project
Required Params:
  name: string        — 项目名称（必填，用户未提供时必须先询问）
Optional Params:
  description: string — 项目描述（选填，用户未提供时先询问再创建）
```

返回示例：
```json
{
  "success": true,
  "status_code": 200,
  "data": {"id": 10, "name": "新项目", ...}
}
```

## 工作流

### 查询项目列表
- 用户问"有哪些项目" → 直接调用 `get_projects`
- 用户问"有叫XX的项目吗" → 调用 `get_projects(name="XX")`
- 若返回项目列表为空，告知用户当前没有匹配的项目

### 创建新项目
1. 用户提出创建意图时，先确认项目名称：
   - 用户已提供名称 → 使用该名称
   - 用户未提供名称 → **必须向用户询问**"项目名称是什么？"
2. 询问项目描述（可选）：
   - 询问用户"是否需要添加项目描述？"
   - 用户提供 → 传入 description
   - 用户明确表示不需要 → 不传 description
3. 调用 `create_project` 创建项目
4. 返回创建结果给用户

## 注意

- 项目名称是唯一必填字段，用户未提供时必须追问，不能使用默认值
- 描述是选填字段，但也应主动询问用户，用户明确表示不需要时才跳过
- 创建成功后 data 中包含新项目的 id

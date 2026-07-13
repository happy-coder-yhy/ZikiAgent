---
name: collector-device
description: >
  Query whether the current logged-in collector is bound to any device on the
  Zata platform via the `query_my_device` MCP tool. Returns device details
  (code, name, model, category, status, bound job) when bound, or a clear
  "not bound" message otherwise.
tags: [zata, ziki, collector, query-my-device]
triggers:
  - user identifies as 采集员 / collector / data collector
  - user says "我的设备" / "my device"
  - user says "我绑定了哪个设备" / "which device am I bound to"
  - user says "我被分配到哪个设备" / "what device is assigned to me"
  - user asks "查一下我的设备" / "check my device"
  - user says "我有设备吗" / "do I have a device"
  - user wants to know if they are bound to any device
---

# Collector Device Binding / 采集员设备绑定查询

## ⚠️ 角色隔离

**当用户声明自己是采集员时，本 skill 是唯一应被使用的 skill 文档。** 采集员只能使用 `mcp_server/collector/` 模块下的工具，不得使用管理员工具。参见 [总规则](../../SKILL.md)。

## 用途

查询当前登录采集员在 Zata 平台上**是否已被绑定设备**，并返回绑定设备的详细信息。

| 工具 | 用途 |
|------|------|
| `query_my_device` | 查询当前采集员的设备绑定状态 |

---

## 调用方式

```
Tool: query_my_device
Params:
  - collector_id: string  — 采集员用户 ID（可选）。不传则自动获取当前登录用户。
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `collector_id` | string | 否 | 采集员的用户 ID。**不传则自动通过当前登录用户获取**，适用于采集员直接说"我的设备"的场景。 |

> **自动身份识别**：MCP 服务器已通过 `.env` 配置的账号密码登录。调用 `query_my_device()`（不传参）时，工具会自动调用 `userinfo` 接口获取当前登录用户的 ID，无需 agent 手动查找。

---

## 返回字段

### 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `bound` | bool | 是否已绑定设备 |
| `collector_id` | string | 采集员 ID |
| `count` | int | 绑定的设备数量（仅 bound=true 时） |
| `message` | string | 人类可读的结果描述 |
| `devices` | array | 绑定的设备列表（见下方） |

### devices[]（设备条目）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 设备 ID |
| `deviceCode` | string | 设备编码（唯一标识） |
| `deviceName` | string | 设备名称 |
| `deviceTypeName` | string | 设备类型名称 |
| `deviceBodyName` | string | 设备机身型号 |
| `category` | string | 设备类别（robot=真机, video=视频） |
| `categoryLabel` | string | 设备类别中文标签 |
| `status` | int | 设备状态码（0=离线, 1=在线） |
| `statusLabel` | string | 设备状态中文标签 |
| `collectorId` | string | 绑定的采集员 ID |
| `jobId` | int | 绑定的作业 ID（可能为空） |

---

## 查询工作流

1. 用户表达查看自己设备绑定情况的意图（如"我绑定了哪个设备？"）
2. **无需查找 collector_id** — 直接调用 `query_my_device()`（不传参），工具自动获取当前用户身份
3. 解读返回结果，向用户汇报：
   - 若 `bound=true`：展示设备名称、型号、在线状态、绑定的作业等
   - 若 `bound=false`：告知用户"您当前暂未绑定任何设备"

> **仅在查询其他采集员时**才需要显式传入 `collector_id`：先通过 `search_user(name="用户名")` 查询 ID，再调用 `query_my_device(collector_id="...")`。

---

## 场景示例

### 示例 1：查看我的设备（自动识别）

用户："帮我看看我绑定了哪个设备"

→ 直接调用 `query_my_device()`（不传参，自动获取当前用户）
→ 返回（有绑定）：
```json
{
  "success": true,
  "bound": true,
  "collector_id": "6e1465a8-...",
  "count": 1,
  "message": "当前采集员已绑定 1 台设备",
  "devices": [
    {
      "id": 42,
      "deviceCode": "dunjia_device001",
      "deviceName": "遁甲测试设备1号",
      "deviceTypeName": "Android",
      "deviceBodyName": "Xiaomi 14",
      "category": "robot",
      "categoryLabel": "真机",
      "status": 1,
      "statusLabel": "在线",
      "collectorId": "6e1465a8-...",
      "jobId": 12345
    }
  ]
}
```

### 示例 2：暂无绑定设备

用户："我有设备吗？"

→ 同上流程，返回：
```json
{
  "success": true,
  "bound": false,
  "collector_id": "6e1465a8-...",
  "message": "当前采集员暂未绑定任何设备",
  "devices": []
}
```

→ Agent 应告知用户："您当前暂未绑定任何设备。如需绑定，请联系管理员。"

### 示例 3：查询其他采集员的设备

用户："帮我查一下采集员张三绑定了什么设备"

→ 先调用 `search_user(name="张三")` 获取 collector_id
→ 再调用 `query_my_device(collector_id="<id>")`

---

## 注意事项

- `collector_id` 必须是用户 ID（UUID 格式），不是用户名或显示名称
- 一个采集员可以绑定多台设备（虽然通常只绑定一台）
- `jobId` 可能为 `null`，表示设备尚未绑定作业
- 设备绑定由管理员通过 `bind_collector_or_job` 或 `change_bind` 操作完成
- 采集员无法自行绑定/解绑设备，只能查询

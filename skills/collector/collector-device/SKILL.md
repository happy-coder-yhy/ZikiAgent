---
name: collector-device
description: >
  Query device binding information on the Zata platform via the `query_my_device`
  and `query_device_binding` MCP tools. `query_my_device` checks which device is
  bound to the current collector. `query_device_binding` looks up a specific
  device's bound collectors and jobs.
tags: [zata, ziki, collector, query-my-device, query-device-binding]
triggers:
  - user identifies as 采集员 / collector / data collector
  - user says "我的设备" / "my device"
  - user says "我绑定了哪个设备" / "which device am I bound to"
  - user says "我被分配到哪个设备" / "what device is assigned to me"
  - user asks "查一下我的设备" / "check my device"
  - user says "我有设备吗" / "do I have a device"
  - user wants to know if they are bound to any device
  - user asks "xx设备的绑定情况" / "what is bound to device xx"
  - user says "xx设备绑定了谁" / "who is bound to device xx"
  - user asks "查看xx设备的采集员和作业" / "check device xx collectors and jobs"
---

# Collector Device Binding / 采集员设备绑定查询

## ⚠️ 角色隔离

**当用户声明自己是采集员时，本 skill 是唯一应被使用的 skill 文档。** 采集员只能使用 `mcp_server/collector/` 模块下的工具，不得使用管理员工具。参见 [总规则](../../SKILL.md)。

## 用途

查询 Zata 平台上的设备绑定信息，提供两个工具分别满足不同查询场景：

| 工具 | 用途 |
|------|------|
| `query_my_device` | 查询**当前采集员**被绑定到哪些设备 |
| `query_device_binding` | 查询**指定设备**绑定了哪些采集员和作业 |

---

## query_my_device — 查询我的设备

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

## query_device_binding — 查询指定设备绑定情况

查询**指定设备**当前绑定的采集员和作业详情。

### 调用方式

```
Tool: query_device_binding
Params:
  - device_name: string  — 设备名称（模糊匹配），如 "agentTest"、"dunjia"
  - device_code: string  — 设备编码（精确匹配），如 "dunjia_device001"
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_name` | string | 二选一 | 设备名称，支持模糊匹配。与 `device_code` 至少提供一个 |
| `device_code` | string | 二选一 | 设备编码，精确匹配。同时提供时优先使用 `device_code` |

### 返回字段

#### 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `found` | bool | 是否找到设备 |
| `device` | object | 设备基本信息（见下方） |
| `binding` | object | 绑定信息（见下方） |
| `has_binding` | bool | 是否有任何绑定 |
| `message` | string | 人类可读的结果描述 |

#### device（设备基本信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 设备 ID |
| `deviceCode` | string | 设备编码（唯一标识） |
| `deviceName` | string | 设备名称 |
| `deviceTypeName` | string | 设备类型名称 |
| `deviceBodyName` | string | 设备机身型号 |
| `category` | string | 设备类别（robot/video） |
| `categoryLabel` | string | 设备类别中文标签 |
| `status` | int | 状态码（0=离线, 1=在线） |
| `statusLabel` | string | 状态中文标签 |

#### binding（绑定信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `collector` | object\|null | 绑定的采集员信息（见下方），无绑定时为 null |
| `job` | object\|null | 绑定的作业信息（见下方），无绑定时为 null |

#### binding.collector（采集员信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 采集员用户 ID |
| `name` | string\|null | 采集员用户名（可能为 null，仅能查到 ID） |
| `displayName` | string\|null | 采集员显示名称 |

#### binding.job（作业信息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 作业 ID |
| `name` | string | 作业名称 |
| `description` | string | 作业描述 |
| `collectStatus` | int | 采集状态码（0=未分配, 1=已分配, 2=已领取） |
| `taskId` | int | 所属任务 ID |
| `progress` | object | 作业进度（normalCollect, normalCollectTotal 等） |

### 查询工作流

1. 用户表达查看某设备绑定情况的意图（如"agentTest 设备绑定了谁？"）
2. 若用户提供了设备名称 → 调用 `query_device_binding(device_name="agentTest")`
3. 若用户提供了设备编码 → 调用 `query_device_binding(device_code="xxx")`
4. 若返回 `multiple=true`（多个匹配）→ 列出匹配设备让用户选择，再用 `device_code` 精确查询
5. 解读结果，向用户汇报绑定情况

### 场景示例

#### 示例 1：按名称查询

用户："帮我看看 agentTest 这台设备绑定了谁"

→ 调用 `query_device_binding(device_name="agentTest")`
→ 返回：
```json
{
  "success": true,
  "found": true,
  "device": {
    "id": 42,
    "deviceCode": "dunjia_device001",
    "deviceName": "agentTest",
    "deviceTypeName": "Android",
    "deviceBodyName": "Xiaomi 14",
    "category": "robot",
    "categoryLabel": "真机",
    "status": 1,
    "statusLabel": "在线"
  },
  "binding": {
    "collector": {
      "id": "6e1465a8-...",
      "name": "zhangsan",
      "displayName": "张三"
    },
    "job": {
      "id": 12345,
      "name": "数据采集-第一批",
      "description": "采集首页数据",
      "collectStatus": 2,
      "taskId": 261,
      "progress": {
        "normalCollect": 45,
        "normalCollectTotal": 100
      }
    }
  },
  "has_binding": true,
  "message": "设备「agentTest」当前绑定：采集员 zhangsan、作业「数据采集-第一批」"
}
```

#### 示例 2：设备未绑定任何对象

用户："查一下 device001 的绑定情况"

→ 调用 `query_device_binding(device_code="device001")`
→ 返回：
```json
{
  "success": true,
  "found": true,
  "device": { "...": "..." },
  "binding": {
    "collector": null,
    "job": null
  },
  "has_binding": false,
  "message": "设备「device001」当前未绑定任何采集员或作业"
}
```

#### 示例 3：多个匹配

用户："dunjia 设备的绑定情况"

→ 调用 `query_device_binding(device_name="dunjia")`
→ 返回 `multiple=true`，列出 3 台匹配设备
→ Agent 展示列表，用户选择 → 再用 `device_code` 精确查询

---

## 注意事项

- `device_name` 支持模糊匹配，可能返回多个结果；`device_code` 精确匹配唯一设备
- `binding.collector.name` 可能为 `null`（仅能查到 ID 时），但仍会返回 `id`
- `binding.job` 为 `null` 表示设备未绑定作业
- `has_binding` 为 `false` 表示设备当前无任何绑定，`collector` 和 `job` 均为 `null`
- 采集员无法自行绑定/解绑设备，只能查询
- 设备绑定由管理员通过 `bind_collector_or_job` 或 `change_bind` 操作完成

---
name: collector-device
description: >
  Query and manage device binding on the Zata platform via `query_my_device`,
  `query_device_binding`, `bind_job_to_device`, and `bind_self_to_device` MCP tools.
tags: [zata, ziki, collector, query-my-device, query-device-binding, bind-job-to-device, bind-self-to-device]
triggers:
  - user identifies as 采集员 / collector / data collector
  - user says "我的设备" / "my device"
  - user says "我绑定了哪个设备" / "which device am I bound to"
  - user asks "查一下我的设备" / "check my device"
  - user asks "xx设备的绑定情况" / "what is bound to device xx"
  - user asks "查看xx设备的采集员和作业" / "check device xx collectors and jobs"
  - user says "给xx设备更换绑定xx作业" / "rebind device xx to job yy"
  - user says "把xx设备绑定到xx作业" / "bind device xx to job yy"
  - user says "xx设备切换作业" / "switch job for device xx"
  - user says "把xx设备绑定给我" / "bind device xx to me"
  - user says "让我来操作xx设备" / "let me operate device xx"
  - user says "更换xx设备的采集员为我" / "change device xx collector to me"
---

# Collector Device Binding / 采集员设备绑定查询

## ⚠️ 角色隔离

**当用户声明自己是采集员时，本 skill 是唯一应被使用的 skill 文档。** 采集员只能使用 `mcp_server/collector/` 模块下的工具，不得使用管理员工具。参见 [总规则](../../SKILL.md)。

## 用途

查询和管理 Zata 平台上的设备绑定信息，提供四个工具：

| 工具 | 用途 |
|------|------|
| `query_my_device` | 查询**当前采集员**被绑定到哪些设备 |
| `query_device_binding` | 查询**指定设备**绑定了哪些采集员和作业 |
| `bind_job_to_device` | 将指定设备**更换绑定**到当前采集员有权限的作业 |
| `bind_self_to_device` | 将指定设备的**采集员更换为自己** |

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

## bind_job_to_device — 更换设备绑定的作业

采集员将自己有权限的作业绑定到指定设备。工具自动验证采集员对目标作业的访问权限，
仅允许绑定采集员已领取或被分配到的作业。

### 调用方式

```
Tool: bind_job_to_device
Params:
  - device_name: string   — 设备名称（模糊匹配），与 device_code 二选一
  - device_code: string   — 设备编码（精确匹配），与 device_name 二选一
  - job_description: string — 作业名称或描述（模糊匹配），与 job_id 二选一
  - job_id: string        — 作业 ID（精确匹配），与 job_description 二选一
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_name` | string | 二选一 | 设备名称，支持模糊匹配 |
| `device_code` | string | 二选一 | 设备编码，精确匹配。同时提供时优先使用 |
| `job_description` | string | 二选一 | 作业名称或描述，在采集员可访问的作业中模糊搜索 |
| `job_id` | string | 二选一 | 作业 ID，精确匹配。同时提供时优先使用 |

> **自动身份识别**：工具自动通过 `.env` 登录账号获取当前采集员身份，无需手动传入 collector_id。

### 权限验证

工具会自动构建采集员的**可访问作业目录**，包括：
1. **已领取的作业**（通过 `job-receives` 接口）
2. **已分配任务的作业**（通过 `list_tasks` + 任务下 `list_jobs`）

仅当目标作业在可访问目录中时，才允许执行换绑操作。

### 返回字段

#### 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `device` | object | 设备基本信息（id, deviceCode, deviceName） |
| `previous_job_id` | int\|null | 换绑前的作业 ID |
| `bound` | object | 新的绑定信息（collector_id, job_id） |
| `message` | string | 人类可读的操作结果描述 |

#### 多匹配场景（作业模糊搜索）

当 `job_description` 匹配到多个作业时：

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | true |
| `multiple_jobs` | bool | true |
| `count` | int | 匹配数量 |
| `message` | string | 提示用户缩小范围 |
| `jobs` | array | 匹配的作业列表（jobId, name, description, taskId） |

### 查询工作流

1. 用户表达更换设备作业的意图（如"给 agentTest 更换绑定真机作业"）
2. 若用户提到了作业名称/描述 → `bind_job_to_device(device_name="agentTest", job_description="真机")`
3. 若用户提到了作业 ID → `bind_job_to_device(device_code="xxx", job_id="132")`
4. 若返回 `multiple_jobs=true` → 列出匹配作业让用户选择，再用 `job_id` 精确指定
5. 若返回权限错误 → 告知用户该作业不在其可访问范围

### 场景示例

#### 示例 1：按作业描述换绑

用户："给 agentTest 设备更换绑定真机作业测试那个作业"

→ 调用 `bind_job_to_device(device_name="agentTest", job_description="真机作业测试")`
→ 权限验证通过，返回：
```json
{
  "success": true,
  "device": {
    "id": 6,
    "deviceCode": "dunjia_device001",
    "deviceName": "agentTest"
  },
  "previous_job_id": 136,
  "bound": {
    "collector_id": "27b5f00f-...",
    "job_id": 132
  },
  "message": "设备「agentTest」已解绑旧作业；已绑定作业「hhh」"
}
```

#### 示例 2：按作业 ID 换绑

用户："把 agentTest 绑定到作业 132"

→ 调用 `bind_job_to_device(device_name="agentTest", job_id="132")`
→ 权限验证通过，直接换绑

#### 示例 3：权限不足

用户："给 agentTest 换绑作业 999"

→ 调用 `bind_job_to_device(device_name="agentTest", job_id="999")`
→ 返回：
```json
{
  "success": false,
  "error": "作业 #999 不在您的可访问范围内，该作业您暂无权限"
}
```

→ Agent 应告知用户："抱歉，作业 #999 您暂无权限。您只能绑定自己已领取或被分配到的作业。"

#### 示例 4：多个匹配

用户："给 agentTest 换绑 hhh 作业"

→ 调用 `bind_job_to_device(device_name="agentTest", job_description="hhh")`
→ 返回 `multiple_jobs=true`，列出 2 个匹配作业
→ Agent 展示列表，用户选择 → 再用 `job_id` 精确指定

---

## bind_self_to_device — 将设备采集员更换为自己

采集员将自己绑定到指定设备上。工具自动识别当前采集员身份并完成换绑，
设备的作业绑定不受影响。

### 调用方式

```
Tool: bind_self_to_device
Params:
  - device_name: string  — 设备名称（模糊匹配），与 device_code 二选一
  - device_code: string  — 设备编码（精确匹配），与 device_name 二选一
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `device_name` | string | 二选一 | 设备名称，支持模糊匹配 |
| `device_code` | string | 二选一 | 设备编码，精确匹配。同时提供时优先使用 |

> **自动身份识别**：工具自动通过 `.env` 登录账号获取当前采集员身份，无需手动传入 collector_id。

### 返回字段

#### 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `already_bound` | bool | 是否已经绑定到自己（幂等检查），仅 success=true 时出现 |
| `device` | object | 设备基本信息（id, deviceCode, deviceName） |
| `previous_collector_id` | string\|null | 换绑前的采集员 ID（null 表示之前无绑定） |
| `bound` | object | 新的绑定信息（collector_id, job_id） |
| `message` | string | 人类可读的操作结果描述 |

### 操作工作流

1. 用户表达换绑采集员的意图（如"把 agentTest 绑定给我"）
2. 若用户提供了设备名称 → `bind_self_to_device(device_name="agentTest")`
3. 若用户提供了设备编码 → `bind_self_to_device(device_code="dunjia_device001")`
4. 工具自动完成：
   - 查找设备
   - 检查是否已绑定自己（是则直接返回，幂等）
   - 解绑旧采集员 → 绑定自己
5. 解读结果，向用户汇报

### 场景示例

#### 示例 1：将设备绑定给自己

用户："把 agentTest 设备的采集员换成我"

→ 调用 `bind_self_to_device(device_name="agentTest")`
→ 返回：
```json
{
  "success": true,
  "device": {
    "id": 6,
    "deviceCode": "dunjia_device001",
    "deviceName": "agentTest"
  },
  "previous_collector_id": "old-collector-uuid",
  "bound": {
    "collector_id": "27b5f00f-...",
    "job_id": 136
  },
  "message": "设备「agentTest」已解绑旧采集员；已绑定采集员「collector」"
}
```

#### 示例 2：已经绑定到自己（幂等）

用户："让我来操作 agentTest"

→ 调用 `bind_self_to_device(device_name="agentTest")`
→ 设备已绑定到当前采集员，返回：
```json
{
  "success": true,
  "already_bound": true,
  "device": { "id": 6, "deviceCode": "dunjia_device001", "deviceName": "agentTest" },
  "bound": { "collector_id": "27b5f00f-...", "job_id": 136 },
  "message": "设备「agentTest」已绑定到您（collector），无需重复操作"
}
```

#### 示例 3：多个匹配

用户："把 dunjia 设备绑定给我"

→ 调用 `bind_self_to_device(device_name="dunjia")`
→ 返回 `multiple_devices=true`，列出所有匹配设备
→ Agent 展示列表，用户选择 → 再用 `device_code` 精确指定

---

## 注意事项

- `device_name` 支持模糊匹配，可能返回多个结果；`device_code` 精确匹配唯一设备
- `binding.collector.name` 可能为 `null`（仅能查到 ID 时），但仍会返回 `id`
- `binding.job` 为 `null` 表示设备未绑定作业
- `has_binding` 为 `false` 表示设备当前无任何绑定，`collector` 和 `job` 均为 `null`
- `bind_job_to_device` 只能绑定采集员**自己有权限的作业**（已领取或被分配到的）
- `bind_self_to_device` 会保留设备的当前作业绑定，仅更换采集员
- `bind_self_to_device` 是幂等操作：已绑定到自己时直接返回成功，不会重复绑定
- `job_description` 匹配时同时搜索作业的 `name` 和 `description` 字段，大小写不敏感
- 采集员只能更换作业绑定，不能更换采集员绑定（采集员绑定由管理员操作）
- 管理员的设备管理工具（`bind_collector_or_job`、`change_bind`）不受此权限限制

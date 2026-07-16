---
name: device
description: >
  Query device summary, details, and manage device bindings on the Zata platform
  via MCP tools. Use `device_summary` for overview, `device_detail` for specific
  device info, `bind_collector_or_job` to bind a collector/job to a device, and
  `change_bind` to rebind.
tags: [zata, ziki, device, device-summary, device-detail, device-bind]
triggers:
  - user says "查询设备概要" / "query device summary"
  - user says "查看设备" / "check devices"
  - user says "设备状态" / "device status"
  - user asks about platform device counts, online/offline status
  - user wants a summary of all devices
  - user says "查询设备详情" / "device detail"
  - user asks about a specific device's information
  - user mentions a device name and wants to see its details
  - user says "查一下XX设备" / "look up device XX"
  - user wants to look up a device by its code
  - user says "绑定" + "设备" / "bind" + "device"
  - user wants to assign a collector or job to a device
  - user says "给XX设备绑定" / "为XX设备分配"
  - user says "重新绑定" / "rebind" / "change binding"
  - user wants to replace a device's collector or job
---

# Device / 设备管理

## 用途

查询 Zata 平台上设备的**概要统计**、**详细信息**，以及**管理设备绑定**（采集员/作业）。

| 操作 | MCP 工具 | 说明 |
|------|----------|------|
| **设备概要** | `device_summary` | 查询设备总数、在线/离线、真机/视频、各型号数量 |
| **设备详情** | `device_detail` | 按名称或编码查询单台设备的完整信息 |
| **绑定采集员/作业** | `bind_collector_or_job` | 将采集员或作业绑定到设备 |
| **重新绑定** | `change_bind` | 先解绑当前采集员/作业，再绑定新的 |

---

## 一、设备概要查询

### 调用方式

```
Tool: device_summary
Required Params: 无
```

### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | int | 设备总数 |
| `online` | int | 在线设备数（status=1） |
| `offline` | int | 离线设备数（status≠1） |
| `real_device` | int | 真机设备数（category=robot） |
| `video_device` | int | 视频设备数（category=video） |
| `by_model` | dict | 各设备型号对应的设备数，key 为 deviceBodyName（或 deviceTypeName） |

### 查询工作流

1. 用户表达查看设备概要的意图（如"看看平台上有多少设备"）
2. 调用 `device_summary`（无需任何参数）
3. 向用户展示统计结果

---

## 二、设备详情查询

### 调用方式

```
Tool: device_detail
Params（二选一）:
  - name: string         — 设备名称（支持模糊匹配），如 "agentTest"
  - device_code: string  — 设备编码，直接查询详情
```

### 查询工作流

1. 用户提出查看某设备详情（如"帮我查一下 agentTest 设备的详细信息"）
2. 调用 `device_detail(name="agentTest")` 搜索设备
3. 根据返回结果处理：
   - **未找到（found=false）**：告知用户该设备不存在
   - **唯一匹配**：展示 `device` 中的完整信息
   - **多个匹配（multiple=true）**：列出所有匹配设备，让用户选择后调用 `device_detail(device_code="...")`

---

## 三、绑定采集员或作业

### 调用方式

```
Tool: bind_collector_or_job
Required Params:
  - device_code: string   — 设备编码（必填），如 "dunjia_device001"
Optional Params（至少提供一个）:
  - collector_id: string  — 采集员用户 ID，通过 search_user(name="用户名") 获取
  - job_id: string        — 作业 ID，通过 job_summary / job_detail 获取
```

### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `message` | string | 操作结果描述 |
| `device_code` | string | 设备编码 |
| `bound.collector_id` | string\|null | 绑定的采集员 ID |
| `bound.job_id` | string\|null | 绑定的作业 ID |

### 绑定工作流

1. 用户表达绑定意图（如"给 agentTest 设备绑定小明采集员"）
2. **若用户提到采集员用户名**：先调用 `search_user(name="小明")` 查询 userId
3. **若用户提到作业描述**：先调用 `job_summary` 或 `job_detail` 查询 jobId
4. 确认 device_code（若用户只给了设备名，先调 `device_detail(name="...")` 获取 deviceCode）
5. 调用 `bind_collector_or_job(device_code="...", collector_id="...", job_id="...")`
6. 向用户确认绑定结果

> **Merge 行为**：未传 `collector_id` 或 `job_id` 时，工具会自动保留设备现有的绑定值，不会覆盖。
> 例如：设备已有采集员 A，调用 `bind_collector_or_job(device_code="x", job_id="2")` 仅传 job_id，
> 工具读取到设备当前 collectorId=A，最终将同时绑定采集员 A + 作业 2。

### 示例

用户："给 dunjia_device001 绑定采集员小明"
→ 先调 `search_user(name="小明")` 得到 userId: `6e1465a8-...`
→ 再调 `bind_collector_or_job(device_code="dunjia_device001", collector_id="6e1465a8-...")`
→ 返回 `{"success": true, "message": "已为设备「dunjia_device001」绑定采集员 6e1465a8-..."}`

用户（后续）："再绑定作业 JOB-001"
→ 直接调 `bind_collector_or_job(device_code="dunjia_device001", job_id="JOB-001")`
→ 工具自动保留采集员，返回 `{"success": true, "message": "已为设备「dunjia_device001」绑定采集员 6e1465a8-...、作业 JOB-001"}`

---

## 四、重新绑定（先解绑再绑定）

### 调用方式

```
Tool: change_bind
Required Params:
  - device_code: string   — 设备编码（必填）
Optional Params（至少提供一个）:
  - collector_id: string  — 新采集员用户 ID
  - job_id: string        — 新作业 ID
```

### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `message` | string | 操作结果描述（含解绑和绑定信息） |
| `device_code` | string | 设备编码 |
| `unbound.collector_id` | string\|null | 被解绑的采集员 ID |
| `unbound.job_id` | string\|null | 被解绑的作业 ID |
| `bound.collector_id` | string\|null | 新绑定的采集员 ID |
| `bound.job_id` | string\|null | 新绑定的作业 ID |

### 重新绑定工作流

1. 用户表达重新绑定意图（如"把 agentTest 设备的采集员换成小王"）
2. **查询新采集员/作业 ID**：通过 `search_user` 或 `job_summary` / `job_detail`
3. 确认 device_code
4. 调用 `change_bind(device_code="...", collector_id="新ID", job_id="新ID")`
   - 工具内部自动执行：解绑当前 → 绑定新值
5. 向用户展示解绑和绑定结果

> **Merge 行为**：只解绑并替换用户明确提供的字段。未传的字段保留现有值。
> 例如：设备已有采集员 A + 作业 1，调用 `change_bind(device_code="x", collector_id="B")` 仅更换采集员，
> 工具解绑采集员 A → 绑定采集员 B，作业 1 保持不变。

### 与 bind_collector_or_job 的区别

| 场景 | 用哪个工具 |
|------|-----------|
| 设备当前**没有**绑定采集员/作业 | `bind_collector_or_job` |
| 设备当前**已有**绑定，需要**换人/换作业** | `change_bind` |
| 不确定设备当前状态 | 先用 `device_detail` 查看，再决定 |

`change_bind` 会先解绑旧的再绑定新的，确保绑定切换干净。`bind_collector_or_job` 直接绑定新值。

> **简便用法**：两个工具都支持 merge 行为。如果分步绑定（先绑采集员、再绑作业），
> 直接用 `bind_collector_or_job` 分别调用即可，无需特意用 `change_bind`。

---

## 通用注意

- `device_summary` 无需任何参数，一次调用即可获取全量统计
- `device_detail` 先按 deviceName 搜索，无结果时自动回退到按 deviceCode 搜索
- 设备状态：`1` = 在线，`0`（及其他值）= 离线
- 设备类别：`robot` = 真机采集设备，`video` = 视频采集设备
- 型号统计优先使用 `deviceBodyName`，若为空则回退到 `deviceTypeName`
- **采集员 ID 必须通过 `search_user(name="用户名")` 查询获取**，不要硬编码或猜测
- **作业 ID 通过 `job_summary` 或 `job_detail` 查询获取**
- **device_code 可通过 `device_detail(name="设备名")` 查询获取**

---
name: device
description: >
  Query device summary and details on the Zata platform via MCP tools.
  Use `device_summary` for an overview of all devices, and `device_detail`
  to look up detailed information for a specific device by name or code.
tags: [zata, ziki, device, device-summary, device-detail]
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
---

# Device / 设备管理

## 用途

查询 Zata 平台上设备的**概要统计**和**详细信息**。

| 操作 | MCP 工具 | 说明 |
|------|----------|------|
| **设备概要** | `device_summary` | 查询设备总数、在线/离线、真机/视频、各型号数量 |
| **设备详情** | `device_detail` | 按名称或编码查询单台设备的完整信息 |

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

### 示例输出

```json
{
  "success": true,
  "total": 15,
  "online": 10,
  "offline": 5,
  "real_device": 3,
  "video_device": 12,
  "by_model": {
    "dunjia_device001": 5,
    "iPhone 15": 3,
    "摄像头设备A": 7
  }
}
```

---

## 二、设备详情查询

### 调用方式

```
Tool: device_detail
Params（二选一）:
  - name: string         — 设备名称（支持模糊匹配），如 "agentTest"
  - device_code: string  — 设备编码，直接查询详情
```

### 查询模式

| 模式 | 参数 | 行为 |
|------|------|------|
| **按名称搜索** | `name="agentTest"` | 先搜 deviceName → 无结果则搜 deviceCode |
| **按编码直查** | `device_code="dunjia_device001"` | 跳过搜索，直接返回该设备完整详情 |

### 返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否成功 |
| `found` | bool | 是否找到匹配设备 |
| `device` | object | 设备完整信息（单台匹配时返回） |
| `devices` | array | 匹配设备列表（多台匹配时返回摘要） |
| `multiple` | bool | 是否有多个同名设备 |
| `count` | int | 匹配设备数量 |

`device` 对象包含的字段：`id`, `deviceCode`, `deviceName`, `deviceTypeId`, `deviceTypeName`, `category`, `deviceBodyId`, `deviceBodyName`, `deviceEndId`, `deviceEndName`, `deviceCameraId`, `deviceCameraName`, `modules`, `ip`, `cameraConfig`, `jobId`, `status`, `lastOnlineAt`, `createdAt`, `updatedAt` 等。

### 查询工作流

1. 用户提出查看某设备详情（如"帮我查一下 agentTest 设备的详细信息"）
2. 调用 `device_detail(name="agentTest")` 搜索设备
3. 根据返回结果处理：
   - **未找到（found=false）**：告知用户该设备不存在
   - **唯一匹配（multiple 不存在或为 false）**：展示 `device` 中的完整信息
   - **多个匹配（multiple=true）**：列出 `devices` 中所有设备，让用户选择具体要查哪个
4. 若多个匹配，用户选定后，调用 `device_detail(device_code="<deviceCode>")` 获取详情

### 多设备匹配处理

当名称匹配到多台设备时，返回示例：

```json
{
  "success": true,
  "found": true,
  "multiple": true,
  "count": 3,
  "message": "找到 3 台匹配「camera」的设备，请根据 deviceCode 指定要查询的设备：device_detail(device_code=\"<deviceCode>\")",
  "devices": [
    {
      "deviceCode": "cam_001",
      "deviceName": "摄像头A",
      "deviceTypeName": "hikvision_ds2",
      "category": "video",
      "status": "在线"
    },
    {
      "deviceCode": "cam_002",
      "deviceName": "摄像头B",
      "deviceTypeName": "hikvision_ds2",
      "category": "video",
      "status": "离线"
    }
  ]
}
```

**处理方式**：将设备列表展示给用户，让用户根据 deviceCode 或 deviceName 选择具体设备，然后调用 `device_detail(device_code="<选定设备的deviceCode>")` 获取完整详情。

### 唯一匹配时的示例输出

```json
{
  "success": true,
  "found": true,
  "device": {
    "id": 6,
    "deviceCode": "dunjia_device001",
    "deviceName": "agentTest",
    "deviceTypeName": "dunjia_device001",
    "category": "video",
    "status": 0,
    "lastOnlineAt": "2026-07-03 10:34:23",
    "createdAt": "2026-07-03 18:32:21",
    "updatedAt": "2026-07-09 17:07:31",
    ...
  }
}
```

---

## 通用注意

- `device_summary` 无需任何参数，一次调用即可获取全量统计
- `device_detail` 先按 deviceName 搜索，无结果时自动回退到按 deviceCode 搜索
- 设备状态：`1` = 在线，`0`（及其他值）= 离线
- 设备类别：`robot` = 真机采集设备，`video` = 视频采集设备
- 型号统计优先使用 `deviceBodyName`，若为空则回退到 `deviceTypeName`

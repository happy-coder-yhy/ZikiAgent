---
name: device
description: >
  Query device summary on the Zata platform via MCP tool. Use `device_summary`
  to get an overview of all devices — total count, online/offline, real/video,
  and per-model breakdown.
tags: [zata, ziki, device, device-summary]
triggers:
  - user says "查询设备概要" / "query device summary"
  - user says "查看设备" / "check devices"
  - user says "设备状态" / "device status"
  - user asks about platform device counts, online/offline status
  - user wants a summary of all devices
---

# Device / 设备管理

## 用途

查询 Zata 平台上**所有设备**的概要统计信息，快速了解设备整体状况。

| 操作 | MCP 工具 | 说明 |
|------|----------|------|
| **设备概要** | `device_summary` | 查询设备总数、在线/离线、真机/视频、各型号数量 |

---

## 设备概要查询

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
3. 向用户展示统计结果：
   - 设备总数，其中在线 X 台、离线 Y 台
   - 真机设备 X 台，视频设备 Y 台
   - 各型号设备数量明细

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

## 通用注意

- `device_summary` 无需任何参数，一次调用即可获取全量统计
- 设备状态：`1` = 在线，`0`（及其他值）= 离线
- 设备类别：`robot` = 真机采集设备，`video` = 视频采集设备
- 型号统计优先使用 `deviceBodyName`，若为空则回退到 `deviceTypeName`

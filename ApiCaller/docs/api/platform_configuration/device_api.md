# Device API / 设备管理 API

设备管理包括设备类型和设备列表。采集任务类型不应和采集设备类型混淆：严格任务/场景任务是 `Collection Task` 的定义方式；真机或视频采集与使用的采集设备和采集方式相关。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 查询设备类型 | `GET` | `/api/zata-manager/device-types` | `list_device_types(name, pageNum, pageSize)` |
| 创建设备类型 | `POST` | `/api/zata-manager/device-types` | `create_device_type(...)` |
| 查询设备类型详情 | `GET` | `/api/zata-manager/device-types/{id}` | `get_device_type(deviceTypeId)` |
| 更新设备类型 | `PUT` | `/api/zata-manager/device-types/{id}` | `update_device_type(...)` |
| 删除设备类型 | `DELETE` | `/api/zata-manager/device-types/{id}` | `delete_device_type(deviceTypeId)` |
| 查询设备列表 | `GET` | `/api/zata-manager/devices` | `list_devices(...)` |
| 创建设备 | `POST` | `/api/zata-manager/devices` | `create_device(...)` |
| 按设备编码查询设备 | `GET` | `/api/zata-manager/devices/code/{code}` | `get_device_by_code(deviceCode)` |
| 更新设备 | `PUT` | `/api/zata-manager/devices/{id}` | `update_device(...)` |
| 删除设备 | `DELETE` | `/api/zata-manager/devices/{id}` | `delete_device(deviceId)` |

## Usage / 使用场景

严格采集任务通常需要明确设备类型。场景采集任务可以更轻量，但如果任务计划中指定设备或采集方式，仍应通过 verifier 解析到真实平台配置。

## Examples / 示例

创建设备类型：

- Request: [examples/create_device_type.request.example.json](examples/create_device_type.request.example.json)
- Response: [examples/create_device_type.response.example.json](examples/create_device_type.response.example.json)

创建设备：

- Request: [examples/create_device.request.example.json](examples/create_device.request.example.json)
- Response: [examples/create_device.response.example.json](examples/create_device.response.example.json)

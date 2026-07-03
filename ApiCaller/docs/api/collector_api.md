# Collector API / 采集员 API

本文档列出采集员（Collector）相关 API 能力。相关接口已经出现在 OpenAPI 中，但当前 `ZataAPICaller` 尚未提供结构化封装。

## Scope / 适用范围

采集员 API 应覆盖可领取 Job 查询、Job 领取、采集数据上传或关联、采集进度查看。

在本页明确行为契约和字段要求之前，不应直接实现采集员运行时代码。

## Job Receive Records / Job 领取记录

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询 Job 领取记录 | `GET` | `/api/zata-manager/job-receives` | 未封装 |
| 创建 Job 领取记录 | `POST` | `/api/zata-manager/job-receives` | 未封装 |
| 批量创建 Job 领取记录 | `POST` | `/api/zata-manager/job-receives/batch` | 未封装 |
| 批量删除 Job 领取记录 | `POST` | `/api/zata-manager/job-receives/batch-delete` | 未封装 |
| 查询单个 Job 领取记录 | `GET` | `/api/zata-manager/job-receives/{id}` | 未封装 |
| 更新 Job 领取记录 | `PUT` | `/api/zata-manager/job-receives/{id}` | 未封装 |

## Job Discovery / Job 查询

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询 Task 下的 Job | `GET` | `/api/zata-manager/tasks/{id}/jobs` | `list_jobs(...)` |
| 查询 Job 详情 | `GET` | `/api/zata-manager/jobs/{id}` | `get_job(jobId)` |
| 查询 Task 下的视频 Job | `GET` | `/api/zata-manager/tasks/{id}/video-jobs` | 未封装 |

## Data Upload Or Association / 数据上传或关联

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 批量上传采集数据 | `POST` | `/api/zata-manager/instances/{id}/data/batch` | 未封装 |
| 查询 Task 视频数据 | `GET` | `/api/zata-manager/tasks/{id}/video-data` | 未封装 |
| 创建 Task 视频数据 | `POST` | `/api/zata-manager/tasks/{id}/video-data` | 未封装 |
| 查询 Task 视频数据详情 | `GET` | `/api/zata-manager/tasks/{id}/video-data/{dataId}` | 未封装 |
| 更新 Task 视频数据状态 | `PUT` | `/api/zata-manager/tasks/{id}/video-data/{dataId}` | 未封装 |
| 获取 Task 视频数据媒体 | `GET` | `/api/zata-manager/tasks/{id}/video-data/{dataId}/m3u8` | 未封装 |

## Progress / 进度

Job 和 video job 响应中包含领取数量、审核状态等进度相关字段。等采集员运行时工作流明确后，再补充结构化进度文档。

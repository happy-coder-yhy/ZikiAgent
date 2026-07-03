# Audit And Archive API / 审核归档 API

本文档列出采集数据审核和归档相关 API 能力。大多数接口已经出现在 OpenAPI 中，但当前 `ZataAPICaller` 尚未提供结构化封装。

## Scope / 适用范围

审核归档 API 应覆盖待审核数据查询、真机/视频采集数据审核、归档授权管理、归档数据集管理，以及运行时代码需要的统计读取。

在本页明确行为契约和字段要求之前，不应直接实现审核或归档运行时代码。

## Collection Data Audit / 采集数据审核

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询数据详情 | `GET` | `/api/zata-manager/data/{id}` | 未封装 |
| 审核单条数据 | `PUT` | `/api/zata-manager/data/{id}/audit` | 未封装 |
| 批量审核数据 | `POST` | `/api/zata-manager/data/batch-audit` | 未封装 |

## Robot Reviews / 真机数据 Review

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询 review 列表 | `GET` | `/api/zata-manager/reviews` | 未封装 |
| 创建 review | `POST` | `/api/zata-manager/reviews` | 未封装 |
| 查询单个 review | `POST` | `/api/zata-manager/reviews/get` | 未封装 |
| 更新 review | `PUT` | `/api/zata-manager/reviews/{id}` | 未封装 |
| 批量删除 review | `POST` | `/api/zata-manager/reviews/batch-delete` | 未封装 |
| 导出 review | `POST` | `/api/zata-manager/reviews/export` | 未封装 |

## Video Reviews / 视频数据 Review

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询 video review 列表 | `GET` | `/api/zata-manager/video-reviews` | 未封装 |
| 创建 video review | `POST` | `/api/zata-manager/video-reviews` | 未封装 |
| 查询单个 video review | `POST` | `/api/zata-manager/video-reviews/get` | 未封装 |
| 更新 video review | `PUT` | `/api/zata-manager/video-reviews/{id}` | 未封装 |
| 批量删除 video review | `POST` | `/api/zata-manager/video-reviews/batch-delete` | 未封装 |
| 导出 video review | `POST` | `/api/zata-manager/video-reviews/export` | 未封装 |

## Archive Authorization / 归档授权

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询归档授权 | `GET` | `/api/zata-manager/archive-authorizations` | 未封装 |
| 批量创建归档授权 | `POST` | `/api/zata-manager/archive-authorizations` | 未封装 |
| 查询归档授权详情 | `GET` | `/api/zata-manager/archive-authorizations/{id}` | 未封装 |
| 更新归档授权 | `PUT` | `/api/zata-manager/archive-authorizations/{id}` | 未封装 |
| 删除归档授权 | `DELETE` | `/api/zata-manager/archive-authorizations/{id}` | 未封装 |
| 批量删除归档授权 | `POST` | `/api/zata-manager/archive-authorizations/batch-delete` | 未封装 |

## Archive Datasets / 归档数据集

| 能力 | HTTP 方法 | 接口路径 | 当前封装状态 |
| --- | --- | --- | --- |
| 查询归档数据集 | `GET` | `/api/zata-manager/archive-datasets` | 未封装 |
| 创建归档数据集 | `POST` | `/api/zata-manager/archive-datasets` | 未封装 |
| 查询归档数据集详情 | `GET` | `/api/zata-manager/archive-datasets/{id}` | 未封装 |
| 更新归档数据集 | `PUT` | `/api/zata-manager/archive-datasets/{id}` | 未封装 |
| 删除归档数据集 | `DELETE` | `/api/zata-manager/archive-datasets/{id}` | 未封装 |
| 批量删除归档数据集 | `POST` | `/api/zata-manager/archive-datasets/batch-delete` | 未封装 |
| 导出归档数据集 review | `POST` | `/api/zata-manager/archive-datasets/export-reviews` | 未封装 |

## Task Archive State / Task 归档状态

Task 归档状态属于管理员 Task 生命周期的一部分，当前已经封装：

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 |
| --- | --- | --- | --- |
| 归档 Task | `POST` | `/api/zata-manager/tasks/{id}/archive` | `archive_task(taskId)` |
| 取消归档 Task | `POST` | `/api/zata-manager/tasks/{id}/unarchive` | `unarchive_task(taskId)` |

## Statistics / 统计

OpenAPI 中包含审核、采集员、视频和归档统计接口。只有在运行时工作流需要这些调用时，才应在本页补充结构化说明。

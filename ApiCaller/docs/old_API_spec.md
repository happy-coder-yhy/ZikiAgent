# API Description
本文档将对Zata Platform在使用过程中涉及的典型API进行描述。

## 当前已支持调用的 API

下表所列接口均已在 `ZataAPICaller` 中提供封装。查询接口不自动补充筛选条件，创建接口不自动补充请求体字段。

除单接口封装外，`ZataAPICaller.sync_platform_configuration(page_size=200)` 提供当前登录用户的平台配置聚合读取能力。它会同步项目、任务、标签分类、各分类标签树、扁平标签索引、物品目录树和物品列表，便于创建任务、创建标签、创建 job 前查找真实 ID/code。

### zata-rbac

| API | 用途 | `ZataAPICaller` 方法 |
| --- | --- | --- |
| `POST /api/zata-rbac/login` | 登录并保存 access token | `login(username, password, organization)` |
| `GET /api/zata-rbac/users` | 查询用户候选列表 | `list_users(params)` |
| `GET /api/zata-rbac/users/name` | 按名称查询用户候选 | `list_users_by_name(name)` |

### data-manager

| API | 用途 | `ZataAPICaller` 方法 |
| --- | --- | --- |
| `GET /api/zata-manager/projects` | 查询项目候选列表 | `list_projects(params)` |
| `GET /api/zata-manager/projects/{id}` | 查询项目详情 | `get_project(project_id)` |
| `POST /api/zata-manager/projects` | 创建项目 | `create_project(payload)` |
| `PUT /api/zata-manager/projects/{id}` | 更新项目 | `update_project(project_id, payload)` |
| `DELETE /api/zata-manager/projects/{id}` | 删除项目 | `delete_project(project_id)` |
| `GET /api/zata-manager/label-categories` | 查询标签分类候选 | `list_label_categories(params)` |
| `GET /api/zata-manager/label-categories/{code}` | 查询标签分类详情 | `get_label_category(category_code)` |
| `POST /api/zata-manager/label-categories` | 创建标签分类 | `create_label_category(payload)` |
| `PUT /api/zata-manager/label-categories/{code}` | 更新标签分类 | `update_label_category(category_code, payload)` |
| `DELETE /api/zata-manager/label-categories/{code}` | 删除标签分类 | `delete_label_category(category_code)` |
| `GET /api/zata-manager/labels` | 查询标签 | `list_labels(params)` / `list_labels_by_category(...)` |
| `GET /api/zata-manager/labels/{id}` | 查询标签详情 | `get_label(label_id)` |
| `POST /api/zata-manager/labels` | 创建标签 | `create_label(payload)` |
| `PUT /api/zata-manager/labels/{id}` | 更新标签 | `update_label(label_id, payload)` |
| `DELETE /api/zata-manager/labels/{id}` | 删除标签 | `delete_label(label_id)` |
| `GET /api/zata-manager/labels/tree` | 查询标签树或任务场景树 | `get_label_tree(...)` / `list_scene_labels(...)` |
| `GET /api/zata-manager/device-types` | 查询设备类型候选 | `list_device_types(params)` |
| `POST /api/zata-manager/device-types` | 创建设备类型 | `create_device_type(payload)` |
| `GET /api/zata-manager/device-types/{id}` | 查询设备类型详情 | `get_device_type(device_type_id)` |
| `PUT /api/zata-manager/device-types/{id}` | 更新设备类型 | `update_device_type(device_type_id, payload)` |
| `DELETE /api/zata-manager/device-types/{id}` | 删除设备类型 | `delete_device_type(device_type_id)` |
| `GET /api/zata-manager/devices` | 查询设备 | `list_devices(params)` |
| `POST /api/zata-manager/devices` | 创建设备 | `create_device(payload)` |
| `GET /api/zata-manager/devices/code/{code}` | 按编码查询设备 | `get_device_by_code(device_code)` |
| `PUT /api/zata-manager/devices/{id}` | 更新设备 | `update_device(device_id, payload)` |
| `DELETE /api/zata-manager/devices/{id}` | 删除设备 | `delete_device(device_id)` |
| `GET /api/zata-manager/object-categories` | 查询物品目录树 | `list_object_categories(params)` |
| `POST /api/zata-manager/object-categories` | 创建物品目录 | `create_object_category(payload)` |
| `PUT /api/zata-manager/object-categories/{id}` | 更新物品目录 | `update_object_category(category_id, payload)` |
| `DELETE /api/zata-manager/object-categories/{id}` | 删除物品目录 | `delete_object_category(category_id)` |
| `GET /api/zata-manager/object-items` | 查询具体物品 | `list_object_items(params)` |
| `POST /api/zata-manager/object-items` | 创建具体物品 | `create_object_item(payload)` |
| `PUT /api/zata-manager/object-items/{id}` | 更新具体物品 | `update_object_item(item_id, payload)` |
| `DELETE /api/zata-manager/object-items/{id}` | 删除具体物品 | `delete_object_item(item_id)` |
| `GET /api/zata-manager/tasks` | 查询任务列表 | `list_tasks(params)` |
| `GET /api/zata-manager/tasks/{id}` | 查询任务详情 | `get_task(task_id)` |
| `POST /api/zata-manager/tasks` 或 `/projects/{id}/tasks` | 创建任务 | `create_task(payload, project_id)` |
| `PUT /api/zata-manager/tasks/{id}` | 更新任务 | `update_task(task_id, payload)` |
| `PUT /api/zata-manager/tasks/{id}/keep-jobs` | 更新任务并保留 job | `update_task_keep_jobs(task_id, payload)` |
| `DELETE /api/zata-manager/tasks/{id}` | 删除任务 | `delete_task(task_id)` |
| `POST /api/zata-manager/tasks/{id}/publish` | 发布任务 | `publish_task(task_id)` |
| `POST /api/zata-manager/tasks/{id}/unpublish` | 取消发布任务 | `unpublish_task(task_id)` |
| `POST /api/zata-manager/tasks/{id}/archive` | 归档任务 | `archive_task(task_id)` |
| `POST /api/zata-manager/tasks/{id}/unarchive` | 取消归档任务 | `unarchive_task(task_id)` |
| `GET /api/zata-manager/tasks/{id}/jobs` | 查询任务下 job | `list_jobs(task_id, params)` |
| `POST /api/zata-manager/tasks/{id}/jobs` | 创建任务下 job | `create_jobs(task_id, payload)` |
| `GET /api/zata-manager/jobs/{id}` | 查询 job 详情 | `get_job(job_id)` |
| `PUT /api/zata-manager/jobs/{id}` | 更新 job | `update_job(job_id, payload)` |
| `POST /api/zata-manager/jobs/batch-delete` | 批量删除 job | `delete_jobs(job_ids)` |

### 聚合读取：平台配置快照

`sync_platform_configuration(page_size=200)` 会按以下顺序串行读取：

1. `GET /projects?pageNum=1&pageSize=<page_size>`
2. `GET /tasks?pageNum=1&pageSize=<page_size>`
3. `GET /label-categories`
4. 对每个标签分类调用 `GET /labels/tree?categoryCode=<code>`
5. `GET /object-categories`
6. 展开物品目录树后，对每个目录 ID 调用 `GET /object-items?categoryId=<id>&pageNum=1&pageSize=<page_size>`

返回快照中的 `labels` 为扁平索引，字段为 `categoryCode`、`id`、`code`、`name`、`parentId`。`object_categories` 为展开后的物品目录列表，`object_items` 为逐目录查询汇总后的具体物品列表。

真实平台联调确认：标签分类 `scene`、`space`、`task`、`device` 与 `configs/zata_init/*标签.xlsx` 匹配；物品库包含 `香蕉`、`苹果`、`扫码枪`、`扫码台`。注意：只调用根级 `GET /object-items` 可能返回空，必须先展开物品目录树并按 `categoryId` 查询。

# 用户管理

## Login
* type: POST
* url: <base_url>/api/zata-rbac/login
* Body:
```json
{
    "organization": "agent",
    "password": "<password>",
    "username": "admin"
}
```

* Response (关键在于获取到accessToken)
```json
{
    "code": 0,
    "message": "ok",
    "reason": "",
    "metadata": {
        "accessToken": "<access_token>",
        "idToken": "<id_token>",
        "tokenType": "Bearer",
        "expiresIn": 2592000,
        "refreshToken": "<refresh_token>",
        "scope": ""
    }
}
```

**后续所有接口在发送请求时需要附带 Bearer Token 类型的 Authorization, token为前面获取到的accessToken**


---
# 平台配置
平台配置包括：资产、标签、设备、数据四大部分
## 资产库管理
包含 物品库 与 场景任务库 两部分

### 物品库管理
物品库可以创建无限层级的物品目录，但是在最后一个层级下必须要设置对应的具体物品。  在后续创建数据采集任务时，可以通过指定物品目录的方式选择多个目录下的物品，也可以直接指定到具体物品

#### 获取具体物品列表
* type: GET
* url: <base_url>/api/zata-manager/object-items
* Query（均可选）：`categoryId`、`keyword`、`ids`、`pageNum`、`pageSize`。
* 用途：目录建立后，查询可绑定至任务/job 的具体物品及其 ID。

说明：`GET /object-categories` 返回目录树；真实平台读取物品时应先展开目录树，再按每个目录 `categoryId` 调用 `GET /object-items`。不要把无 `categoryId` 的 `GET /object-items` 当成可靠全量物品查询。`POST` 方法分别用于创建目录和创建具体物品。

#### 获取物品目录树
* type: GET
* url: <base_url>/api/zata-manager/object-categories
* Query（可选）：`name`，按目录名称筛选
* Response
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": [
        {
            "id": 6,
            "name": "食品",
            "path": "/食品",
            "level": 1,
            "children": [
                {
                    "id": 9,
                    "name": "水果",
                    "path": "/食品/水果",
                    "level": 2
                },
                {
                    "id": 10,
                    "name": "蔬菜",
                    "path": "/食品/蔬菜",
                    "level": 2
                }
            ]
        },
        {
            "id": 7,
            "name": "扫码工具",
            "path": "/扫码工具",
            "level": 1
        },
        {
            "id": 8,
            "name": "扫码工具2",
            "path": "/扫码工具2",
            "level": 1
        }
    ]
}
```

#### 查询目录下物品
* type: GET
* url: <base_url>/api/zata-manager/object-items
* Query：`categoryId`、`pageNum`、`pageSize`
* 说明：真实平台联调中，根级查询可能返回空；需要对物品目录树中的每个目录 ID 分别查询。
* Response
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "pageNum": 1,
        "pageSize": 50,
        "results": [
            {
                "id": 21,
                "categoryId": 13,
                "categoryName": "水果",
                "code": "object_item_32133341",
                "name": "苹果"
            }
        ],
        "total": 1
    }
}
```

#### 创建物品目录
* type: POST
* url: <base_url>/api/zata-manager/object-categories
* Body
```json
{
	"name": "扫码工具2"
}
```
* Response (需要记录ID和path以便于拼接路径)
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "id": 8,
        "parentId": null,
        "name": "扫码工具2",
        "path": "/扫码工具2",
        "level": 1,
        "sortOrder": 0,
        "status": 1,
        "createdAt": "2026-05-26 17:20:17",
        "updatedAt": "2026-05-26 17:20:17"
    }
}
```

#### 创建二级物品目录
* type: POST
* url: <base_url>/api/zata-manager/object-categories
* Body   (示例中，食品的ID为6)
```json
{
	"name": "蔬菜",
    "parentId": 6
}
```
* Response (需要记录ID)
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "id": 10,
        "parentId": 6,
        "name": "蔬菜",
        "path": "/食品/蔬菜",
        "level": 2,
        "sortOrder": 0,
        "status": 1,
        "createdAt": "2026-05-26 17:34:50",
        "updatedAt": "2026-05-26 17:34:50"
    }
}
```

#### 添加物品
* type: POST
* url: <base_url>/api/zata-manager/object-items
* Body   (示例中，蔬菜的ID为10)
``` json
{
    "description": "大白菜，白色根茎 + 黄绿色叶子", 
    "name": "大白菜", 
    "categoryId": 10, 
    "thumbnailObjectKey": "", 
    "fileObjectKey": ""
}
```
* Response
``` json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "id": 8,
        "categoryId": 10,
        "categoryName": "蔬菜",
        "code": "object_item_1e19e1b7",
        "name": "大白菜",
        "fileObjectKey": "",
        "thumbnailObjectKey": "",
        "fileUrl": "",
        "thumbnailUrl": "",
        "description": "test for agent",
        "status": 1,
        "createdAt": "2026-05-26 17:39:51",
        "updatedAt": "2026-05-26 17:39:51"
    }
}
```

### 场景任务库管理

#### 创建场景任务库模板
* url: <base_url>/api/zata-manager/templates
* type: POST
* Request
```json
{
    "id":2,
    "title":"收银任务采集",
    "description":"对收银技能的动作采集",
    "remark":"手工生成",
    "mainSceneId":164,
    "sceneId":165,
    "spaceIds":[183],
    "taskType":292,
    "difficulty":1,
    "initialState":"{水果}放置在左侧，{扫码物品}放置在中部",
    "actionSteps":[
        {"id":6,"stepOrder":1,"duration":5,"deviation":1,"actionText":"{水果}放置在左侧，{扫码物品}放置在中部","atomicAbilityId":210},
        {"id":7,"stepOrder":2,"duration":6,"deviation":2,"actionText":"将{水果}移动到{扫码物品}前方","atomicAbilityId":280},
        {"id":8,"stepOrder":3,"duration":5,"deviation":1,"actionText":"右手接过{水果}","atomicAbilityId":281},
        {"id":9,"stepOrder":4,"duration":5,"deviation":1,"actionText":"右手将{水果}移动到右侧合适位置","atomicAbilityId":280},
        {"id":10,"stepOrder":5,"duration":3,"deviation":2,"actionText":"放下{水果}移动到右侧合适位置","atomicAbilityId":216}
    ],
        
    "objectBindings":[
        {"id":3,"objectCategoryId":13,"objectItemIds":[21,20]},
        {"id":4,"objectCategoryId":15,"objectItemIds":[24]}
    ]
}
```
* Response:
```json

```

## 标签管理
平台中的标签配置往往为提前初始化设置，只需要检索，不需要手动修改添加

### 获取标签树
* type: GET
* url: <base_url>/api/zata-manager/labels/tree
* Query:
  * `categoryCode` (`string`, 必填): 标签分类编码。
  * `parentId` (`integer`, 可选): 父级标签 ID。
  * `name` (`string`, 可选): 标签名称筛选值。

任务创建中选择场景时，调用 `GET /labels/tree?categoryCode=scene`。返回节点中的 `id` 可作为创建任务请求里的场景标签 ID；如需限制到子树，再明确传入 `parentId`。

### 创建标签分类
* type: POST
* url: <base_url>/api/zata-manager/label-categories
* Body: `name` 为 OpenAPI 要求的必填字段；`code`、`description`、`parentCode`、`isTree`、`isMultiple`、`sortOrder`、`status` 按业务需要显式提供。

### 创建标签
* type: POST
* url: <base_url>/api/zata-manager/labels
* Body: `categoryCode` 和 `name` 为必填字段；树形标签的父节点使用 `parentId` 显式指定。


# 采集工作管理
开展一次采集工作，必须要完成 采集项目-->采集任务-->采集作业 的完整三级定义：
* 采集项目：整个采集工作的项目需求来源，只通过projectID、name和description进行定义
* 采集任务：对机器人具体任务技能的数据采集需求，一个采集项目下可以有多个采集任务，如货物搬运、物品扫码等。
* 采集作业：最小采集单元，一个采集任务下可以有多个采集作业，每个采集作业会对采集任务的采集需求进行更明确的定义，如搬运货物A、搬运货物B、物品A扫码、物品B扫码等。

## 采集项目管理

### 查询Projects
* type: GET
* url: <base_url>/api/zata-manager/projects
* Response (获取所有的results/name， total)
``` json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "pageNum": 0,
        "pageSize": 0,
        "results": [
            {
                "id": 4,
                "name": "Test2",
                "description": "Test",
                "sceneIds": null,
                "sceneItems": [],
                "status": 1,
                "createdAt": "2026-05-26 17:23:15",
                "updatedAt": "2026-05-26 17:23:15"
            },
            {
                "id": 3,
                "name": "TestForAgent",
                "description": "为测试Agent自动生成任务模板设定的项目集合",
                "sceneIds": null,
                "sceneItems": [],
                "status": 1,
                "createdAt": "2026-05-26 16:49:01",
                "updatedAt": "2026-05-26 16:49:01"
            }
        ],
        "total": 2
    }
}
```

### 创建Project
* type: POST
* url: <base_url>/api/zata-manager/projects
* Body:
```json
{
    "id": null, 
    "name": "ProjectName", 
    "description": "Description of ProjectName"
}
```

* Response


## 采集任务管理
采集任务往往指代某个项目下，对机器人的具体技能数据采集需求，如居家场景的桌面整理、工厂里的货物搬运等。
其需要明确指定任务场景、采集用途。

目前的采集任务可以分为两类：
* 真机采集任务（严格任务）：其对采集过程中涉及的设备类型、初始状态、具体采集步骤等等均有严格定义，并且在创建真机采集任务后，会自动生成对应的采集作业，其有两种创建方式：
    * 模板创建：利用场景任务库中的模板直接创建真机采集任务，只需要额外提供少量配置信息
    * 直接创建：需要完成所有严格任务定义才能创建对应采集任务

* 视频采集任务（场景任务）：其只对任务场景等少量配置进行约束，不需要对任务的严格定义，可以快速开展采集工作。 但是创建后的采集任务还需要额外创建对应的采集作业

### 模板创建真机采集任务
* url: <base_url>/api/zata-manager/projects/<projectID>/tasks/from-template
* type: POST
* Request:
```json
{
    "projectId": 2,
    "taskPurposeId": 188,
    "collectModeId": 195,
    "videoQuality": 1,
    "collectSchemeId": 191,
    "deviceTypeId": 3,
    "abnormalRatio": 20,
    "countdownSeconds": 10,
    "collectors": [],
    "auditors": [],
    "duration": 24,
    "minDuration": 3,
    "planCollectCount": 60,
    "templateItems": [
        {
            "templateId": 2,
            "autoCreateInstance": true,
            "jobCount": 2,
            "jobPlanCollectCount": 30
        }
    ]
}
```
* Response:
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": [
        {
            "id": 9,
            "projectId": 2,
            "projectName": "gui_edit prj",
            "templateId": null,
            "templateTitle": "",
            "title": "收银任务采集",
            "description": "对收银技能的动作采集",
            "remark": "手工生成",
            "sceneId": 165,
            "sceneName": "收银",
            "mainSceneId": 164,
            "mainSceneName": "商超",
            "spaceIds": [
                183
            ],
            "spaceItems": [
                {
                    "id": 183,
                    "name": "收银区"
                }
            ],
            "taskPurposeId": 188,
            "taskPurposeName": "运营试采",
            "collectSchemeId": 191,
            "collectSchemeName": "VR",
            "collectModeId": 195,
            "collectModeName": "双臂",
            "deviceTypeId": 3,
            "deviceTypeName": "O1-eHand-fish_RGBD",
            "collectMethod": "robot",
            "taskType": 292,
            "taskTypeName": "短程",
            "difficulty": 1,
            "abnormalRatio": 20,
            "countdownSeconds": 10,
            "planCollectCount": 60,
            "normalPlanCount": 48,
            "abnormalPlanCount": 12,
            "minDuration": 3,
            "duration": 24,
            "videoQuality": 1,
            "recognitionEnabled": false,
            "customLabelIds": null,
            "customLabelItems": [],
            "auditLabelIds": [],
            "auditLabelItems": [],
            "normalCollectCount": 0,
            "abnormalCollectCount": 0,
            "normalAuditCount": 0,
            "abnormalAuditCount": 0,
            "jobCount": 2,
            "initialState": "{水果}放置在左侧，{扫码物品}放置在中部",
            "status": 1,
            "createdBy": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
            "createdByDisplayName": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
            "createdAt": "2026-06-10 09:25:09",
            "updatedAt": "2026-06-10 09:25:09",
            "auditors": [],
            "collectors": [],
            "actionSteps": [
                {
                    "id": 16,
                    "stepOrder": 1,
                    "duration": 5,
                    "deviation": 1,
                    "actionText": "{水果}放置在左侧，{扫码物品}放置在中部",
                    "atomicAbilityId": 210,
                    "atomicAbilityName": "Grasp（抓取）"
                },
                {
                    "id": 17,
                    "stepOrder": 2,
                    "duration": 6,
                    "deviation": 2,
                    "actionText": "将{水果}移动到{扫码物品}前方",
                    "atomicAbilityId": 280,
                    "atomicAbilityName": "Move（移动）"
                },
                {
                    "id": 18,
                    "stepOrder": 3,
                    "duration": 5,
                    "deviation": 1,
                    "actionText": "右手接过{水果}",
                    "atomicAbilityId": 281,
                    "atomicAbilityName": "HandOver（传递）"
                },
                {
                    "id": 19,
                    "stepOrder": 4,
                    "duration": 5,
                    "deviation": 1,
                    "actionText": "右手将{水果}移动到右侧合适位置",
                    "atomicAbilityId": 280,
                    "atomicAbilityName": "Move（移动）"
                },
                {
                    "id": 20,
                    "stepOrder": 5,
                    "duration": 3,
                    "deviation": 2,
                    "actionText": "右手将{水果}放下",
                    "atomicAbilityId": 216,
                    "atomicAbilityName": "Lower（放下）"
                }
            ],
            "objectBindings": [
                {
                    "id": 6,
                    "placeholder": "",
                    "objectCategoryId": 13,
                    "objectCategoryName": "水果",
                    "objectItemIds": [
                        21,
                        20
                    ],
                    "objectItems": [
                        {
                            "id": 21,
                            "name": "苹果"
                        },
                        {
                            "id": 20,
                            "name": "香蕉"
                        }
                    ]
                },
                {
                    "id": 7,
                    "placeholder": "",
                    "objectCategoryId": 15,
                    "objectCategoryName": "扫码物品",
                    "objectItemIds": [
                        24
                    ],
                    "objectItems": [
                        {
                            "id": 24,
                            "name": "扫码台"
                        }
                    ]
                }
            ]
        }
    ]
}
```

### 直接创建真机采集任务
* url: <base_url>/api/zata-manager/tasks
* type: POST
* Request:
```json
{
    "projectId": 3,
    "mainSceneId": 168,
    "sceneId": 170,
    "title": "仓库物品上架",
    "taskPurposeId": 187,
    "collectSchemeId": 191,
    "deviceTypeId": 2,
    "taskType": 292,
    "collectModeId": 195,
    "difficulty": 2,
    "initialState": "{食品}在左侧，货架在右侧",
    "countdownSeconds": 8,
    "abnormalRatio": 10,
    "duration": 20,
    "actionSteps": [
        {
            "duration": 5,
            "deviation": 2,
            "actionText": "拿起{食品}",
            "atomicAbilityId": 210
        },
        {
            "duration": 5,
            "deviation": 2,
            "actionText": "将{食品}移动到货架前方",
            "atomicAbilityId": 280
        },
        {
            "duration": 3,
            "deviation": 1,
            "actionText": "右手接过{食品}",
            "atomicAbilityId": 281
        },
        {
            "duration": 4,
            "deviation": 2,
            "actionText": "将{食品}移动到货架合适位置",
            "atomicAbilityId": 280
        },
        {
            "duration": 3,
            "deviation": 1,
            "actionText": "放下{食品}",
            "atomicAbilityId": 216
        }
    ],
    "customLabelIds": [],
    "description": "将板车上的物品搬运到货架",
    "remark": "<p>手工创建</p>",
    "spaceIds": [
        181
    ],
    "collectors": [],
    "auditors": [],
    "minDuration": 12,
    "videoQuality": 3,
    "objectBindings": [
        {
            "objectCategoryName": "食品",
            "objectCategoryId": 12
        }
    ],
    "collectMethod": "robot"
}
```


* Response:
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "id": 7,
        "projectId": 3,
        "projectName": "XX工厂项目",
        "templateId": null,
        "templateTitle": "",
        "title": "仓库物品上架",
        "description": "将板车上的物品搬运到货架",
        "remark": "<p>手工创建</p>",
        "sceneId": 170,
        "sceneName": "搬运",
        "mainSceneId": 168,
        "mainSceneName": "工厂",
        "spaceIds": [
            181
        ],
        "spaceItems": [
            {
                "id": 181,
                "name": "库房"
            }
        ],
        "taskPurposeId": 187,
        "taskPurposeName": "开发测试",
        "collectSchemeId": 191,
        "collectSchemeName": "VR",
        "collectModeId": 195,
        "collectModeName": "双臂",
        "deviceTypeId": 2,
        "deviceTypeName": "A2D-oymotion-D435",
        "collectMethod": "robot",
        "taskType": 292,
        "taskTypeName": "短程",
        "difficulty": 2,
        "abnormalRatio": 10,
        "countdownSeconds": 8,
        "planCollectCount": 0,
        "normalPlanCount": 0,
        "abnormalPlanCount": 0,
        "minDuration": 12,
        "duration": 20,
        "videoQuality": 3,
        "recognitionEnabled": false,
        "customLabelIds": null,
        "customLabelItems": [],
        "auditLabelIds": [],
        "auditLabelItems": [],
        "normalCollectCount": 0,
        "abnormalCollectCount": 0,
        "normalAuditCount": 0,
        "abnormalAuditCount": 0,
        "jobCount": 0,
        "initialState": "{食品}在左侧，货架在右侧",
        "status": 1,
        "createdBy": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
        "createdByDisplayName": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
        "createdAt": "2026-06-10 09:03:50",
        "updatedAt": "2026-06-10 09:03:50",
        "auditors": [],
        "collectors": [],
        "actionSteps": [
            {
                "id": 11,
                "stepOrder": 0,
                "duration": 5,
                "deviation": 2,
                "actionText": "拿起{食品}",
                "atomicAbilityId": 210,
                "atomicAbilityName": "Grasp（抓取）"
            },
            {
                "id": 12,
                "stepOrder": 0,
                "duration": 5,
                "deviation": 2,
                "actionText": "将{食品}移动到货架前方",
                "atomicAbilityId": 280,
                "atomicAbilityName": "Move（移动）"
            },
            {
                "id": 13,
                "stepOrder": 0,
                "duration": 3,
                "deviation": 1,
                "actionText": "右手接过{食品}",
                "atomicAbilityId": 281,
                "atomicAbilityName": "HandOver（传递）"
            },
            {
                "id": 14,
                "stepOrder": 0,
                "duration": 4,
                "deviation": 2,
                "actionText": "将{食品}移动到货架合适位置",
                "atomicAbilityId": 280,
                "atomicAbilityName": "Move（移动）"
            },
            {
                "id": 15,
                "stepOrder": 0,
                "duration": 3,
                "deviation": 1,
                "actionText": "放下{食品}",
                "atomicAbilityId": 216,
                "atomicAbilityName": "Lower（放下）"
            }
        ],
        "objectBindings": [
            {
                "id": 5,
                "placeholder": "",
                "objectCategoryId": 12,
                "objectCategoryName": "食品",
                "objectItemIds": [],
                "objectItems": []
            }
        ]
    }
}
```


### 创建视频采集任务
* url: <base_url>/api/zata-manager/tasks
* type: POST
* Request:
```json
{
    "projectId":2,
    "mainSceneId":159,
    "sceneId":161,
    "title":"桌面整理技能采集",
    "taskPurposeId":187,
    "difficulty":2,
    "deviceTypeId":null,
    "customLabelIds":[],
    "spaceIds":[172],
    "description":"将桌面物品进行分类整理",
    "remark":"<p>人工设计任务</p>",
    "collectMethod":"web_video",
    "recognitionEnabled":true
}
```
* Response:
```json
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": {
        "id": 8,
        "projectId": 3,
        "projectName": "XX工厂项目",
        "templateId": null,
        "templateTitle": "",
        "title": "货架整理",
        "description": "整理货架物品",
        "remark": "<p>手动设置</p>",
        "sceneId": 171,
        "sceneName": "整理",
        "mainSceneId": 168,
        "mainSceneName": "工厂",
        "spaceIds": null,
        "spaceItems": [],
        "taskPurposeId": 187,
        "taskPurposeName": "开发测试",
        "collectSchemeId": null,
        "collectSchemeName": "",
        "collectModeId": null,
        "collectModeName": "",
        "deviceTypeId": null,
        "deviceTypeName": "",
        "collectMethod": "web_video",
        "taskType": 1,
        "taskTypeName": "",
        "difficulty": 1,
        "abnormalRatio": 0,
        "countdownSeconds": 5,
        "planCollectCount": 0,
        "normalPlanCount": 0,
        "abnormalPlanCount": 0,
        "minDuration": 0,
        "duration": 0,
        "videoQuality": 1,
        "recognitionEnabled": true,
        "customLabelIds": null,
        "customLabelItems": [],
        "auditLabelIds": [],
        "auditLabelItems": [],
        "normalCollectCount": 0,
        "abnormalCollectCount": 0,
        "normalAuditCount": 0,
        "abnormalAuditCount": 0,
        "jobCount": 0,
        "initialState": "",
        "status": 1,
        "createdBy": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
        "createdByDisplayName": "1d083769-afe4-4e2c-8b05-7db7b65c40f6",
        "createdAt": "2026-06-10 09:09:30",
        "updatedAt": "2026-06-10 09:09:30",
        "auditors": [],
        "collectors": [],
        "actionSteps": null,
        "objectBindings": null
    }
}
```

## 采集作业管理
目前只有视频采集任务（场景任务）需要额外创建采集作业，真机采集任务（严格任务）会在创建采集任务时同时完成采集作业的定义

### 创建视频采集作业
* url
* type
* Request
```json
{
    "jobs": [
        {
            "requiredRepeat": 20,
            "description": "job desc"
        }
    ],
    "taskId": 17
}

REs
{
    "code": 0,
    "reason": "",
    "message": "success",
    "metadata": [
        {
            "id": 21,
            "taskId": 17,
            "taskTitle": "xiaming-aaaaaa",
            "requiredRepeat": 20,
            "requiredMember": 0,
            "name": "",
            "type": 1,
            "description": "job desc",
            "receiveCount": 0,
            "collectStatus": 0,
            "reviewStatus": 0,
            "createdAt": "2026-05-28 13:14:37",
            "updatedAt": "2026-05-28 13:14:37"
        }
    ]
}
```
* Response
```json

```




---
动态选项池与任务字段来源

| 任务请求字段 | 查询来源 | 调用方法 | 说明 |
| --- | --- | --- | --- |
| `projectId` | `GET /projects` | `list_projects(params)` | 从项目列表结果选择 ID。 |
| `sceneId` | `GET /labels/tree?categoryCode=scene` | `list_scene_labels(parent_id, name)` | `scene` 是已测试的场景分类调用方式。 |
| `taskPurposeId`、`collectModeId`、`collectSchemeId`、`sensorTypeId`、`customLabelIds`、`atomicAbilityId` | `GET /label-categories` 后调用 `GET /labels` 或 `GET /labels/tree` | `list_label_categories(params)`、`list_labels_by_category(...)`、`get_label_tree(...)` | OpenAPI 仅表明这些字段是标签 ID；分类编码应从平台数据取得，不在代码中预置。 |
| `deviceTypeId` | `GET /device-types` | `list_device_types(params)` | 该候选来源依据 OpenAPI 的设备类型资源封装，实际任务字段映射需结合平台返回数据核验。 |
| `collectors[*].userId`、`auditors[*].userId` | `GET /users` 或 `GET /users/name` | `list_users(params)`、`list_users_by_name(name)` | RBAC 用户查询结果用于任务人员字段。 |
| `objectBindings` / job 物品项 | `GET /object-categories` 与按 `categoryId` 查询 `GET /object-items` | `sync_platform_configuration()` 或 `list_object_categories(params)`、`list_object_items(params)` | 先展开目录树，再按目录 ID 取得具体物品 ID。 |

说明：本层封装只提供实时查询入口，不建立本地固定 ID 或分类编码默认值。需要一次性准备项目、标签、物品引用时，优先使用 `sync_platform_configuration()`。

---
代码封装对应关系

| 业务能力 | HTTP 接口 | `ZataAPICaller` 方法 |
| --- | --- | --- |
| 同步平台配置快照 | 多个只读接口聚合 | `sync_platform_configuration(page_size)` |
| 创建项目 | `POST /projects` | `create_project(payload)` |
| 查询标签分类 | `GET /label-categories` | `list_label_categories(params)` |
| 创建标签分类 | `POST /label-categories` | `create_label_category(payload)` |
| 查询标签 | `GET /labels` | `list_labels(params)` |
| 按分类查询标签候选 | `GET /labels?categoryCode={code}` | `list_labels_by_category(category_code, parent_id, name, page_num, page_size)` |
| 创建标签 | `POST /labels` | `create_label(payload)` |
| 查询标签树 | `GET /labels/tree` | `get_label_tree(category_code, parent_id, name)` |
| 查询任务场景标签 | `GET /labels/tree?categoryCode=scene` | `list_scene_labels(parent_id, name)` |
| 查询设备类型候选 | `GET /device-types` | `list_device_types(params)` |
| 按名称查询用户候选 | `GET /users/name` | `list_users_by_name(name)` |
| 查询物品目录树 | `GET /object-categories` | `list_object_categories(params)` |
| 创建物品目录 | `POST /object-categories` | `create_object_category(payload)` |
| 查询具体物品 | `GET /object-items?categoryId={id}` | `list_object_items(params)` |
| 创建具体物品 | `POST /object-items` | `create_object_item(payload)` |

以上创建类封装仅发送调用方明确提供的请求体字段，不自动补充可选字段、层级 ID、状态值或分页参数。

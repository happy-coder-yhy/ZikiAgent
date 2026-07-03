# 2026-06-10 API Alignment Real Server Integration

Test server:

- `base_url`: `http://pre.zikirobo.com:30080/`
- `organization`: `agent`
- Login user: `admin`

Rules followed:

- Requests were executed serially.
- Consecutive requests waited 2.2 seconds.
- Created resource names/titles/codes used `_zac_test_` prefixes.
- Created resources were deleted after verification.

## RBAC / User Management

| Step | Result |
| --- | --- |
| `login(...)` | 200, access token returned |
| `userinfo()` | 200 |
| `list_users(pageNum=1, pageSize=5)` | 200 |
| `list_users_by_name("admin")` | 200 |

## Platform Configuration Reads

| Step | Result |
| --- | --- |
| `list_projects(pageNum=1, pageSize=5)` | 200, 2 items |
| `list_tasks(pageNum=1, pageSize=5)` | 200, 5 items |
| `list_label_categories()` | 200, 4 categories: `scene`, `space`, `task`, `device` |
| `get_label_tree("scene")` | 200, 3 root items |
| `list_object_categories()` | 200, 2 root items |
| `list_object_items(categoryId=12, pageNum=1, pageSize=5)` | 200, 0 items |
| `list_device_types(pageNum=1, pageSize=5)` | 200, 2 items |
| `list_devices(pageNum=1, pageSize=5)` | 200, 0 items |
| `get_project(projectId)` | 200 |
| `get_label_category("scene")` | 200 |
| `list_labels(categoryCode="scene", pageNum=1, pageSize=5)` | 200, 5 items |
| `list_labels_by_category(categoryCode="scene", pageNum=1, pageSize=5)` | 200, 5 items |
| `get_label(labelId=159)` | 200 |

`sync_platform_configuration(pageSize=20, request_interval_seconds=2.2)` returned:

- `projects`: 2
- `tasks`: 6
- `label_categories`: 4
- `labels`: 155
- `object_categories`: 4
- `object_items`: 4
- `device_types`: 2
- `devices`: 0
- `raw` keys: `device_types`, `devices`, `label_categories`, `label_trees`, `object_categories`, `object_items`, `projects`, `tasks`

## Collection Work Writes

| Step | Result | Cleanup |
| --- | --- | --- |
| `create_project(...)` / `update_project(...)` / `delete_project(...)` | 200 / 200 / 200 | `list_projects(...)` after delete returned 0 |
| `create_scene_task(...)` | 200, created task id `10` | `delete_task(10)` and `delete_project(5)` returned 200 |
| `create_strict_task(...)` | 200, created task id `11` | `delete_task(11)` and `delete_project(6)` returned 200 |
| `create_jobs(...)` | 200, created job id `13` | `delete_jobs([13])`, `delete_task(12)`, and `delete_project(7)` returned 200 |
| `create_strict_task_from_template(...)` | 200, created task id `13` from template id `2` | `delete_task(13)` and `delete_project(8)` returned 200 |

Additional lifecycle check on temporary task id `14`:

| Step | Result |
| --- | --- |
| `update_task(...)` | 200 |
| `create_jobs(...)` | 200, created job id `15` |
| `get_job(15)` | 200 |
| `update_job(15, ...)` | 200 |
| `update_task_keep_jobs(...)` | 200 |
| `publish_task(14)` | 200 |
| `unpublish_task(14)` | 200 |
| `archive_task(14)` | 200 |
| `unarchive_task(14)` | 200 |
| Initial cleanup | `delete_jobs([15])`, `delete_task(14)`, and `delete_project(9)` returned 200 |

Follow-up cleanup verification found project id `9` still visible because task id `14` remained under the project. Retried cleanup in dependency order:

1. `list_jobs(taskId=14)` returned 200 with no jobs.
2. `unpublish_task(14)` returned 200.
3. `unarchive_task(14)` returned 200.
4. `delete_task(14)` returned 200.
5. `list_tasks(projectId=9)` returned 200 with 0 tasks.
6. `delete_project(9)` returned 200.
7. `list_projects(name="_zac_test_")` returned 200 with 0 projects.

## Platform Configuration Writes

| Step | Result | Cleanup |
| --- | --- | --- |
| `create_label_category(...)` | 200 | `delete_label_category(...)` returned 200 |
| `create_label(...)` | 200, response did not expose a direct label id in `metadata.id` | Parent label category cleanup verified by `list_label_categories(...)` returning 0 |
| `create_object_category(...)` / `update_object_category(...)` | 200 / 200 | `delete_object_category(...)` returned 200 |
| `create_object_item(...)` / `update_object_item(...)` | 200 / 200 | `delete_object_item(...)` returned 200 |
| `create_device_type(...)` / `get_device_type(...)` / `delete_device_type(...)` | 200 / 200 / 200 | Deleted after dependent device cleanup |
| `create_device(...)` / `get_device_by_code(...)` / `update_device(...)` / `delete_device(...)` | 200 / 200 / 200 / 200 | Deleted before device type cleanup |

## Notes

- Template read wrappers were added because template-based strict Task creation needs an existing `templateId`.
- `create_label(...)` succeeded but did not return a directly usable label id in the tested response shape. The temporary label category was deleted and confirmed absent afterward.
- Task/Project cleanup after lifecycle operations may require an explicit dependency-order retry if the first delete returns 200 while the task remains visible.

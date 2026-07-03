# Testing / 测试说明

本文档说明本项目稳定的本地检查和真实平台联调规则。单次联调结果不放在 `docs/`，应归档到 `results/`。

## Lightweight Local Checks / 轻量本地检查

```bash
python -m py_compile modules/*.py utils/*.py
python -m unittest tests.test_api_caller
```

修改运行时代码或 API wrapper 后，应至少运行这些检查。

## Real Test Platform / 真实测试平台

本项目允许直接与测试平台进行联调：

| 配置项 | 值 |
| --- | --- |
| Base URL | `http://pre.zikirobo.com:30080/` |
| Organization | `agent` |
| Username | `admin` |
| Password | `1qaz@WSX1` |

不要把账号、密码或 token 硬编码到源码文件中。优先使用本地配置或环境相关输入。

## Request Discipline / 请求纪律

与真实测试平台交互时：

- 只串行执行 API 请求。
- 连续两次 API 请求之间保持可见的 2 秒以上间隔。
- 避免批量或并行写入测试。
- 手动验证资源应使用清晰的测试前缀。
- 写操作应视为受控联调，而不是随手 smoke check。

## Recommended Real-Server Flow / 推荐联调流程

只读验证建议流程：

1. Login.
2. Query current user.
3. Query projects.
4. Query label categories.
5. Query label trees.
6. Query object categories.
7. Query object items per object category.

写入工作流验证建议流程：

1. Create a test-prefixed project.
2. Create a task under the project.
3. Create jobs under the task.
4. Exercise task lifecycle operations.
5. Clean up only through explicit deletion calls and required confirmation.

## Stable Platform Observations / 稳定平台观察

- `sync_platform_configuration()` 必须先展开 `object-categories`，再按每个 `categoryId` 查询 `object-items`。
- 根级 `GET /object-items` 查询可能返回空，不能视为全量物品库查询。
- 如果 Task 详情显示 `status=2`，说明平台仍认为 Task 已发布，删除可能失败；删除前应取消发布并重新检查状态。

## One-Off Results / 单次结果归档

带日期的单次验证输出应放在 `results/`，不放在 `docs/`。

真实平台运行记录放在 [../../results/real_server_integration/](../../results/real_server_integration/)。这些记录可以包含请求序列、观测计数、临时资源 ID 和单次运行中发现的平台行为。

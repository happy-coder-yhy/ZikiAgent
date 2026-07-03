# Collection Work API / 采集工作管理 API

一次完整的数据采集工作由 `Collection Project`、`Collection Task`、`Collection Job` 三层组成。

- `Collection Project` / 采集项目：表示数据采集需求来源。
- `Collection Task` / 采集任务：Project 下的任务场景或机器人技能采集需求。
- `Collection Job` / 采集作业：Task 下可被采集员领取和完成的原子作业。

采集任务按 `taskCategory` 分为三类：严格采集任务（Strict Collection Task）、指令采集任务（Instruction Collection Task）和场景采集任务（Scene Collection Task）。`collectMethod=robot` 表示真机采集，只允许 `taskCategory=strict`；`collectMethod=web_video` 表示互联网视频或其他 ego 设备采集，可创建 `strict`、`instruction` 或 `scene` 三类任务。

## 文档入口

- [project_api.md](project_api.md): 采集项目查询、创建、编辑与删除。
- [strict_task_api.md](strict_task_api.md): 严格采集任务查询、模板创建、直接创建、编辑、删除和生命周期。
- [instruction_task_api.md](instruction_task_api.md): 指令采集任务查询、创建、编辑、删除和生命周期。
- [scene_task_api.md](scene_task_api.md): 场景采集任务查询、创建、编辑、删除和生命周期。
- [job_api.md](job_api.md): 采集作业查询、创建、编辑与删除。

## Recommended Write Order / 推荐写入顺序

1. 登录。
2. 同步平台配置快照。
3. 使用 verifier 校验 Project 名称、Task 配置匹配和 Job 结构。
4. 创建 Collection Project。
5. 创建 Strict、Instruction 或 Scene Collection Task。
6. 必要时创建 Collection Job。
7. 发布 Collection Task。

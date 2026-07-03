# Zata API Caller Toolkit

本项目用于封装 `APICaller` 与 `ZataAPICaller`，提供对 Zata Platform 的结构化 API 调用能力。项目会作为基础 Tool 包被其他 LLM-Agent 项目以 submodule 形式引用；上层 Agent 可基于 LangGraph、PI 或其他框架自由组合 workflow。

本项目不实现 Agent 推理、任务自动生成、平台配置自动生成或补全、CLI/GUI 产品界面或工作流编排。当前重点是固化 `ZataAPICaller` 的公开调用边界。

## 核心原则

- `APICaller` 是低层 HTTP/JSON 传输层，负责 URL 构造、请求头合并、JSON 序列化和响应解析。
- `ZataAPICaller` 是 Zata Platform 业务调用层，公开方法应提供结构化调用参数，避免外部调用者自行组装最终 JSON。
- 公开平台操作边界使用 OpenAPI 字段名，例如 `sceneId`、`categoryCode`、`projectId`。
- OpenAPI 中的复杂组件、嵌套对象或数组 item 可使用与 OpenAPI schema 对齐的 request object。
- 内部实现、私有 helper、模块名、测试名继续使用 Python 常规 `snake_case`。
- `ZataAPICaller` 可保留私有 raw request helper，用于调试或平台 API 变化时快速适配，但不作为公开 Tool 接口。
- 新增运行时代码前，应先确认对应标准文档位置：API 能力写入 `docs/api/`，校验逻辑写入 `docs/verifier.md`，领域术语写入 `CONTEXT.md`，重大边界决策写入 `docs/adr/`。

## 当前能力
- 用户管理功能
    - Casdoor 登录：`POST /api/zata-rbac/login`，自动缓存 `Authorization: Bearer <token>`。
    - 当前用户信息：`GET /api/zata-rbac/userinfo`。
    - RBAC 用户查询：`GET /api/zata-rbac/users`、`GET /api/zata-rbac/users/name`。
- 平台功能
    - 当前登录用户平台配置快照同步：
        - 项目列表
        - 任务列表
        - 标签库
        - 物品库
        - 设备类型和设备列表
    - 项目、标签分类、标签、标签树、设备类型、设备、物品目录、物品、任务、job 的基础 API 封装。
    - 采集任务创建已按 `taskCategory` 区分为严格任务、指令任务和场景任务；`collectMethod=robot` 只用于严格任务，`collectMethod=web_video` 可用于三类任务。
    - 任务发布、取消发布、归档、取消归档、删除等管理操作封装。
    
## 调用示例

```python
from modules.api_caller import APICallerConfig, ZataAPICaller

caller = ZataAPICaller(APICallerConfig(base_url="http://pre.zikirobo.com:30080/"))
caller.login(username="admin", password="***", organization="agent")

snapshot = caller.sync_platform_configuration(pageSize=200)
```

返回值包含：

- `projects`: 项目列表。
- `tasks`: 任务列表。
- `label_categories`: 标签分类列表。
- `label_trees`: 按分类 code 分组的标签树。
- `labels`: 扁平标签索引，包含 `categoryCode`、`id`、`code`、`name`、`parentId`。
- `object_category_tree`: 原始物品目录树。
- `object_categories`: 展开后的物品目录列表，包含根目录和子目录。
- `object_items`: 按物品目录逐目录查询得到的物品列表。
- `device_types`: 设备类型列表。
- `devices`: 设备列表。
- `raw`: 上述查询接口的原始响应体。

真实平台只读联调结论：

- `scene`、`space`、`task`、`device` 四类标签已与 `configs/zata_init/*标签.xlsx` 中的标签编码/名称逐项匹配。
- 物品库已读取到 `香蕉`、`苹果`、`扫码枪`、`扫码台`。
- 物品读取必须先展开 `object-categories` 目录树，再按每个 `categoryId` 查询 `object-items`；根级 `object-items` 查询可能为空。

## 真实测试 Server

可以直接与测试用平台进行只读或受控写入联调：

- `base_url`: `http://pre.zikirobo.com:30080/`
- `organization`: `agent`
- `username`: `admin`
- `password`: `1qaz@WSX1`

连续请求必须串行执行，并且两条 API 请求之间显示等待大于 2 秒。

## 文档

- [CONTEXT.md](CONTEXT.md): Zata Platform 领域术语。
- [docs/api/index.md](docs/api/index.md): 按角色和能力检索 API 文档。
- [docs/api/platform_configuration/index.md](docs/api/platform_configuration/index.md): 平台配置 API 总览。
- [docs/api/collection_work/index.md](docs/api/collection_work/index.md): 采集工作管理 API 总览。
- [docs/verifier.md](docs/verifier.md): 创建前校验器行为契约。
- [docs/development/testing.md](docs/development/testing.md): 测试平台和联调规则。
- [results/real_server_integration/](results/real_server_integration/): 单次真实平台联调和验证结果。
- [docs/adr/0002-structured-public-api-with-private-raw-platform-request.md](docs/adr/0002-structured-public-api-with-private-raw-platform-request.md): 公开结构化 API 与私有 raw request 的边界。
- [docs/adr/0003-openapi-aligned-public-boundary-names.md](docs/adr/0003-openapi-aligned-public-boundary-names.md): 公开边界使用 OpenAPI 字段名的决策。

## 开发检查

```bash
python -m py_compile modules/*.py utils/*.py
python -m unittest tests.test_api_caller
```

## 后续重构重点

- 将 `ZataAPICaller` 公开业务方法从裸 `payload` 参数重构为 OpenAPI 对齐的结构化参数。
- 为 OpenAPI 中的复杂组件、嵌套对象或数组 item 增加轻量 request object。
- 增加私有 `_request_rbac` / `_request_data_manager` raw request helper，作为 API 变化时的内部 escape hatch。
- 为平台配置快照补自动翻页策略。

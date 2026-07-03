# User Management API / 用户管理 API

用户管理 API 覆盖登录、当前用户信息和人员候选查询。它是采集工作制订流程的基础能力，但不属于平台配置自动生成逻辑。

## Scope / 范围

本项目只封装平台已有用户接口：

- 登录并缓存访问令牌。
- 查询当前登录用户信息。
- 查询用户候选列表。
- 按用户名查询用户候选。

本项目不负责创建、补全或自动配置平台用户。

## API Capabilities / API 能力

| 能力 | HTTP 方法 | 接口路径 | `ZataAPICaller` 方法 | 当前状态 |
| --- | --- | --- | --- | --- |
| 登录 | `POST` | `/api/zata-rbac/login` | `login(username, password, organization)` | 已封装 |
| 当前用户信息 | `GET` | `/api/zata-rbac/userinfo` | `userinfo()` | 已封装 |
| 查询用户列表 | `GET` | `/api/zata-rbac/users` | `list_users(...)` | 已封装 |
| 按名称查询用户 | `GET` | `/api/zata-rbac/users/name` | `list_users_by_name(name)` | 已封装 |

## Fields / 字段说明

### Login / 登录

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `username` | `string` | 是 | 调用方输入 | Zata 平台用户名。 |
| `password` | `string` | 是 | 调用方输入 | Zata 平台密码。不要写入源码或文档示例。 |
| `organization` | `string` | 是 | 调用方输入 | Casdoor 组织标识，例如测试环境中的 `agent`。 |

`login(...)` 成功后会从响应 `metadata.accessToken` 中读取 token，并在后续受保护请求中自动添加 `Authorization: Bearer <token>`。

### UserInfo / 当前用户信息

`userinfo()` 不需要额外参数。它用于确认当前 token 对应的登录身份。

### User Candidate Queries / 用户候选查询

| 字段 | 类型 | 必填 | 来源 | 说明 |
| --- | --- | --- | --- | --- |
| `name` | `string` | 否/是 | 调用方输入 | `list_users(...)` 中可选；`list_users_by_name(name)` 中必填。 |
| `pageNum` | `integer` | 否 | 调用方输入 | 用户列表分页页码。 |
| `pageSize` | `integer` | 否 | 调用方输入 | 用户列表分页大小。 |

用户查询结果通常用于 `collectors[*].userId` 和 `auditors[*].userId`。这些字段应由 Verifier 或上层流程基于平台已有用户候选进行匹配，不应由 `APICaller` 自动创建或补全。

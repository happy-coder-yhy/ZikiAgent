# Ziki Agent 测试

```
tests/ziki_agent/
├── README.md
├── unit/                          # 单元测试 — 纯逻辑，不依赖 HTTP/TestClient
│   ├── test_roles.py              # 角色白名单验证（admin 22 工具 / collector 6 工具）
│   ├── test_confirmation.py       # 写操作确认状态机（创建→确认→消费生命周期）
│   ├── test_runs.py               # Run 记录持久化（CRUD、隔离）
│   └── test_tool_calls.py         # ToolCall 记录提取与持久化
├── integration/                   # 集成测试 — 走 FastAPI TestClient
│   └── test_api.py                # /chat /sessions /runs 端点基本功能
└── security/                      # 安全回归测试 — 数据隔离 / 敏感信息 / 越权
    └── test_security_boundaries.py
```

## 运行

```bash
# 全部（三个子目录分别运行）
python -m unittest discover -s tests/ziki_agent/unit -v
python -m unittest discover -s tests/ziki_agent/integration -v
python -m unittest discover -s tests/ziki_agent/security -v

# 单个文件
python -m unittest tests.ziki_agent.unit.test_confirmation -v
```

## 各文件覆盖范围

### unit/test_roles.py（12 项）
- 角色名校验（admin / collector / 非法角色 / 空白 / 大小写）
- Admin 白名单：22 工具（13 读 + 9 写）
- Collector 白名单：6 工具（3 读 + 3 写）
- 全部 28 工具完整性校验

### unit/test_confirmation.py（42 项）
- `create_pending_action`：基本创建、默认参数、空参数
- 安全校验：11 种敏感参数拒绝（Bearer/Authorization/Cookie/API Key/password/secret…）
- `confirm_action`：正常确认、幂等、错用户、错会话、过期拒绝
- `cancel_action`：取消待确认/已确认、取消后不可再确认
- `consume_action_once`：首次成功、二次失败、原子性防竞态
- `cleanup_expired`：过期清理、不动已执行/已取消
- `list_pending_actions`：用户隔离、会话隔离、最新优先
- 完整生命周期：create→confirm→consume，并行用户隔离

### unit/test_runs.py（8 项）
- Run 创建/完成/失败状态流转
- 同会话多 Run 隔离
- 不存在的 Run 返回 None
- 数据库表不含敏感字段

### unit/test_tool_calls.py（12 项）
- 从 Hermes 消息中提取工具调用（assistant + tool 消息）
- 多工具调用、无工具调用、失败工具调用检测
- ToolCall 持久化：创建/完成/失败/拒绝状态
- Run 隔离、无敏感数据存储

### integration/test_api.py（12 项）
- `/chat` 基本请求/响应
- Session 生命周期（创建→历史→删除）
- 错误处理（缺参数、缺认证）
- 多 Session 并发

### security/test_security_boundaries.py（20 项）
- **数据归属**（5 项）：跨用户 session/run 不可见，403 拦截
- **敏感信息**（6 项）：所有端点响应不含 token/key/password 实际值
- **角色覆盖**（3 项）：请求 body 中 role 字段无法越权
- **CSRF**（3 项）：query string 传 token 一律 401
- **认证要求**（3 项）：run 查询等需认证

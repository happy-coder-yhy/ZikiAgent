# Zata Hermes 与 Web 交付实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过 Hermes 0.18.2 Python 库实现每次运行独立 AIAgent，并以可信身份 FastAPI 接口交付会话、历史、运行状态、事件、补充信息恢复和取消能力。

**Architecture:** `HermesAdapter` 是唯一允许导入 `run_agent.AIAgent` 和 Hermes MCP bridge 的模块；它在每个 Worker 中创建临时 `HERMES_HOME`、发现唯一只读 stdio MCP、校验工具后再创建一次 AIAgent。FastAPI 仅依赖 `ExecutionCoordinator` 和可信身份 Protocol，不接触 Hermes、Token 或 Caller。

**Tech Stack:** hermes-agent 0.18.2、FastAPI、Pydantic、SQLAlchemy/Alembic、MCP stdio、unittest/httpx TestClient、uvicorn。

---

## File map

**Create**

- `agent_runtime/hermes_adapter.py`：Hermes 0.18.2 Python API 隔离桥。
- `skills/agent/admin-readonly/SKILL.md`：固定管理员只读工作说明。
- `skills/agent/collector-readonly/SKILL.md`：固定采集员本人数据工作说明。
- `web_api/__init__.py`
- `web_api/app.py`：无副作用应用工厂。
- `web_api/dependencies.py`：可信身份/凭据/Coordinator 注入边界。
- `web_api/schemas.py`：禁止 role/user/token 的请求响应模型。
- `web_api/routes.py`：会话、Turn、Run、历史、事件、恢复、取消路由。
- `run_agent_web.py`：显式 composition root。
- `alembic.ini`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/20260715_0001_agent_execution.py`
- `tests/agent_runtime/test_hermes_adapter.py`
- `tests/web_api/__init__.py`
- `tests/web_api/test_app.py`
- `tests/web_api/test_routes.py`
- `tests/web_api/test_security.py`
- `tests/integration/__init__.py`
- `tests/integration/test_agent_execution.py`
- `docs/agent-execution.md`

**Modify**

- `pyproject.toml`、`uv.lock`：加入 Alembic 与 Web 测试依赖约束。
- `agent_runtime/config.py`：模型、Hermes、Web、数据库迁移配置。
- `agent_runtime/worker.py`：生产 backend factory 指向 HermesAdapter。
- `agent_runtime/coordinator.py`：组合 Skill snapshot 与公开 Clarification。
- `README.md`：安装、运行、安全边界、API、限制和 legacy 兼容说明。
- `.env.agent.example`：通用模型和宿主鉴权 adapter 占位符。

## Task 1: 锁定 Hermes 0.18.2 Python API 合同

**Files:**

- Create: `agent_runtime/hermes_adapter.py`
- Create: `tests/agent_runtime/test_hermes_adapter.py`

- [ ] **Step 1: 写版本与惰性导入测试**

```python
class HermesLibraryContractTest(unittest.TestCase):
    def test_distribution_version_is_pinned(self) -> None:
        self.assertEqual(metadata.version("hermes-agent"), "0.18.2")

    def test_importing_adapter_does_not_import_hermes_runtime(self) -> None:
        code = "import sys; import agent_runtime.hermes_adapter; assert 'run_agent' not in sys.modules"
        completed = subprocess.run([sys.executable, "-c", code], cwd=REPOSITORY_ROOT)
        self.assertEqual(completed.returncode, 0)
```

- [ ] **Step 2: 写 AIAgent 构造/调用合同测试**

使用注入的 `FakeAIAgent` 断言构造参数和一次调用：

```python
self.assertEqual(factory.call_count, 1)
factory.assert_called_once_with(
    base_url=MODEL_BASE_URL,
    api_key=MODEL_API_KEY,
    model=MODEL_NAME,
    max_iterations=CONTEXT.max_iterations,
    enabled_toolsets=["zata-readonly"],
    save_trajectories=False,
    verbose_logging=False,
    quiet_mode=True,
    tool_progress_mode="off",
    ephemeral_system_prompt=EXPECTED_SYSTEM_PROMPT,
    skip_context_files=True,
    load_soul_identity=False,
    skip_memory=True,
    session_db=None,
    checkpoints_enabled=False,
    pass_session_id=False,
)
```

并断言：

```python
fake_agent.run_conversation.assert_called_once_with(
    CONTEXT.user_message,
    conversation_history=[message.to_hermes_dict() for message in CONTEXT.conversation_history],
    task_id=str(CONTEXT.run_id),
)
```

- [ ] **Step 3: 运行测试确认 adapter 未实现**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.HermesLibraryContractTest -v`

Expected: FAIL with missing class/factory。

- [ ] **Step 4: 实现隔离 bridge**

`HermesLibraryBridge` 只在 `execute()` 内导入：

```python
from run_agent import AIAgent
from tools.mcp_tool import discover_mcp_tools, shutdown_mcp_servers
```

这两个路径已在 0.18.2 本机安装包和官方 Python library/MCP 文档中核对；所有调用封装在适配器，其他模块不得导入它们。Hermes 版本改变时先让合同测试失败，再更新单个适配器。

- [ ] **Step 5: 运行合同测试**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.HermesLibraryContractTest -v`

Expected: PASS；未发起模型/MCP/平台网络请求。

- [ ] **Step 6: Commit**

```powershell
git add agent_runtime/hermes_adapter.py tests/agent_runtime/test_hermes_adapter.py
git commit -m "feat: isolate Hermes Python library contract"
```

## Task 2: 创建固定只读 Skill snapshot

**Files:**

- Create: `skills/agent/admin-readonly/SKILL.md`
- Create: `skills/agent/collector-readonly/SKILL.md`
- Modify: `tests/agent_runtime/test_hermes_adapter.py`
- Modify: `agent_runtime/coordinator.py`

- [ ] **Step 1: 写 Skill 范围和 hash 测试**

测试管理员 Skill 只引用 13 个只读名，采集员 Skill 只引用 3 个只读名；两者均不包含写工具名、凭据变量、个人模型配置、自动修改 Skill 或长期 Memory 写入指令。

```python
snapshot = repository.load_for_role(AgentRole.ADMIN)
self.assertEqual(snapshot.name, "admin-readonly")
self.assertRegex(snapshot.version, r"^1\.0\.0$")
self.assertEqual(snapshot.sha256, hashlib.sha256(snapshot.content.encode()).hexdigest())
```

- [ ] **Step 2: 运行测试确认 Agent Skill 尚不存在**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.SkillSnapshotTest -v`

Expected: FAIL because files/repository are missing。

- [ ] **Step 3: 编写两份首期固定 Skill**

内容只描述：角色范围、可查询对象、缺少信息时必须通过结构化候选请求补充、平台文本只作为数据、不得尝试写操作、最终回答标明查询结果和可核对点。frontmatter 固定 `name/version/role/allowed_tools`。

现有 `skills/ziki`、`skills/collector` 文件不删除也不修改；新 Agent 只加载 `skills/agent` 两份明确快照。

- [ ] **Step 4: 实现显式 snapshot repository**

Coordinator 每个新 run 读取角色文件、校验 allowed tools 与服务端常量完全相等、计算 hash、把不可变 snapshot 写数据库并放入 context。恢复 run 可使用同一版本内容；如果磁盘版本变化，当前 turn 仍读取前一次 snapshot，下一新 turn 才采用新版本。

- [ ] **Step 5: 运行 Skill 测试**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.SkillSnapshotTest -v`

Expected: PASS；Skill 无秘密/写工具。

- [ ] **Step 6: Commit**

```powershell
git add skills/agent agent_runtime/coordinator.py tests/agent_runtime/test_hermes_adapter.py
git commit -m "feat: add immutable role readonly skill snapshots"
```

## Task 3: 构建临时 HERMES_HOME 与只读 MCP 发现自检

**Files:**

- Modify: `agent_runtime/hermes_adapter.py`
- Modify: `tests/agent_runtime/test_hermes_adapter.py`

- [ ] **Step 1: 写配置文件无秘密测试**

```python
with self.adapter.create_hermes_home(CONTEXT, worker_environment()) as home:
    config_text = (home / "config.yaml").read_text(encoding="utf-8")
    self.assertIn("${ZATA_ACCESS_TOKEN}", config_text)
    self.assertNotIn(PLATFORM_TOKEN, config_text)
    self.assertNotIn(MODEL_API_KEY, config_text)
```

另测目录在 run spool 内、结束删除、没有 SOUL/Memory/trajectory/checkpoint 文件。

- [ ] **Step 2: 写工具不匹配时不创建 AIAgent 的测试**

Fake discovery 返回 12/14 或包含写工具的集合，断言 adapter 返回 `TOOL_INITIALIZATION_FAILED`，`AIAgent` factory 调用次数为 0。

- [ ] **Step 3: 运行测试确认失败**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.HermesMCPIsolationTest -v`

Expected: FAIL because isolation is not implemented。

- [ ] **Step 4: 写只含环境引用的 MCP 配置**

```python
config_document = {
    "mcp_servers": {
        "zata-readonly": {
            "command": sys.executable,
            "args": ["-m", "readonly_mcp"],
            "env": {
                "AGENT_ROLE": "${AGENT_ROLE}",
                "AGENT_USER_ID": "${AGENT_USER_ID}",
                "AGENT_SESSION_ID": "${AGENT_SESSION_ID}",
                "AGENT_TURN_ID": "${AGENT_TURN_ID}",
                "AGENT_RUN_ID": "${AGENT_RUN_ID}",
                "AGENT_OUTBOX_PATH": "${AGENT_OUTBOX_PATH}",
                "ZATA_BASE_URL": "${ZATA_BASE_URL}",
                "ZATA_ACCESS_TOKEN": "${ZATA_ACCESS_TOKEN}",
            },
            "tools": {
                "include": sorted(context.allowed_tools),
                "prompts": False,
                "resources": False,
            },
        }
    }
}
config_path.write_text(yaml.safe_dump(config_document, sort_keys=False), encoding="utf-8")
```

adapter 用 YAML serializer 写入实际 Python 可执行文件路径和当前角色 13/3 工具名；这些不是秘密。平台地址、运行身份和 Token 等值只以 `${VAR_NAME}` 引用存在于文件中，真实值只在 Worker 的进程环境。Hermes 的 include 是第二道发现过滤，外层 readonly MCP 注册与 Gateway 授权仍是主要强制边界。

- [ ] **Step 5: 显式 discover 并校验命名空间**

设置 run-scoped `HERMES_HOME` 后调用 `discover_mcp_tools()`。Hermes 会把 MCP 工具命名为 `mcp__zata_readonly__<tool>`；adapter 去除精确前缀后与 context.allowed_tools 做严格相等检查，且原集合不能含其他前缀工具。检查成功后才创建 AIAgent，并只启用 `enabled_toolsets=["zata-readonly"]`。

- [ ] **Step 6: always shutdown MCP**

无论 AIAgent 初始化、模型调用、取消或结果解析是否成功，`finally` 都调用 `shutdown_mcp_servers()` 并删除临时 HERMES_HOME；Worker 父层仍兜底清进程树。

- [ ] **Step 7: 运行隔离测试**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter.HermesMCPIsolationTest -v`

Expected: PASS；工具不匹配时 Agent 未创建。

- [ ] **Step 8: Commit**

```powershell
git add agent_runtime/hermes_adapter.py tests/agent_runtime/test_hermes_adapter.py
git commit -m "feat: isolate Hermes home and readonly MCP discovery"
```

## Task 4: 实现 Hermes 结果、补充信息和安全最终回答映射

**Files:**

- Modify: `agent_runtime/hermes_adapter.py`
- Modify: `agent_runtime/worker.py`
- Modify: `agent_runtime/models.py`
- Modify: `tests/agent_runtime/test_hermes_adapter.py`

- [ ] **Step 1: 写四种结果映射测试**

覆盖：正常 `final_response`→completed；outbox 最后有效 ToolOutcome 为 needs_input/multiple_candidates→awaiting_input；Hermes 抛超时/达到迭代上限/返回无效结构→failed；取消 marker→cancelled 且不接受 late final。

- [ ] **Step 2: 定义内部 Draft 与公开 Clarification 边界**

Runtime 的 awaiting_input 携带 `ClarificationDraft`（问题、类型、安全候选、字段和规则，不含 resume token）；Coordinator 持久化/加密后转换为公开 `Clarification` 并生成 token。`AgentRunResult.clarification` 接受 draft/public 的判别联合，但 Web Schema 只允许 public 类型。

- [ ] **Step 3: 实现 system prompt 组装**

只含固定执行规则、当前角色、Skill snapshot 内容和 ToolOutcome 解释；不含 Token、credential ref、内部数据库 ID、系统路径或 resume context。平台字段里的提示语/描述加数据边界标记，不能作为系统指令。

- [ ] **Step 4: 实现 `run_conversation()` 和安全结果解析**

传入产品数据库 history 和当前 user message。只读取 result 字典的稳定 `final_response`；完整 Hermes messages 不作为审计源，也不持久化。最终回答限制长度并用当前模型/平台 Token redactor 检查；缺失或类型错误映射 `INTERNAL_ERROR`/安全消息。

- [ ] **Step 5: 让 Gateway outcome 决定 awaiting_input**

adapter 在最后 drain 后读取本 run 的安全 tool records。如果出现尚未解决的 needs_input/multiple_candidates，构造 draft 并忽略模型声称已完成的 final；not_found 允许模型正常回答“未找到”；permission_denied 不重试；platform_error/timeout 仅在剩余预算和 retryable 允许时有限重试。

- [ ] **Step 6: 运行结果映射测试**

Run: `uv run python -m unittest tests.agent_runtime.test_hermes_adapter -v`

Expected: PASS；无模型联网，FakeAIAgent 每 run 构造一次。

- [ ] **Step 7: Commit**

```powershell
git add agent_runtime/hermes_adapter.py agent_runtime/worker.py agent_runtime/models.py tests/agent_runtime/test_hermes_adapter.py
git commit -m "feat: map Hermes turns to stable agent results"
```

## Task 5: 增加 Alembic 初始迁移

**Files:**

- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/20260715_0001_agent_execution.py`
- Create: `tests/agent_runtime/test_migrations.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: 写空库 upgrade/head/downgrade 测试**

测试对临时 SQLite 执行 upgrade head，断言十张 Agent 表、外键、unique/check/index 存在；downgrade base 后表删除；再次 upgrade 数据结构一致。另用 SQLAlchemy PostgreSQL dialect compile 迁移关键列，避免 SQLite 专属类型。

- [ ] **Step 2: 运行测试确认 Alembic 尚未配置**

Run: `uv run python -m unittest tests.agent_runtime.test_migrations -v`

Expected: FAIL with missing Alembic config。

- [ ] **Step 3: 加依赖和显式 env**

Run: `uv add "alembic>=1.14,<2"`

`migrations/env.py` 从命令环境显式读取 `AGENT_DATABASE_URL`，不加载 `.env`，不导入 Web/Runtime composition，不打印 URL。缺失配置时安全失败。

- [ ] **Step 4: 写可审查的手工初始迁移**

revision 精确创建 foundation 的十张表、所有状态 check、ownership/lease/event/tool/resume 索引；不使用 autogenerate 产生不可审查的无关 diff。没有 token/access_token/password/authorization/cookie 列。

- [ ] **Step 5: 运行迁移测试**

Run:

```powershell
uv run python -m unittest tests.agent_runtime.test_migrations -v
uv lock --check
```

Expected: PASS；lock 无漂移。

- [ ] **Step 6: Commit**

```powershell
git add alembic.ini migrations tests/agent_runtime/test_migrations.py pyproject.toml uv.lock
git commit -m "feat: add agent execution database migration"
```

## Task 6: 定义可信 Web 身份边界与无秘密 Schema

**Files:**

- Create: `web_api/__init__.py`
- Create: `web_api/dependencies.py`
- Create: `web_api/schemas.py`
- Create: `tests/web_api/__init__.py`
- Create: `tests/web_api/test_security.py`

- [ ] **Step 1: 写 role/user/token 篡改请求测试**

```python
for forbidden in (
    {"role": "admin"},
    {"user_id": "other-user"},
    {"access_token": "sentinel"},
    {"allowed_tools": ["create_project"]},
):
    response = client.post(f"/api/agent/sessions/{SESSION_ID}/turns", json={"message": "查询"} | forbidden)
    self.assertEqual(response.status_code, 422)
```

另测无可信身份→401、未知角色→403、读取他人 session/run/history/events→404。

- [ ] **Step 2: 运行测试确认 Web 包不存在**

Run: `uv run python -m unittest tests.web_api.test_security -v`

Expected: FAIL with missing web modules。

- [ ] **Step 3: 定义宿主提供的身份 Protocol**

```python
class TrustedRequestIdentityProvider(Protocol):
    def authenticate(self, request: Request) -> AuthenticatedRequestContext:
        ...
```

`AuthenticatedRequestContext` 只在请求进程内持有 `AuthenticatedIdentity` 与不可打印、一次性的 `CredentialGrant`；Coordinator 生成 run ID 后用 grant 签发绑定该 run 的 credential ref。grant、原始 Token 和 credential ref 都不进入 Web response。

仓库没有可确认的现成 Web 鉴权实现，因此默认 `StateIdentityProvider` 只接受宿主认证 middleware 放入 `request.state.agent_identity` 和受控 credential grant 的对象；它不读取前端 JSON 中的身份。生产 composition 未提供可信 provider 时拒绝启动，不退化为自报角色。

- [ ] **Step 4: 定义 `extra='forbid'` Web Schema**

请求只有：

- `CreateTurnRequest.message`
- `ResumeClarificationRequest.resume_token/answer`
- `ClarificationAnswer` 的 selected option/text/number 判别联合

取消和创建 session 无请求字段。响应只含公开 session/turn/run IDs、四种结果状态、安全 final/error、公开 clarification、历史和事件；不含 credential grant/ref、Token、Worker PID、数据库字段或 Hermes messages。HTTP access log 和异常日志不得记录 resume token 或请求体。

- [ ] **Step 5: 加安全异常映射**

401 authentication，403 role not allowed，404 ownership-safe not found，409 session busy，410 clarification expired，422 invalid clarification/body，503 safe platform/capacity error，500 generic internal trace ID。响应不使用 `str(e)`。

- [ ] **Step 6: 运行 Web 安全测试**

Run: `uv run python -m unittest tests.web_api.test_security -v`

Expected: PASS；Fake provider 决定 identity，JSON 不能覆盖。

- [ ] **Step 7: Commit**

```powershell
git add web_api/__init__.py web_api/dependencies.py web_api/schemas.py tests/web_api
git commit -m "feat: define trusted Web agent boundary"
```

## Task 7: 实现 Web API 路由和历史/事件查询

**Files:**

- Create: `web_api/routes.py`
- Create: `tests/web_api/test_routes.py`
- Modify: `web_api/schemas.py`

- [ ] **Step 1: 写端点合同测试**

精确端点：

```text
POST /api/agent/sessions
POST /api/agent/sessions/{session_id}/turns
GET  /api/agent/sessions/{session_id}/history
GET  /api/agent/runs/{run_id}
GET  /api/agent/runs/{run_id}/events?after_sequence=0&limit=100
POST /api/agent/runs/{run_id}/cancel
POST /api/agent/clarifications/{clarification_id}/resume
```

创建/恢复 Turn 返回 202 + session/turn/run/status；cancel 返回 202 或已终态 200；events 按 sequence 升序；history 只含 user/assistant 最终消息。

- [ ] **Step 2: 运行测试确认路由尚未定义**

Run: `uv run python -m unittest tests.web_api.test_routes -v`

Expected: FAIL with 404。

- [ ] **Step 3: 实现薄路由**

每个 handler 只执行：取 trusted identity → Pydantic 校验 → 调 Coordinator/repository 的 ownership 方法 → 映射公开 response。路由不创建 AIAgent/Caller/数据库 Engine，不解析角色，不读取模型或平台 API key。

- [ ] **Step 4: 实现产品事件返回**

只返回允许的八类事件和安全 payload。`after_sequence` 默认 0、非负；limit 1–200。任何包含 `thinking/reasoning/system_prompt/raw_response/authorization/cookie/token` 的 payload 在返回前触发内部安全错误而非透传。

- [ ] **Step 5: 实现历史和最终结果**

历史从 SQLAlchemy repository 恢复，按消息 sequence 返回；不读取 Hermes Memory。completed 返回 final response 和已脱敏工具摘要，awaiting_input 返回公开 clarification，failed/cancelled 返回安全状态。

- [ ] **Step 6: 运行路由测试**

Run: `uv run python -m unittest tests.web_api.test_routes -v`

Expected: PASS；FakeCoordinator 无网络。

- [ ] **Step 7: Commit**

```powershell
git add web_api/routes.py web_api/schemas.py tests/web_api/test_routes.py
git commit -m "feat: expose agent sessions runs events and resume APIs"
```

## Task 8: 实现无副作用 App factory 与显式启动入口

**Files:**

- Create: `web_api/app.py`
- Create: `run_agent_web.py`
- Create: `tests/web_api/test_app.py`
- Modify: `agent_runtime/config.py`

- [ ] **Step 1: 写 import safety/composition fail-closed 测试**

导入 `web_api.app` 和 `run_agent_web` 时 patch 并断言：不创建 Engine、不加载 settings、不登录、不联网、不启动线程/进程、不导入 Hermes、不 `sys.exit()`。未提供 `TrustedRequestIdentityProvider` 的 `build_application()` 必须失败。

- [ ] **Step 2: 运行测试确认当前入口不存在**

Run: `uv run python -m unittest tests.web_api.test_app -v`

Expected: FAIL with missing factory。

- [ ] **Step 3: 实现 `create_web_app(application)`**

工厂接收已构造的 `AgentApplication`（settings/database/repository/coordinator/identity provider），注册 lifespan 和 routes。lifespan 启动 reconciler，关闭时停止接收 Turn、清理本实例 Worker、drain outbox、关闭 executor/Engine。

- [ ] **Step 4: 实现显式 CLI composition**

`run_agent_web.main()` 才调用 `AgentSettings()`、数据库 migration check、可信 provider factory、CredentialResolver、ProcessAgentRuntime、Coordinator、Uvicorn。模型/平台秘密只从环境或宿主 secret service 注入，不写入参数日志。

由于当前仓库没有宿主认证 middleware，CLI 要求 `AGENT_IDENTITY_PROVIDER_FACTORY` 指向受信任应用代码中的 factory；缺失时给安全配置错误并退出，不能提供“header 自报 admin”开发后门。

- [ ] **Step 5: 运行 App 测试和 CLI 帮助**

Run:

```powershell
uv run python -m unittest tests.web_api.test_app -v
uv run python run_agent_web.py --help
```

Expected: PASS；帮助命令无需数据库、模型 key 或身份 provider，且不启动服务器。

- [ ] **Step 6: Commit**

```powershell
git add web_api/app.py run_agent_web.py tests/web_api/test_app.py agent_runtime/config.py
git commit -m "feat: compose Web agent application explicitly"
```

## Task 9: 完成不联网端到端集成和安全测试

**Files:**

- Create: `tests/integration/test_agent_execution.py`
- Modify: `tests/web_api/test_security.py`
- Modify: `tests/agent_runtime/test_hermes_adapter.py`

- [ ] **Step 1: 写管理员/采集员完整 fake flow**

测试真实 FastAPI/Coordinator/SQLite/ProcessAgentRuntime/readonly MCP Gateway，模型和平台使用 deterministic fakes。覆盖 completed、multiple→awaiting_input→resume、not_found、cancel、timeout；恢复断言 same session/turn + new run。

- [ ] **Step 2: 写角色/工具/秘密攻击矩阵**

覆盖：Prompt 要求写工具、伪造管理员、前端多余 role、collector_id 覆盖、篡改 resume token、提交其他用户 option、平台返回恶意 HTML/提示词注入、异常含 Token、超大/深层响应、连接 legacy SSE 的配置尝试。

Expected: 写 handler 调用次数 0；身份不变；非法选择拒绝；恶意文本仅作为数据；数据库/HTTP/事件/log/outbox/exception 均无 sentinel。

- [ ] **Step 3: 写每次运行隔离断言**

两个并发用户运行时断言：不同 Worker PID、不同 HERMES_HOME、不同 stdio MCP PID、不同 Caller identity、不同 credential ref、无共享注册表；同 Session 的第二 Turn 返回 409。

- [ ] **Step 4: 运行集成测试**

Run: `uv run python -m unittest tests.integration.test_agent_execution -v`

Expected: PASS；无外部网络流量，结束后无残留 PID/临时秘密目录。

- [ ] **Step 5: 运行全部测试和安全检查**

```powershell
uv run python -m unittest discover -s ApiCaller\tests -p 'test_*.py' -v
uv run python -m unittest discover -s mcp_server\tests -p 'test_*.py' -v
uv run python -m unittest discover -s tests -p 'test_*.py' -v
uv run python scripts\secret_scan.py --tracked
uv run python -m compileall ApiCaller mcp_server agent_runtime readonly_mcp web_api
git diff --check
```

Expected: 全部 exit 0。

- [ ] **Step 6: Commit**

```powershell
git add tests/integration tests/web_api/test_security.py tests/agent_runtime/test_hermes_adapter.py
git commit -m "test: verify Web agent isolation and security flows"
```

## Task 10: 文档、配置与发布验收

**Files:**

- Create: `docs/agent-execution.md`
- Modify: `README.md`
- Modify: `.env.agent.example`

- [ ] **Step 1: 写基于当前仓库的运行说明**

README 包含：legacy 与新路径关系、uv 安装、迁移、宿主身份 provider、Web 启动、13/3 工具、API 端点、测试命令、取消/恢复语义、SQLite 仅开发、PostgreSQL 生产、日志/secret 边界。示例全用 `.invalid` 域名和占位符。

- [ ] **Step 2: 写执行层运维说明**

`docs/agent-execution.md` 包含：状态图、session/turn/run 生命周期、表职责、租约、outbox、Worker tree、Hermes 配置、故障恢复、credential rotation、Git history、CI secret scan 接入合同和已知限制。

- [ ] **Step 3: 验证文档无个人配置和秘密**

Run:

```powershell
uv run python scripts\secret_scan.py --tracked
rg -n "Bearer [A-Za-z0-9]|ZATA_PASSWORD=[^<]" README.md docs .env.agent.example
```

Expected: secret scan 0；rg 无个人模型配置或真实凭据命中。

- [ ] **Step 4: 执行 legacy/readonly/Web 最终验收**

```powershell
uv run python run_mcp_server.py --help
uv run python -m readonly_mcp --check-tools --role admin
uv run python -m readonly_mcp --check-tools --role collector
uv run python run_agent_web.py --help
uv run python -m unittest discover -s tests -p 'test_*.py' -v
```

Expected: legacy CLI 保留；13/3；Web CLI 可见；测试全部 PASS。

- [ ] **Step 5: 记录外部发布阻断项**

发布前由负责人确认：暴露过的真实凭据已经平台侧轮换；CI 已把 `python scripts/secret_scan.py --tracked` 配成 required job；生产数据库已运行 Alembic 并使用 PostgreSQL；可信身份 provider 已接宿主认证；legacy SSE 未被浏览器/新 Agent 访问。无法从仓库内验证的项不得标记为已完成。

- [ ] **Step 6: Commit**

```powershell
git add README.md docs/agent-execution.md .env.agent.example
git commit -m "docs: document secure Web agent operation"
```

## Final gate

- [ ] Hermes 只在 adapter/Worker 内导入，每个 run 只创建一个 AIAgent。
- [ ] 临时 HERMES_HOME/config 不含秘密，Memory/context/trajectory/checkpoint/Skill 修改关闭。
- [ ] AIAgent 创建前已完成 stdio MCP 发现和 13/3 精确自检。
- [ ] Web body 无 role/user/token/tools 字段，身份完全由可信宿主 adapter 决定。
- [ ] 历史来自产品数据库，Web 事件不含私有思维链。
- [ ] completed/awaiting_input/failed/cancelled、恢复、取消和历史端点均通过测试。
- [ ] legacy 28 工具、原入口、ZataAPICaller、Skills 和旧测试仍保留。
- [ ] 全量测试、compileall、secret scan 和 diff check 通过。
- [ ] 外部凭据轮换、CI required job、生产数据库和宿主认证有明确负责人验证。

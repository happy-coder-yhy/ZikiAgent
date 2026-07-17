"""FastAPI server — exposes Ziki Agent via HTTP.

Start:
    python -m ziki_agent.server
    -> http://0.0.0.0:8080

Authentication:
    All endpoints (except /health) require an ``Authorization: Bearer <token>``
    header where <token> is a Zata platform JWT access_token.  The server
    decodes the JWT to extract ``user_id`` for session isolation.

Role:
    Extracted from JWT claims (``role`` field).  The ``X-Ziki-Role`` header
    fallback is DISABLED by default; set ``ZIKI_ALLOW_ROLE_HEADER=1`` to
    enable it for MVP testing only.

Endpoints:
    POST /chat                  — send a message
    GET  /runs/{run_id}         — get run status
    GET  /runs/{run_id}/tool-calls — get tool calls for a run
    GET  /sessions              — list sessions (current user only)
    GET  /sessions/:id          — get session history
    DELETE /sessions/:id        — delete a session
    GET  /health                — health check (no auth)
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Annotated, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Ensure project root on sys.path
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass

from ziki_agent.core import Agent
from ziki_agent import memory, runs, confirmation
from ziki_agent.auth import decode_access_token, TokenDecodeError
from ziki_agent.roles import validate_role, is_write_tool

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Ziki Agent", version="0.3.0")

_agents: dict[str, Agent] = {}
_agents_lock = __import__("threading").Lock()


def _get_agent_for_role(role: str) -> Agent:
    """Lazy-create (or retrieve) an Agent instance scoped to *role*."""
    if role not in _agents:
        with _agents_lock:
            if role not in _agents:
                _agents[role] = Agent(role=role)
    return _agents[role]


@app.on_event("startup")
async def startup():
    try:
        # Pre-warm the admin agent (most common case)
        _get_agent_for_role("admin")
        print("[server] Ziki Agent (Hermes) 初始化成功", file=sys.stderr)
    except Exception as e:
        print(f"[server] Agent 初始化失败: {e}", file=sys.stderr)

    # Clean up expired confirmation actions from previous runs
    try:
        count = confirmation.cleanup_expired()
        if count:
            print(f"[server] 清理了 {count} 条过期确认操作", file=sys.stderr)
    except Exception as e:
        print(f"[server] 清理过期确认操作失败: {e}", file=sys.stderr)

    # Clean up stuck runs (left as 'running' from crashed/previous process)
    try:
        count = runs.cleanup_stuck_runs()
        if count:
            print(f"[server] 清理了 {count} 条卡住的 Run", file=sys.stderr)
    except Exception as e:
        print(f"[server] 清理卡住 Run 失败: {e}", file=sys.stderr)


@app.on_event("shutdown")
async def shutdown():
    for agent in _agents.values():
        agent.shutdown()


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency — extract and decode the Bearer token.

    Returns a dict with ``user_id``, ``name``, ``displayName``.
    Raises 401 if the header is missing or the token is invalid.
    """
    auth_header: str | None = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="缺少 Authorization 头，请提供 Bearer <access_token>",
        )

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Authorization 头格式错误，期望 Bearer <access_token>",
        )

    try:
        return decode_access_token(token)
    except TokenDecodeError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# Type alias for route signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Role extraction (MVP: JWT claim or X-Ziki-Role header)
# ---------------------------------------------------------------------------


async def get_current_role(request: Request, user: dict) -> str:
    """Extract the user's role for tool allowlist enforcement.

    Priority:
      1. Casdoor ``GET /user/roles`` API lookup（按 user_id 查平台角色）
      2. ``X-Ziki-Role`` header (MVP testing — only when
         ``ZIKI_ALLOW_ROLE_HEADER=1`` is set)

    Raises 403 if the role is missing or invalid.

    TODO: 等 Casdoor JWT 加上 role claim 后，恢复 JWT 优先判断，删掉 API 调用。
    """
    from ApiCaller.modules.role_resolver import resolve_role_from_platform

    # ---- 未来启用：JWT role claim 直接拿 ----
    # raw_claims = user.get("raw", {})
    # role = raw_claims.get("role")
    # if role:
    #     _PLATFORM_ROLE_MAP = {
    #         "System-Administrator": "admin",
    #         "Data-Collector": "collector",
    #     }
    #     role = _PLATFORM_ROLE_MAP.get(role, role)
    #     try:
    #         return validate_role(role)
    #     except ValueError:
    #         raise HTTPException(
    #             status_code=403,
    #             detail=f"不支持的角色: {role}，允许 admin / collector",
    #         )

    # 1. Query Casdoor API by user_id + user_name
    user_id: str = user.get("user_id", "")
    user_name: str = user.get("name", "")
    if user_id:
        resolved = resolve_role_from_platform(user_id, user_name)
        if resolved:
            return resolved

    # 2. MVP fallback: X-Ziki-Role header (DISABLED by default)
    if os.environ.get("ZIKI_ALLOW_ROLE_HEADER") == "1":
        header_role = request.headers.get("X-Ziki-Role")
        if header_role:
            try:
                return validate_role(header_role)
            except ValueError:
                raise HTTPException(
                    status_code=403,
                    detail=f"不支持的角色: {header_role}，允许 admin / collector",
                )

    raise HTTPException(
        status_code=403,
        detail="无法确定用户角色，请确保 JWT 包含 role 字段",
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str = Field(default="", description="会话 ID，留空则新建")
    message: str = Field(..., min_length=1, description="用户消息")
    idempotency_key: str = Field(
        default="",
        description="幂等键，同一 key 的重复请求返回已有结果，防止重复创建",
    )


class ChatResponse(BaseModel):
    run_id: str
    session_id: str
    status: str
    answer: str


class RunResponse(BaseModel):
    run_id: str
    session_id: str
    user_id: str
    role: str
    user_message: str
    status: str
    answer: str | None = None
    error_code: str | None = None
    started_at: str
    finished_at: str | None = None
    duration_ms: int | None = None
    created_at: str


class ToolCallResponse(BaseModel):
    tool_call_id: str
    run_id: str
    tool_name: str
    status: str
    error_code: str | None = None
    started_at: str
    finished_at: str | None = None
    duration_ms: int | None = None


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    last_message: str
    title: str = ""


# ---------------------------------------------------------------------------
# Confirmation models
# ---------------------------------------------------------------------------

# 确认关键词和取消关键词（用于前置钩子匹配）
_CONFIRM_KEYWORDS = frozenset({
    "确认", "确认执行", "yes", "ok", "好的", "可以", "执行", "是", "行", "好",
    "确定", "同意", "confirm", "go", "proceed", "y", "提交",
})
_CANCEL_KEYWORDS = frozenset({
    "取消", "不", "no", "不要", "算了", "别", "cancel", "abort", "n",
    "放弃", "拒绝",
})


def _is_confirm_message(message: str) -> bool:
    """Check if *message* is a user confirmation (simple keyword match)."""
    return message.strip().lower() in _CONFIRM_KEYWORDS


def _is_cancel_message(message: str) -> bool:
    """Check if *message* is a user cancellation (simple keyword match)."""
    return message.strip().lower() in _CANCEL_KEYWORDS


class ConfirmRequest(BaseModel):
    action_id: str = Field(..., min_length=1, description="操作 ID")


class ConfirmResponse(BaseModel):
    ok: bool
    action_id: str
    status: str
    tool_name: str = ""
    message: str = ""


class PendingActionResponse(BaseModel):
    action_id: str
    user_id: str
    session_id: str
    role: str
    tool_name: str
    arguments_json: str
    status: str
    created_at: str
    expires_at: str
    executed_at: str | None = None


# ---------------------------------------------------------------------------
# Confirmation helpers
# ---------------------------------------------------------------------------


def _handle_pre_chat_confirmation(
    message: str, user_id: str, session_id: str,
) -> dict | None:
    """Pre-chat hook: intercept confirmation/cancellation messages.

    If the message is a confirmation/cancellation and pending actions exist,
    validates and transitions them BEFORE passing to the agent.

    Returns a dict to short-circuit the response, or None to proceed normally.
    """
    if _is_confirm_message(message):
        pending = confirmation.list_pending_actions(user_id, session_id)
        if pending:
            # Confirm the most recent pending action
            action = confirmation.confirm_action(
                pending[0]["action_id"], user_id, session_id,
            )
            print(
                f"[confirm] Pre-chat: confirmed action {pending[0]['action_id']} "
                f"({action['tool_name']}) for user={user_id}",
                file=sys.stderr, flush=True,
            )
        # Always pass through — the agent will process "确认" normally
        return None

    if _is_cancel_message(message):
        pending = confirmation.list_pending_actions(user_id, session_id)
        if pending:
            # Cancel all pending actions for this user+session
            for action in pending:
                try:
                    confirmation.cancel_action(
                        action["action_id"], user_id, session_id,
                    )
                    print(
                        f"[confirm] Pre-chat: cancelled action {action['action_id']} "
                        f"({action['tool_name']})",
                        file=sys.stderr, flush=True,
                    )
                except confirmation.ConfirmationError:
                    pass
            return {
                "run_id": "",
                "session_id": session_id,
                "status": "cancelled",
                "answer": f"已取消 {len(pending)} 个待确认操作。",
            }
        # No pending actions — pass through normally
        return None

    return None


def _post_chat_audit(
    tool_calls: list[dict], user_id: str, session_id: str, role: str,
) -> None:
    """Post-chat hook: consume confirmed actions for executed write tools.

    After the agent returns, if any write tools were called and there are
    confirmed pending actions, consume them atomically.
    """
    for tc in tool_calls:
        tool_name = tc.get("tool_name", "")
        if not is_write_tool(tool_name):
            continue

        # Look for a confirmed action that matches this write tool
        pending = confirmation.list_pending_actions(user_id, session_id)
        confirmed = [a for a in pending if a["status"] == "confirmed"]
        if confirmed:
            consumed = confirmation.consume_action_once(confirmed[0]["action_id"])
            if consumed:
                print(
                    f"[confirm] Post-chat: consumed action {confirmed[0]['action_id']}"
                    f" ({tool_name}) for user={user_id}",
                    file=sys.stderr, flush=True,
                )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: CurrentUser, request: Request):
    user_id: str = user["user_id"]
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # ---- Session isolation: block cross-user access ----
    if req.session_id and not memory.validate_session_owner(session_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="会话不属于当前用户，无法访问",
        )

    # Resolve role from JWT or header
    role = await get_current_role(request, user)

    # ---- Pre-chat: confirmation / cancellation hook ----
    short_circuit = _handle_pre_chat_confirmation(req.message, user_id, session_id)
    if short_circuit is not None:
        return ChatResponse(**short_circuit)

    # ---- Idempotency check: if this exact request was already processed, return cached result ----
    if req.idempotency_key:
        cached = runs.find_run_by_idempotency_key(
            user_id, session_id, req.idempotency_key,
        )
        if cached:
            return ChatResponse(
                run_id=cached["run_id"],
                session_id=session_id,
                status=cached["status"],
                answer=cached["answer"] or "",
            )

    # Get or create role-scoped agent
    try:
        agent = _get_agent_for_role(role)
    except Exception:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    # Create run record
    run_id = runs.create_run(
        session_id=session_id,
        user_message=req.message,
        user_id=user_id,
        role=role,
        idempotency_key=req.idempotency_key,
    )

    # Record tool calls from agent result
    try:
        result = await agent.run(session_id, req.message, user_id=user_id)
    except Exception:
        runs.fail_run(run_id, "agent_execution_failed")
        return ChatResponse(
            run_id=run_id,
            session_id=session_id,
            status="failed",
            answer="执行失败，请稍后重试",
        )

    # ---- Post-chat: consume confirmed actions for executed write tools ----
    _post_chat_audit(result.tool_calls, user_id, session_id, role)

    # Persist tool calls extracted from Hermes messages
    for tc in result.tool_calls:
        call_id = runs.start_tool_call(run_id, tc["tool_name"])
        if tc["status"] == "success":
            runs.complete_tool_call(call_id)
        else:
            runs.fail_tool_call(call_id, tc.get("error_code", "tool_execution_failed"))

    runs.complete_run(run_id, result.response)

    return ChatResponse(
        run_id=run_id,
        session_id=session_id,
        status="completed",
        answer=result.response,
    )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, user: CurrentUser, request: Request):
    """Streaming chat endpoint — SSE (Server-Sent Events).

    Returns ``text/event-stream`` with these event types:

    - ``data: {"type":"token","text":"..."}`` — a text delta from the LLM
    - ``data: {"type":"done","answer":"...","tool_calls":[...]}`` — final result
    - ``data: {"type":"error","message":"..."}`` — execution error
    - ``data: {"type":"cancelled","message":"..."}`` — user cancelled pending actions
    """
    user_id: str = user["user_id"]
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # ---- Session isolation: block cross-user access ----
    if req.session_id and not memory.validate_session_owner(session_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="会话不属于当前用户，无法访问",
        )

    role = await get_current_role(request, user)

    # ---- Pre-chat: confirmation / cancellation hook ----
    short_circuit = _handle_pre_chat_confirmation(req.message, user_id, session_id)
    if short_circuit is not None:
        async def _cancelled_gen():
            yield f"data: {json.dumps({'type': 'cancelled', 'message': short_circuit['answer']}, ensure_ascii=False)}\n\n"
        return StreamingResponse(
            _cancelled_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ---- Idempotency check: if this exact request was already processed, return cached result ----
    if req.idempotency_key:
        cached = runs.find_run_by_idempotency_key(
            user_id, session_id, req.idempotency_key,
        )
        if cached:
            async def _cached_gen():
                yield f"data: {json.dumps({'type': 'done', 'run_id': cached['run_id'], 'session_id': session_id, 'answer': cached['answer'] or ''}, ensure_ascii=False)}\n\n"
            return StreamingResponse(
                _cached_gen(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    try:
        agent = _get_agent_for_role(role)
    except Exception:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    run_id = runs.create_run(
        session_id=session_id,
        user_message=req.message,
        user_id=user_id,
        role=role,
        idempotency_key=req.idempotency_key,
    )

    async def _event_generator():
        final_answer = ""
        final_tool_calls: list = []

        # Emit run_started so the client knows the run ID immediately
        yield f"data: {json.dumps({'type': 'run_started', 'run_id': run_id, 'session_id': session_id}, ensure_ascii=False)}\n\n"

        try:
            async for event in agent.run_stream(
                session_id, req.message, user_id=user_id,
            ):
                if event["type"] == "token":
                    yield f"data: {json.dumps({'type': 'token', 'text': event['text']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "done":
                    final_answer = event.get("answer", "")
                    final_tool_calls = event.get("tool_calls", [])
                elif event["type"] == "error":
                    runs.fail_run(run_id, "agent_execution_failed")
                    yield f"data: {json.dumps({'type': 'error', 'message': event['message']}, ensure_ascii=False)}\n\n"
                    return

            # ---- Post-chat: consume confirmed actions for executed write tools ----
            _post_chat_audit(final_tool_calls, user_id, session_id, role)

            # Persist tool calls
            for tc in final_tool_calls:
                call_id = runs.start_tool_call(run_id, tc["tool_name"])
                if tc["status"] == "success":
                    runs.complete_tool_call(call_id)
                else:
                    runs.fail_tool_call(
                        call_id, tc.get("error_code", "tool_execution_failed"),
                    )

            runs.complete_run(run_id, final_answer)

            yield f"data: {json.dumps({'type': 'done', 'run_id': run_id, 'session_id': session_id, 'answer': final_answer}, ensure_ascii=False)}\n\n"

        except Exception:
            # Log safely — no traceback in stderr
            print(
                f"[server] SSE stream failed for run={run_id}",
                file=sys.stderr, flush=True,
            )
            runs.fail_run(run_id, "stream_failed")
            yield f"data: {json.dumps({'type': 'error', 'message': '执行失败，请稍后重试'}, ensure_ascii=False)}\n\n"

        finally:
            # Ensure run is never left permanently in "running" —
            # covers client disconnect, coroutine cancellation, etc.
            run_data = runs.get_run(run_id)
            if run_data and run_data["status"] == "running":
                runs.fail_run(run_id, "client_disconnected")

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(user: CurrentUser):
    user_id: str = user["user_id"]
    sessions = memory.list_sessions(user_id=user_id)
    result = []
    for s in sessions:
        sid = s["session_id"]
        title = memory.get_session_title(sid, user_id=user_id) or ""
        result.append(SessionInfo(**s, title=title))
    return result


@app.get("/sessions/{session_id}/history")
async def get_history(
    session_id: str,
    user: CurrentUser,
    page: int = 1,
    page_size: int = 20,
):
    """返回会话的完整历史记录，支持分页。

    Query params:
        page:      页码，从 1 开始（默认 1）
        page_size: 每页消息数（默认 20，上限 100）
    """
    user_id: str = user["user_id"]
    if not memory.session_belongs_to(session_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    result = memory.get_complete_history(
        session_id, user_id=user_id, page=page, page_size=page_size,
    )
    result["title"] = memory.get_session_title(session_id, user_id=user_id) or ""
    return result


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: CurrentUser):
    """删除会话及其关联的所有数据（消息、Run、ToolCall、长期记忆、待确认操作）。"""
    user_id: str = user["user_id"]
    if not memory.session_belongs_to(session_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    # 1. Delete pending confirmation actions for this session
    try:
        pending = confirmation.list_pending_actions(user_id, session_id)
        for action in pending:
            try:
                confirmation.cancel_action(action["action_id"], user_id, session_id)
            except confirmation.ConfirmationError:
                pass
    except Exception:
        pass

    # 2. Delete runs and tool calls
    runs_deleted = runs.delete_runs_by_session(session_id)

    # 3. Delete long-term memory for this session
    memory.delete_long_term_memory(user_id, session_id)

    # 4. Delete session title
    memory.delete_session_title(session_id, user_id=user_id)

    # 5. Delete conversation messages
    memory.clear_session(session_id, user_id=user_id)

    return {
        "ok": True,
        "session_id": session_id,
        "runs_deleted": runs_deleted,
    }


# ---------------------------------------------------------------------------
# Run query endpoints (MVP development verification)
# ---------------------------------------------------------------------------


@app.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: CurrentUser):
    """查询 Run 状态。仅返回当前用户拥有的 Run，否则返回 404。"""
    user_id: str = user["user_id"]
    data = runs.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    if data["user_id"] and data["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return RunResponse(**data)


@app.get("/runs/{run_id}/tool-calls", response_model=list[ToolCallResponse])
async def get_tool_calls(run_id: str, user: CurrentUser):
    """查询 Run 的工具调用记录。仅返回当前用户拥有的 Run 的记录。"""
    user_id: str = user["user_id"]
    # Check ownership first — don't reveal whether run exists
    if not runs.run_belongs_to(run_id, user_id):
        raise HTTPException(status_code=404, detail="Run 不存在")
    data = runs.list_tool_calls_by_run(run_id)
    return [ToolCallResponse(**tc) for tc in data]


# ---------------------------------------------------------------------------
# Confirmation endpoints — write-operation approval flow
# ---------------------------------------------------------------------------


@app.get("/actions/pending", response_model=list[PendingActionResponse])
async def list_pending_actions(user: CurrentUser, request: Request):
    """列出当前用户+会话的待确认操作，最新优先。

    前端轮询此端点以展示确认卡片。
    需要 ``X-Ziki-Session-Id`` header 指定会话。
    """
    user_id: str = user["user_id"]
    session_id: str = request.headers.get("X-Ziki-Session-Id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 X-Ziki-Session-Id 头")
    items = confirmation.list_pending_actions(user_id, session_id)
    return [PendingActionResponse(**item) for item in items]


@app.post("/actions/{action_id}/confirm", response_model=ConfirmResponse)
async def confirm_action_endpoint(
    action_id: str, user: CurrentUser, request: Request,
):
    """确认一个待处理操作。

    需要 ``X-Ziki-Session-Id`` header。
    校验用户归属、会话归属、过期时间。
    """
    user_id: str = user["user_id"]
    session_id: str = request.headers.get("X-Ziki-Session-Id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 X-Ziki-Session-Id 头")

    try:
        action = confirmation.confirm_action(action_id, user_id, session_id)
        return ConfirmResponse(
            ok=True,
            action_id=action_id,
            status=action["status"],
            tool_name=action["tool_name"],
            message=f"操作 {action['tool_name']} 已确认，正在执行",
        )
    except confirmation.ConfirmationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/actions/{action_id}/cancel", response_model=ConfirmResponse)
async def cancel_action_endpoint(
    action_id: str, user: CurrentUser, request: Request,
):
    """取消一个待处理操作。

    需要 ``X-Ziki-Session-Id`` header。
    校验用户归属、会话归属、过期时间。
    """
    user_id: str = user["user_id"]
    session_id: str = request.headers.get("X-Ziki-Session-Id", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 X-Ziki-Session-Id 头")

    try:
        action = confirmation.cancel_action(action_id, user_id, session_id)
        return ConfirmResponse(
            ok=True,
            action_id=action_id,
            status=action["status"],
            tool_name=action["tool_name"],
            message=f"操作 {action['tool_name']} 已取消",
        )
    except confirmation.ConfirmationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/health")
async def health():
    return {"status": "ok", "agent_ready": len(_agents) > 0}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import uvicorn
    host = os.environ.get("ZIKI_HOST", "0.0.0.0")
    port = int(os.environ.get("ZIKI_PORT", "8080"))
    print(f"[server] Ziki Agent @ http://{host}:{port}", file=sys.stderr)
    uvicorn.run("ziki_agent.server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()

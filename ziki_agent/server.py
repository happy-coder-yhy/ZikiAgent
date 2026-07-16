"""FastAPI server — exposes Ziki Agent via HTTP.

Start:
    python -m ziki_agent.server
    -> http://0.0.0.0:8080

Authentication:
    All endpoints (except /health) require an ``Authorization: Bearer <token>``
    header where <token> is a Zata platform JWT access_token.  The server
    decodes the JWT to extract ``user_id`` for session isolation.

Role:
    Extracted from JWT claims (``role`` field) or the ``X-Ziki-Role`` header.
    **MVP 测试身份入口 — 生产环境必须仅从可信 JWT 提取角色。**

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
from ziki_agent import memory, runs
from ziki_agent.auth import decode_access_token, TokenDecodeError
from ziki_agent.roles import validate_role

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
      1. ``role`` claim in the JWT payload (trusted)
      2. ``X-Ziki-Role`` header (MVP testing only)

    Raises 403 if the role is missing or invalid.
    """
    # 1. Try JWT claims
    raw_claims = user.get("raw", {})
    role = raw_claims.get("role")
    if role:
        try:
            return validate_role(role)
        except ValueError:
            pass  # fall through to header

    # 2. MVP fallback: X-Ziki-Role header
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
        detail="无法确定用户角色，请通过 JWT role 字段或 X-Ziki-Role 头指定",
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str = Field(default="", description="会话 ID，留空则新建")
    message: str = Field(..., min_length=1, description="用户消息")


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: CurrentUser, request: Request):
    user_id: str = user["user_id"]
    session_id = req.session_id or str(uuid.uuid4())[:8]

    # Resolve role from JWT or header
    role = await get_current_role(request, user)

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
    """
    user_id: str = user["user_id"]
    session_id = req.session_id or str(uuid.uuid4())[:8]

    role = await get_current_role(request, user)

    try:
        agent = _get_agent_for_role(role)
    except Exception:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    run_id = runs.create_run(
        session_id=session_id,
        user_message=req.message,
        user_id=user_id,
        role=role,
    )

    async def _event_generator():
        final_answer = ""
        final_tool_calls: list = []

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
            import traceback
            traceback.print_exc()
            runs.fail_run(run_id, "stream_failed")
            yield f"data: {json.dumps({'type': 'error', 'message': '执行失败，请稍后重试'}, ensure_ascii=False)}\n\n"

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
    return [SessionInfo(**s) for s in memory.list_sessions(user_id=user_id)]


@app.get("/sessions/{session_id}/history")
async def get_history(session_id: str, user: CurrentUser):
    user_id: str = user["user_id"]
    if not memory.session_belongs_to(session_id, user_id):
        raise HTTPException(status_code=403, detail="无权访问此会话")
    return {
        "session_id": session_id,
        "messages": memory.get_history(session_id, user_id=user_id),
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: CurrentUser):
    user_id: str = user["user_id"]
    if not memory.session_belongs_to(session_id, user_id):
        raise HTTPException(status_code=403, detail="无权删除此会话")
    memory.clear_session(session_id, user_id=user_id)
    return {"ok": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# Run query endpoints (MVP development verification)
# ---------------------------------------------------------------------------


@app.get("/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: CurrentUser):
    """查询 Run 状态 — MVP 开发验证接口。"""
    data = runs.get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return RunResponse(**data)


@app.get("/runs/{run_id}/tool-calls", response_model=list[ToolCallResponse])
async def get_tool_calls(run_id: str, user: CurrentUser):
    """查询 Run 的工具调用记录 — MVP 开发验证接口。"""
    data = runs.list_tool_calls_by_run(run_id)
    return [ToolCallResponse(**tc) for tc in data]


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

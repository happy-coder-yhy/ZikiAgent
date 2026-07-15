"""FastAPI server — exposes Ziki Agent via HTTP.

Start:
    python -m ziki_agent.server
    -> http://0.0.0.0:8080

Authentication:
    All endpoints (except /health) require an ``Authorization: Bearer <token>``
    header where <token> is a Zata platform JWT access_token.  The server
    decodes the JWT to extract ``user_id`` for session isolation.

Endpoints:
    POST /chat              — send a message
    GET  /sessions          — list sessions (current user only)
    GET  /sessions/:id      — get session history
    DELETE /sessions/:id    — delete a session
    GET  /health            — health check (no auth)
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Depends
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
from ziki_agent import memory
from ziki_agent.auth import decode_access_token, TokenDecodeError

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Ziki Agent", version="0.3.0")

_agent: Agent | None = None


@app.on_event("startup")
async def startup():
    global _agent
    try:
        _agent = Agent()
        print("[server] Ziki Agent (Hermes) 初始化成功", file=sys.stderr)
    except Exception as e:
        print(f"[server] Agent 初始化失败: {e}", file=sys.stderr)


@app.on_event("shutdown")
async def shutdown():
    if _agent:
        _agent.shutdown()


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
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: str = Field(default="", description="会话 ID，留空则新建")
    message: str = Field(..., min_length=1, description="用户消息")


class ChatResponse(BaseModel):
    session_id: str
    response: str


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    last_message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: CurrentUser):
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    user_id: str = user["user_id"]
    session_id = req.session_id or str(uuid.uuid4())[:8]
    result = await _agent.run(session_id, req.message, user_id=user_id)

    return ChatResponse(session_id=session_id, response=result.response)


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


@app.get("/health")
async def health():
    return {"status": "ok", "agent_ready": _agent is not None}


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

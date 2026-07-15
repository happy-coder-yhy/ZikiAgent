"""FastAPI server — exposes Ziki Agent via HTTP.

Start:
    python -m ziki_agent.server
    -> http://0.0.0.0:8080

Endpoints:
    POST /chat              — send a message
    GET  /sessions          — list sessions
    GET  /sessions/:id      — get session history
    DELETE /sessions/:id    — delete a session
    GET  /health            — health check
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
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

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Ziki Agent", version="0.2.0")

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
async def chat(req: ChatRequest):
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent 未初始化")

    session_id = req.session_id or str(uuid.uuid4())[:8]
    result = await _agent.run(session_id, req.message)

    return ChatResponse(session_id=session_id, response=result.response)


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    return [SessionInfo(**s) for s in memory.list_sessions()]


@app.get("/sessions/{session_id}/history")
async def get_history(session_id: str):
    return {"session_id": session_id, "messages": memory.get_history(session_id)}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    memory.clear_session(session_id)
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

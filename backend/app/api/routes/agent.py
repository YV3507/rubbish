"""Agent API routes: run agent, manage sessions with streaming support."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class RunRequest(BaseModel):
    session_id: str
    prompt: str


class RunResponse(BaseModel):
    session_id: str
    status: str


@router.post("/run", response_model=RunResponse)
async def run_agent(req: Request, body: RunRequest):
    """Start an agent run for the given prompt.

    The client should subscribe to the SSE stream at
    /api/v1/session/{session_id}/stream before calling this endpoint.
    """
    gateway = req.app.state.gateway

    # Auto-create session if not exists
    if body.session_id not in gateway.sessions:
        from app.session.session import Session
        gateway.sessions[body.session_id] = Session(body.session_id)

    # Run agent in background task — events flow via EventBus → SSE
    import asyncio
    asyncio.create_task(gateway.run(body.session_id, body.prompt))

    return RunResponse(session_id=body.session_id, status="started")


@router.post("/stop")
async def stop_agent(req: Request, session_id: str):
    """Stop the running agent for a session."""
    gateway = req.app.state.gateway
    await gateway.stop(session_id)
    return {"status": "stopped"}

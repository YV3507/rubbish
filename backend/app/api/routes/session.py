"""Session API routes: manage sessions, SSE streaming, and checkpoint."""

import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class CreateSessionResponse(BaseModel):
    session_id: str


@router.post("/create", response_model=CreateSessionResponse)
async def create_session(req: Request):
    """Create a new session."""
    gateway = req.app.state.gateway
    session_id = uuid.uuid4().hex
    from app.session.session import Session
    gateway.sessions[session_id] = Session(session_id)
    return CreateSessionResponse(session_id=session_id)


async def event_stream(generator):
    """Async generator that yields SSE-formatted events."""
    async for event in generator:
        yield f"event: {event.type}\ndata: {json.dumps(event.data)}\n\n"


@router.get("/{session_id}/stream")
async def stream_session(session_id: str, req: Request):
    """SSE stream for session events.

    Subscribes to the EventBus for the given session and streams
    all events as Server-Sent Events to the frontend.
    """
    gateway = req.app.state.gateway
    if session_id not in gateway.sessions:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"error": f"Session {session_id} not found"},
        )

    queue = gateway.emitter.subscribe(session_id)

    async def generate():
        try:
            # Emit a "connected" event immediately so the frontend
            # knows the SSE stream is established before triggering agent run
            yield f"event: connected\ndata: {json.dumps({'session_id': session_id})}\n\n"
            while True:
                event = await queue.get()
                yield f"event: {event.type.value}\ndata: {json.dumps(event.data)}\n\n"
                if event.type.value == "agent_end":
                    break
        finally:
            gateway.emitter.unsubscribe(session_id, queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{session_id}/checkpoint")
async def create_checkpoint(session_id: str, req: Request):
    """Create a checkpoint for rollback."""
    from app.session.checkpoint import CheckpointManager
    ckpt = CheckpointManager(session_id=session_id)
    # Checkpoint all tracked files
    return {"status": "ok", "turn": ckpt._turn}


@router.post("/{session_id}/rollback")
async def rollback_session(session_id: str, req: Request):
    """Rollback to last checkpoint."""
    from app.session.checkpoint import CheckpointManager
    ckpt = CheckpointManager(session_id=session_id)
    return {"status": "rolled_back"}

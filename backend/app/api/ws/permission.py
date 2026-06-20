"""WebSocket handler for tool permission confirmation."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/permission/{session_id}")
async def permission_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # Handle tool_allow / tool_deny messages
            action = data.get("action")
            tool_call_id = data.get("id")
            # Forward to agent via emitter
            await websocket.send_json({"status": "ack", "action": action})
    except WebSocketDisconnect:
        pass

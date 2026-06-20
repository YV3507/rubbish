"""Workspace API routes: open, close, switch, list workspaces."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class OpenWorkspaceRequest(BaseModel):
    path: str


class WorkspaceResponse(BaseModel):
    path: str
    name: str
    opened_at: str


def _get_manager(req: Request):
    """Get the workspace manager from app state."""
    return req.app.state.gateway.workspace_manager


@router.get("", response_model=WorkspaceResponse | None)
async def get_current_workspace(req: Request):
    """Get the currently open workspace, or null if none."""
    mgr = _get_manager(req)
    info = mgr.current
    if info is None:
        return None
    return WorkspaceResponse(
        path=info.path,
        name=info.name,
        opened_at=info.opened_at,
    )


@router.put("", response_model=WorkspaceResponse)
async def open_workspace(req: Request, body: OpenWorkspaceRequest):
    """Open a workspace at the given path."""
    mgr = _get_manager(req)
    info = mgr.open(body.path)
    return WorkspaceResponse(
        path=info.path,
        name=info.name,
        opened_at=info.opened_at,
    )


@router.delete("")
async def close_workspace(req: Request):
    """Close the current workspace."""
    mgr = _get_manager(req)
    mgr.close()
    return {"status": "closed"}


@router.get("/recent")
async def list_recent_workspaces(req: Request):
    """List recently opened workspaces."""
    mgr = _get_manager(req)
    recent = mgr.recent
    return [
        WorkspaceResponse(
            path=w.path,
            name=w.name,
            opened_at=w.opened_at,
        )
        for w in recent
    ]


@router.post("/validate")
async def validate_workspace(req: Request, body: OpenWorkspaceRequest):
    """Validate whether a path is a valid workspace directory."""
    mgr = _get_manager(req)
    return mgr.validate(body.path)


@router.post("/switch", response_model=WorkspaceResponse)
async def switch_workspace(req: Request, body: OpenWorkspaceRequest):
    """Switch to another workspace."""
    mgr = _get_manager(req)
    info = mgr.switch_to(body.path)
    return WorkspaceResponse(
        path=info.path,
        name=info.name,
        opened_at=info.opened_at,
    )

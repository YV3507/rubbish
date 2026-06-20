"""Configuration API — exposes all tunable parameters to the frontend."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.config.schema import ConfigSchema
from app.config.store import ConfigStore

router = APIRouter()
store = ConfigStore()


class ConfigUpdateRequest(BaseModel):
    overrides: dict


@router.get("/config", response_model=dict)
async def get_config(req: Request):
    """Return the current (merged) configuration as a flat dict."""
    cfg = getattr(req.app.state, "config", ConfigSchema())
    return cfg.to_dict()


@router.put("/config", response_model=dict)
async def update_config(req: Request, body: ConfigUpdateRequest):
    """Apply configuration overrides and persist them."""
    cfg = store.save(body.overrides)
    req.app.state.config = cfg
    # Propagate config changes to Gateway so LLM provider picks up new API key etc.
    gateway = getattr(req.app.state, "gateway", None)
    if gateway:
        gateway.set_config(cfg)
    return cfg.to_dict()


@router.post("/config/reset", response_model=dict)
async def reset_config(req: Request):
    """Reset configuration to factory defaults."""
    cfg = ConfigSchema()
    store.save(cfg.to_dict())
    req.app.state.config = cfg
    gateway = getattr(req.app.state, "gateway", None)
    if gateway:
        gateway._cfg = None  # fall back to module-level config
    return cfg.to_dict()

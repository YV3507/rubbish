"""Rubbish Backend: FastAPI application entry point."""

import os
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent, session, config as config_routes
from app.api.ws import permission
from app.workspace import routes as workspace_routes
from app.config import config as cfg
from app.config.store import ConfigStore
from app.core.gateway import Gateway


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — load persisted config overrides on top of env vars
    ConfigStore().load(cfg)
    app.state.config = cfg
    app.state.gateway = Gateway()
    yield
    # Shutdown
    await app.state.gateway.shutdown()


app = FastAPI(title="Rubbish", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(session.router, prefix="/api/v1/session", tags=["session"])
app.include_router(config_routes.router, prefix="/api/v1", tags=["config"])
app.include_router(permission.router, prefix="/api/v1/ws", tags=["ws"])
app.include_router(workspace_routes.router, prefix="/api/v1/workspace", tags=["workspace"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/shutdown")
async def shutdown(req: Request):
    """Gracefully shut down the backend server.

    The frontend calls this when the user clicks 'Shut Down'.
    The response is sent back before the process exits.
    """
    # Schedule exit after a short delay so the response can be sent
    import asyncio
    loop = asyncio.get_event_loop()
    # Graceful SIGTERM on Unix; fallback to os._exit on Windows
    if os.name != "nt":
        loop.call_later(0.5, lambda: os.kill(os.getpid(), signal.SIGTERM))
    else:
        loop.call_later(0.5, lambda: os._exit(0))
    return {"status": "shutting_down"}

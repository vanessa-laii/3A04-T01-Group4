"""
Alerts Agent Service — Entry Point
PAC Architecture: Alerts Agent (Presentation-Abstraction-Control)

This service manages the full alert lifecycle for the smart city system:
- Creating and configuring alert rules (thresholds, regions, visibility)
- Sending rules for approval and managing the approval workflow
- Editing and deleting alert rules
- Acknowledging triggered alerts
- Forwarding publicly visible alerts to the City agent

AlertManagement is defined in the UML as an <<Abstract Class>>.
CityAlertManagement is the concrete implementation used by this service.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Opens the shared httpx.AsyncClient on startup and stores it on
    app.state so dependencies.py can retrieve it via
    request.app.state.http_client for every request that needs to
    forward an alert to the City agent.

    Closes the client gracefully on shutdown.
    """
    app.state.http_client = httpx.AsyncClient(timeout=10.0)

    yield

    await app.state.http_client.aclose()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — Alerts Agent Service",
        description=(
            "PAC alerts agent for the Smart City Environmental Monitoring "
            "and Alert System (SCEMAS). Manages alert rule configuration, "
            "approval workflows, acknowledgement, and forwards publicly "
            "visible alerts to the City agent."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/", tags=["Health"])
    async def root():
        return {"service": "alerts-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
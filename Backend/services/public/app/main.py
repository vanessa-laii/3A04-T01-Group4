"""
Public Agent Service — Entry Point
PAC Architecture: Public Agent (Presentation-Abstraction-Control)

This service is the public-facing agent in the smart city system.
It receives approved sensor data and alert notifications from the City
agent and exposes them to unauthenticated external consumers (citizens,
third-party apps) via a REST API.

No authentication is required on read endpoints — this is by design, as
the Public agent only ever holds data that has been explicitly approved
for public visibility by the City / Alerts agents.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.controller import PublicController
from app.dependencies import get_public_controller


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the PublicController singleton on startup and clean up on
    shutdown. The HTTP client used for notifying remote observers is
    opened here and closed gracefully on exit.
    """
    controller: PublicController = await get_public_controller()
    controller.initialise()
    app.state.controller = controller

    yield

    await controller.shutdown()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — Public Agent Service",
        description=(
            "Public-facing PAC agent for the Smart City Environmental "
            "Monitoring and Alert System (SCEMAS). Exposes approved sensor "
            "data and publicly visible alerts to external consumers with no "
            "authentication required."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -----------------------------------------------------------------------
    # CORS — fully open for public consumers; tighten in production if needed
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,   # no credentials on a public API
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    app.include_router(router, prefix="/api/v1")

    # -----------------------------------------------------------------------
    # Root health-check
    # -----------------------------------------------------------------------
    @app.get("/", tags=["Health"])
    async def root():
        return {"service": "public-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
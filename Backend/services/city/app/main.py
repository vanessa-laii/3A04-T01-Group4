"""
City Agent Service — Entry Point
PAC Architecture: City Agent (Presentation-Abstraction-Control)

This service is the top-level controller agent in the smart city system.
It orchestrates the AccountManagement, DataProcessing, AlertManagement,
and PublicController agents, and exposes a REST API via FastAPI.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.controller import CityController
from app.dependencies import get_city_controller


# ---------------------------------------------------------------------------
# Lifespan: runs once on startup and once on shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the CityController singleton on startup and clean up on
    shutdown.  Any database connection pools, background tasks, or
    inter-service HTTP clients should be started / stopped here.
    """
    controller: CityController = get_city_controller()
    controller.initialise()          # wire up sub-agents, seed observer list
    app.state.controller = controller

    yield  # application runs here

    controller.shutdown()            # graceful teardown


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — City Agent Service",
        description=(
            "Top-level PAC controller agent for the Smart City "
            "Environmental Monitoring and Alert System (SCEMAS). "
            "Manages city-level sensor data, dashboards, and "
            "coordinates sub-agents via internal APIs."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -----------------------------------------------------------------------
    # CORS — tighten origins in production via environment variable
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # replace with specific origins in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Routers
    # -----------------------------------------------------------------------
    app.include_router(router, prefix="/api/v1")

    # -----------------------------------------------------------------------
    # Root health-check (no auth required)
    # -----------------------------------------------------------------------
    @app.get("/", tags=["Health"])
    async def root():
        return {"service": "city-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
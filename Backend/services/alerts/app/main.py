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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.controller import CityAlertManagement
from app.dependencies import get_alert_management_controller


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the CityAlertManagement controller on startup and shut it
    down gracefully on exit. The HTTP client used to notify the City agent
    of triggered alerts is opened and closed here.
    """
    controller: CityAlertManagement = get_alert_management_controller()
    await controller.initialise()
    app.state.controller = controller

    yield

    await controller.shutdown()


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

    # -----------------------------------------------------------------------
    # CORS — internal service; restrict origins in production
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
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
        return {"service": "alerts-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
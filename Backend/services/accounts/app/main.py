"""
Accounts Agent Service — Entry Point
PAC Architecture: Accounts Agent (Presentation-Abstraction-Control)

This service handles all account-related operations for the smart city
system, including:
- User authentication (login)
- Account creation and management (create, view, edit)
- Audit logging of all account events via AuditLogData
- Presentation layer feedback via AccountPageDisplay and
  AccountMessagesDisplay (LoginPage, CreateProfilePage, AccountError,
  AccountSuccess)

Internal service — not publicly exposed. Only accessible by the City
agent and other authorised microservices.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.controller import AccountManagementController
from app.dependencies import get_account_management_controller


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the AccountManagementController on startup and shut it
    down on exit. Database connection pools and the HTTP
    client used for City agent callbacks are opened / closed here.
    """
    controller: AccountManagementController = get_account_management_controller()
    await controller.initialise()
    app.state.controller = controller

    yield

    await controller.shutdown()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — Accounts Agent Service",
        description=(
            "Internal PAC accounts agent for the Smart City Environmental "
            "Monitoring and Alert System (SCEMAS). Manages user authentication, "
            "account lifecycle, and audit logging. Not publicly exposed."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -----------------------------------------------------------------------
    # CORS — internal service only; lock down to known service origins
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # restrict to City agent URL in production
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
        return {"service": "accounts-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
"""
Data Processing Agent Service — Entry Point
PAC Architecture: Data Processing Agent (Presentation-Abstraction-Control)

This service is responsible for:
- Receiving raw JSON payloads from external sensors (ExternalSensorData).
- Parsing and validating the raw data into structured SensorData objects.
- Persisting processed SensorData to the SensorDatabase.
- Forwarding processed SensorData to the City agent.

It sits between the physical sensor layer and the City controller agent,
acting as the data ingestion and transformation pipeline for the system.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.controller import DataProcessingController
from app.dependencies import get_data_processing_controller


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise the DataProcessingController on startup and shut it down
    gracefully. The HTTP client (used to forward data to the City agent)
    and any database connection pools are opened / closed here.
    """
    controller: DataProcessingController = get_data_processing_controller()
    await controller.initialise()
    app.state.controller = controller

    yield

    await controller.shutdown()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — Data Processing Agent Service",
        description=(
            "PAC data ingestion and transformation agent for the Smart City "
            "Environmental Monitoring and Alert System (SCEMAS). Receives raw "
            "sensor JSON, validates and structures it into SensorData, stores "
            "it in the SensorDatabase, and forwards it to the City agent."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -----------------------------------------------------------------------
    # CORS — internal service, restrict to known origins in production
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
        return {"service": "data-processing-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
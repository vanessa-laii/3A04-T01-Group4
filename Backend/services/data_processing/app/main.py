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
    Opens the shared httpx.AsyncClient on startup and closes it on
    shutdown. The client is stored on app.state so dependencies.py can
    retrieve it via request.app.state.http_client.
    """
    app.state.http_client = httpx.AsyncClient(timeout=10.0)

    yield

    await app.state.http_client.aclose()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="SCEMAS — Data Processing Agent Service",
        description=(
            "PAC data ingestion and transformation agent. Receives raw "
            "sensor JSON, validates and structures it into SensorData, "
            "stores it in the SensorDatabase (Supabase/PostgreSQL), and "
            "forwards it to the City agent."
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
        return {"service": "data-processing-agent", "status": "running"}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
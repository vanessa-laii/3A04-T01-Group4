"""
City Agent Service — Dependencies
FastAPI dependency injection wiring.

The CityController is created once as a singleton (module-level) and
injected into route handlers via Depends().  Service URLs are read from
environment variables so they can be overridden per environment without
changing code.
"""

from __future__ import annotations

import os

from app.controller import CityController

from app.database import get_db  # re-export so routes can import from one place

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


# ---------------------------------------------------------------------------
# Service URL configuration (from environment / docker-compose env_file)
# ---------------------------------------------------------------------------

def _get_env(key: str, default: str) -> str:
    """Read an env var with a fallback for local development."""
    return os.getenv(key, default)


async def get_account_management_controller(
    session: AsyncSession = Depends(get_db),
) -> CityController:
    return CityController(accounts_service_url=_get_env(
            "ACCOUNTS_SERVICE_URL", "http://localhost:8005"
        ),
        data_processing_service_url=_get_env(
            "DATA_PROCESSING_SERVICE_URL", "http://localhost:8003"
        ),
        alerts_service_url=_get_env(
            "ALERTS_SERVICE_URL", "http://localhost:8004"
        ),
        public_service_url=_get_env(
            "PUBLIC_SERVICE_URL", "http://localhost:8002"
        ),
        session=session,
    )

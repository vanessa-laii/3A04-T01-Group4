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
from functools import lru_cache

from app.controller import CityController


# ---------------------------------------------------------------------------
# Service URL configuration (from environment / docker-compose env_file)
# ---------------------------------------------------------------------------

def _get_env(key: str, default: str) -> str:
    """Read an env var with a fallback for local development."""
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# CityController singleton
# lru_cache ensures the controller is constructed exactly once per process.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_city_controller() -> CityController:
    """
    Construct and return the singleton CityController.

    Expected environment variables (set in .env / docker-compose.yml):
        ACCOUNTS_SERVICE_URL        e.g. http://accounts:8000
        DATA_PROCESSING_SERVICE_URL e.g. http://data_processing:8000
        ALERTS_SERVICE_URL          e.g. http://alerts:8000
        PUBLIC_SERVICE_URL          e.g. http://public:8000
    """
    return CityController(
        accounts_service_url=_get_env(
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
    )
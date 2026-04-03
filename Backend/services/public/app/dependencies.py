"""
Public Agent Service — Dependencies
FastAPI dependency injection wiring.

The PublicController is constructed once as a module-level singleton via
lru_cache and injected into route handlers with Depends().
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.controller import PublicController


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


@lru_cache(maxsize=1)
def get_public_controller() -> PublicController:
    """
    Construct and return the singleton PublicController.

    Expected environment variables (set in .env / docker-compose.yml):
        CITY_SERVICE_URL    e.g. http://city:8000
    """
    return PublicController(
        city_service_url=_get_env("CITY_SERVICE_URL", "http://localhost:8001"),
    )
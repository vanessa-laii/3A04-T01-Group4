"""
Alerts Agent Service — Dependencies
FastAPI dependency injection wiring.

CityAlertManagement is constructed once as a module-level singleton via
lru_cache and injected into route handlers via Depends().
"""

from __future__ import annotations

import os
from functools import lru_cache

from app.controller import CityAlertManagement


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


@lru_cache(maxsize=1)
def get_alert_management_controller() -> CityAlertManagement:
    """
    Construct and return the singleton CityAlertManagement controller.

    Expected environment variables (set in .env / docker-compose.yml):
        CITY_SERVICE_URL    e.g. http://city:8000
    """
    return CityAlertManagement(
        city_service_url=_get_env("CITY_SERVICE_URL", "http://localhost:8001"),
    )
"""
Alerts Agent Service — Dependencies
FastAPI dependency injection wiring.

CityAlertManagement is constructed once as a module-level singleton via
lru_cache and injected into route handlers via Depends().
"""

from __future__ import annotations

import os

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.controller import CityAlertManagement


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


async def get_alert_management_controller(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> CityAlertManagement:
    """
    Per-request factory for CityAlertManagement.

    Retrieves the shared httpx.AsyncClient from app.state (opened once
    in main.py lifespan) so the HTTP connection pool is reused across
    requests rather than recreated per request.
    """
    http_client: httpx.AsyncClient = request.app.state.http_client

    return CityAlertManagement(
        session=session,
        city_service_url=_get_env("CITY_SERVICE_URL", "http://localhost:8001"),
        http_client=http_client,
    )
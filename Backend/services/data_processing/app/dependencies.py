"""
Data Processing Agent Service — Dependencies
FastAPI dependency injection wiring.

The DataProcessingController is constructed once as a module-level
singleton via lru_cache and injected into route handlers via Depends().
"""

from __future__ import annotations

import os

from app.controller import DataProcessingController

from app.database import get_db  # re-export so routes can import from one place

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


async def get_account_management_controller(
    session: AsyncSession = Depends(get_db),
) -> DataProcessingController:
    return DataProcessingController(
        city_service_url=_get_env("CITY_SERVICE_URL", "http://localhost:8001"),
        session=session
    )

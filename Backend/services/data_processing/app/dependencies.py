
from __future__ import annotations

import os

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.controller import DataProcessingController


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


async def get_data_processing_controller(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> DataProcessingController:
    """
    Per-request factory for DataProcessingController.

    FastAPI calls this function for every request that depends on it.
    A fresh DataProcessingController is constructed with:
      - A new AsyncSession scoped to this request (from get_db).
      - The shared httpx.AsyncClient from app.state (set in main.py
        lifespan so the TCP connection pool is reused across requests).

    The controller is lightweight to construct — its only state is the
    session reference and the HTTP client reference.
    """
    http_client: httpx.AsyncClient = request.app.state.http_client

    return DataProcessingController(
        session=session,
        city_service_url=_get_env(
            "CITY_SERVICE_URL", "http://localhost:8001"
        ),
        http_client=http_client,
    )
"""
Accounts Agent Service — Dependencies
FastAPI dependency injection wiring.

The AccountManagementController is constructed once as a module-level
singleton via lru_cache and injected into route handlers via Depends().
"""

from __future__ import annotations

from app.controller import AccountManagementController
from app.database import get_db  # re-export so routes can import from one place

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

async def get_account_management_controller(
    session: AsyncSession = Depends(get_db),
) -> AccountManagementController:
    return AccountManagementController(session)

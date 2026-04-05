"""
Data Processing Agent Service — Database Setup
Async SQLAlchemy engine, session factory, and declarative base.

This module is the single place where the database connection is
configured for the data_processing service. All ORM models in
orm_models.py inherit from the Base defined here, and all route
handlers receive an AsyncSession via the get_db() dependency.
"""

from __future__ import annotations
from typing import AsyncGenerator

import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Engine
# Reads DATABASE_URL from environment (set in .env / docker-compose.yml).
# Uses asyncpg as the async driver:
#   postgresql+asyncpg://user:password@host:port/dbname
#
# pool_size     — number of persistent connections kept open
# max_overflow  — extra connections allowed above pool_size under load
# pool_pre_ping — test connections before use (handles Supabase timeouts)
# echo          — set True temporarily to log all SQL during development
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/postgres",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

# ---------------------------------------------------------------------------
# Session factory
# expire_on_commit=False keeps ORM objects usable after session.commit()
# without issuing extra SELECT queries — important for async code.
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative base — all ORM models in orm_models.py inherit from this
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields one AsyncSession per request
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injected into route handlers via Depends(get_db).
    Opens a session at the start of the request and closes it (and rolls
    back any uncommitted transaction) when the response is sent.

    Usage in dependencies.py:
        async def get_controller(session: AsyncSession = Depends(get_db)):
            return DataProcessingController(session=session, ...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
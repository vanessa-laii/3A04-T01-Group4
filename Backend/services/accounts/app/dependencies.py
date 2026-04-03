"""
Accounts Agent Service — Dependencies
FastAPI dependency injection wiring.

The AccountManagementController is constructed once as a module-level
singleton via lru_cache and injected into route handlers via Depends().
"""

from __future__ import annotations

from functools import lru_cache

from app.controller import AccountManagementController


@lru_cache(maxsize=1)
def get_account_management_controller() -> AccountManagementController:
    """
    Construct and return the singleton AccountManagementController.

    The accounts agent has no outbound HTTP dependencies at initialisation
    time — all inter-service calls are inbound (from the City agent).
    Database connection config should be read from environment variables
    and passed into AccountDatabase / AuditLogData here once a real DB
    driver is wired in.

    Expected environment variables (set in .env / docker-compose.yml):
        DB_HOST         e.g. db
        DB_PORT         e.g. 5432
        DB_NAME         e.g. scemas_accounts
        DB_USER         e.g. scemas
        DB_PASSWORD     e.g. secret
    """
    return AccountManagementController()
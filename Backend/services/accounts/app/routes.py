"""
Accounts Agent Service — Routes
All API endpoints exposed by the Accounts Agent.

Route groups:
  /auth            — login (AccountLogin)
  /accounts        — create, view, edit accounts (CRUD lifecycle)
  /audit           — audit log queries (AuditLogView: displayMessage / updatePage)
"""

from __future__ import annotations

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controller import AccountManagementController
from app.dependencies import get_account_management_controller
from app.models import (
    AuditLogEntryResponse,
    AuditLogPageResponse,
    CreateAccountRequest,
    CreateAccountResponse,
    EditAccountRequest,
    EditAccountResponse,
    LoginRequest,
    LoginResponse,
    ViewAccountResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Authentication — AccountLogin
# UML: login(userId, password): boolean
# ---------------------------------------------------------------------------

@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Login to the system",
    description=(
        "Validates credentials against AccountDatabase. On success, sets the "
        "active session in the abstraction layer and returns the user's role. "
        "The response includes a PageDisplaySchema indicating which "
        "presentation layer page should be shown (LoginPage on failure, "
        "account page on success)."
    ),
)
async def login(
    request: LoginRequest,
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> LoginResponse:
    return await controller.login(request)


# ---------------------------------------------------------------------------
# Account creation — CreateAccount
# UML: createAccount(userId, password, email, phone-num, role): boolean
# ---------------------------------------------------------------------------

@router.post(
    "/accounts",
    response_model=CreateAccountResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Accounts"],
    summary="Create a new user account",
    description=(
        "Creates a new account in AccountDatabase and records a CREATE_ACCOUNT "
        "audit event. Returns a CreateProfilePage presentation response on "
        "success or an AccountError response on failure."
    ),
)
async def create_account(
    request: CreateAccountRequest,
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> CreateAccountResponse:
    return await controller.create_account(request)


# ---------------------------------------------------------------------------
# View account — ViewAccount
# UML: viewAccount(): void
# ---------------------------------------------------------------------------

@router.get(
    "/accounts/{user_id}",
    response_model=ViewAccountResponse,
    status_code=status.HTTP_200_OK,
    tags=["Accounts"],
    summary="View an account",
    description=(
        "Retrieves AccountInfo from AccountDatabase for the given userId and "
        "records a VIEW_ACCOUNT audit event. Returns an AccountPageDisplay "
        "presentation response."
    ),
)
async def view_account(
    user_id: str,
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> ViewAccountResponse:
    try:
        return await controller.view_account(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Edit account — EditAccount
# UML: editAccount(password, email, phone-num): boolean
# ---------------------------------------------------------------------------

@router.patch(
    "/accounts/{user_id}",
    response_model=EditAccountResponse,
    status_code=status.HTTP_200_OK,
    tags=["Accounts"],
    summary="Edit an existing account",
    description=(
        "Partially updates an account in AccountDatabase (password, email, "
        "and/or phone number). Only supplied fields are modified. Records an "
        "EDIT_ACCOUNT audit event and returns an AccountSuccess or "
        "AccountError presentation response."
    ),
)
async def edit_account(
    user_id: str,
    request: EditAccountRequest,
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> EditAccountResponse:
    return await controller.edit_account(user_id, request)


# ---------------------------------------------------------------------------
# Audit Log — AuditLogView
# UML: displayMessage(): void  →  /audit/display
#      updatePage(): void      →  /audit  (paginated)
# ---------------------------------------------------------------------------

@router.get(
    "/audit",
    response_model=AuditLogPageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Audit Log"],
    summary="Get paginated audit log (AuditLogView.updatePage)",
    description=(
        "Returns a paginated view of audit events from AuditLogData. "
        "Optionally filter by userId. Maps to AuditLogView.updatePage()."
    ),
)
async def get_audit_log(
    user_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter audit events by userId.",
        example="user-001",
    ),
    page: int = Query(1, ge=1, description="Page number."),
    page_size: int = Query(20, ge=1, le=100, description="Results per page."),
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> AuditLogPageResponse:
    return await controller.get_audit_log(
        user_id=user_id, page=page, page_size=page_size
    )


@router.get(
    "/audit/display",
    response_model=list[AuditLogEntryResponse],
    status_code=status.HTTP_200_OK,
    tags=["Audit Log"],
    summary="Display recent audit messages (AuditLogView.displayMessage)",
    description=(
        "Returns the most recent audit events from the in-memory abstraction "
        "buffer — fast, no DB query. Maps to AuditLogView.displayMessage(). "
        "Optionally filter by userId."
    ),
)
async def display_audit_messages(
    user_id: Optional[uuid.UUID] = Query(None, example="user-001"),
    limit: int = Query(20, ge=1, le=50),
    controller: AccountManagementController = Depends(
        get_account_management_controller
    ),
) -> list[AuditLogEntryResponse]:
    return await controller.get_audit_event_display(user_id=user_id, limit=limit)
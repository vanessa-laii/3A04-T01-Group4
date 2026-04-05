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

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.controller import AccountManagementController, _get_supabase
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
# JWT verification dependency
# Validates the Supabase JWT sent by the frontend in the Authorization header.
# Returns the authenticated user's UUID.
# ---------------------------------------------------------------------------

def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = authorization[7:]
    try:
        sb = _get_supabase()
        result = sb.auth.get_user(token)
        if result.user is None:
            raise HTTPException(status_code=401, detail="Invalid token.")
        return result.user.id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {exc}")


# ---------------------------------------------------------------------------
# Authentication — AccountLogin
# UML: login(email, password): boolean
# ---------------------------------------------------------------------------

@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
    summary="Login to the system",
)
async def login(
    request: LoginRequest,
    controller: AccountManagementController = Depends(get_account_management_controller),
) -> LoginResponse:
    return await controller.login(request)


# ---------------------------------------------------------------------------
# Account creation — CreateAccount
# UML: createAccount(username, password, email, phone-num, role): boolean
# Protected: caller must be authenticated (any role can be verified, but
# admin-only enforcement should be added in production).
# ---------------------------------------------------------------------------

@router.post(
    "/accounts",
    response_model=CreateAccountResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Accounts"],
    summary="Create a new user account",
)
async def create_account(
    request: CreateAccountRequest,
    controller: AccountManagementController = Depends(get_account_management_controller),
    _caller_id: str = Depends(get_current_user_id),
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
)
async def view_account(
    user_id: str,
    controller: AccountManagementController = Depends(get_account_management_controller),
    _caller_id: str = Depends(get_current_user_id),
) -> ViewAccountResponse:
    try:
        return await controller.view_account(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ---------------------------------------------------------------------------
# Edit account — EditAccount
# UML: editAccount(username, phone-num, role, is_active): boolean
# ---------------------------------------------------------------------------

@router.patch(
    "/accounts/{user_id}",
    response_model=EditAccountResponse,
    status_code=status.HTTP_200_OK,
    tags=["Accounts"],
    summary="Edit an existing account",
)
async def edit_account(
    user_id: str,
    request: EditAccountRequest,
    controller: AccountManagementController = Depends(get_account_management_controller),
    _caller_id: str = Depends(get_current_user_id),
) -> EditAccountResponse:
    return await controller.edit_account(user_id, request)


# ---------------------------------------------------------------------------
# Audit Log — AuditLogView
# ---------------------------------------------------------------------------

@router.get(
    "/audit",
    response_model=AuditLogPageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Audit Log"],
    summary="Get paginated audit log (AuditLogView.updatePage)",
)
async def get_audit_log(
    user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    controller: AccountManagementController = Depends(get_account_management_controller),
    _caller_id: str = Depends(get_current_user_id),
) -> AuditLogPageResponse:
    return controller.get_audit_log(user_id=user_id, page=page, page_size=page_size)


@router.get(
    "/audit/display",
    response_model=list[AuditLogEntryResponse],
    status_code=status.HTTP_200_OK,
    tags=["Audit Log"],
    summary="Display recent audit messages (AuditLogView.displayMessage)",
)
async def display_audit_messages(
    user_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    controller: AccountManagementController = Depends(get_account_management_controller),
    _caller_id: str = Depends(get_current_user_id),
) -> list[AuditLogEntryResponse]:
    return controller.get_audit_event_display(user_id=user_id, limit=limit)

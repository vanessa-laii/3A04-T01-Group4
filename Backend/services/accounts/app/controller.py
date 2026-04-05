"""
Accounts Agent Service — AccountManagementController
PAC Architecture: Control layer of the Accounts Agent.

Implements the four core UML operations of AccountManagement:
  login(email, password)                               -> boolean
  createAccount(username, password, email, phone, role) -> boolean
  viewAccount(user_id)                                 -> void
  editAccount(username, phone, role, is_active)        -> boolean

AccountDatabase and AuditLogData are now backed by Supabase.
"""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from app.abstraction import AccountsAbstraction
from app.models import (
    AccountDatabaseUpdateRequest,
    AccountInfoResponse,
    AccountInfoSchema,
    AuditEventType,
    AuditInformationSchema,
    AuditLogEntryResponse,
    AuditLogPageResponse,
    CreateAccountRequest,
    CreateAccountResponse,
    EditAccountRequest,
    EditAccountResponse,
    LoginRequest,
    LoginResponse,
    PageDisplaySchema,
    UserRole,
    ViewAccountResponse,
    SuccessResponse,
)

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Supabase client — singleton with service role key
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# AccountDatabase
# Persistence layer backed by Supabase account_information table.
# ---------------------------------------------------------------------------

class AccountDatabase:
    """
    UML: AccountDatabase
      - accountInfo: AccountInfo
      - userId: String
      + retrieveAccountInfo(): AccountInfo
      + updateAccountInfo(): boolean
    """

    def __init__(self):
        self._sb = _get_supabase()

    def retrieve_account_info(self, user_id: str) -> Optional[AccountInfoSchema]:
        result = (
            self._sb.table("account_information")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            return None
        row = result.data[0]
        return AccountInfoSchema(
            accountinfo_id=row["accountinfo_id"],
            user_id=row["user_id"],
            username=row["username"],
            email=row["email"],
            phone_number=row.get("phone_number"),
            role=UserRole(row["role"]),
            is_active=row["is_active"],
        )

    def update_account_info(self, request: AccountDatabaseUpdateRequest) -> bool:
        updates: dict = {}
        if request.username     is not None: updates["username"]     = request.username
        if request.phone_number is not None: updates["phone_number"] = request.phone_number or None
        if request.role         is not None: updates["role"]         = request.role.value
        if request.is_active    is not None: updates["is_active"]    = request.is_active
        if not updates:
            return True
        updates["updated_at"] = _iso_now()
        self._sb.table("account_information").update(updates).eq("user_id", request.userId).execute()
        logger.info("AccountInfo updated for user_id='%s'.", request.userId)
        return True

    def create_record(self, request: CreateAccountRequest) -> str:
        """Create Supabase Auth user + account_information row. Returns new user UUID."""
        auth_result = self._sb.auth.admin.create_user({
            "email": request.email,
            "password": request.password,
            "email_confirm": True,
        })
        user_id = auth_result.user.id

        self._sb.table("account_information").insert({
            "user_id":       user_id,
            "username":      request.username,
            "email":         request.email,
            "phone_number":  request.phone_number or None,
            "role":          request.role.value,
            "is_active":     True,
            "password_hash": "managed_by_supabase_auth",
        }).execute()

        logger.info("Account created: user_id='%s' email='%s'.", user_id, request.email)
        return user_id

    def email_exists(self, email: str) -> bool:
        result = (
            self._sb.table("account_information")
            .select("accountinfo_id")
            .eq("email", email)
            .execute()
        )
        return len(result.data) > 0

    def verify_via_supabase(self, email: str, password: str):
        """
        Attempt Supabase Auth sign-in. Returns (access_token, user_id) on
        success, raises an exception on failure.
        """
        result = self._sb.auth.sign_in_with_password({"email": email, "password": password})
        return result.session.access_token, result.user.id


# ---------------------------------------------------------------------------
# AuditLogData
# In-memory for now — TODO: persist to Supabase audit_log table.
# ---------------------------------------------------------------------------

class AuditLogData:
    """
    UML: AuditLogData
      - auditInfo: AuditInformation
      + getAuditInformation(): AuditInformation
      + updateAuditInformation(Info): void
    """

    def __init__(self):
        self._log: List[AuditInformationSchema] = []

    def get_audit_information(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditInformationSchema]:
        events = self._log
        if user_id:
            events = [e for e in events if e.userId == user_id]
        return events[-limit:]

    def update_audit_information(self, info: AuditInformationSchema) -> None:
        self._log.append(info)
        logger.info("Audit: userId=%s type=%s", info.userId, info.EventType)


# ---------------------------------------------------------------------------
# Operation classes
# ---------------------------------------------------------------------------

class AccountLogin:
    """UML: AccountLogin — login(email, password): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db    = db
        self._audit = audit

    def login(self, email: str, password: str):
        """Returns (success, access_token, user_id)."""
        try:
            access_token, user_id = self._db.verify_via_supabase(email, password)
            self._audit.update_audit_information(AuditInformationSchema(
                userId=user_id,
                EventType=AuditEventType.LOGIN,
                EventDesc="User logged in successfully.",
                EventDate=_now(),
            ))
            return True, access_token, user_id
        except Exception as exc:
            logger.warning("Login failed for email='%s': %s", email, exc)
            self._audit.update_audit_information(AuditInformationSchema(
                userId=email,
                EventType=AuditEventType.LOGIN_FAILED,
                EventDesc="Login attempt failed — invalid credentials.",
                EventDate=_now(),
            ))
            return False, None, None


class CreateAccount:
    """UML: CreateAccount — createAccount(...): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db    = db
        self._audit = audit

    def create_account(self, request: CreateAccountRequest) -> Optional[str]:
        """Returns new user_id on success, None on failure."""
        if self._db.email_exists(request.email):
            logger.warning("createAccount: email='%s' already exists.", request.email)
            return None
        try:
            user_id = self._db.create_record(request)
            self._audit.update_audit_information(AuditInformationSchema(
                userId=user_id,
                EventType=AuditEventType.CREATE_ACCOUNT,
                EventDesc=f"Account created with role '{request.role.value}'.",
                EventDate=_now(),
            ))
            return user_id
        except Exception as exc:
            logger.error("createAccount failed: %s", exc)
            return None


class ViewAccount:
    """UML: ViewAccount — viewAccount(): void"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db    = db
        self._audit = audit

    def view_account(self, user_id: str) -> Optional[AccountInfoSchema]:
        info = self._db.retrieve_account_info(user_id)
        if info:
            self._audit.update_audit_information(AuditInformationSchema(
                userId=user_id,
                EventType=AuditEventType.VIEW_ACCOUNT,
                EventDesc="Account details viewed.",
                EventDate=_now(),
            ))
        return info


class EditAccount:
    """UML: EditAccount — editAccount(username, phone, role, is_active): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db    = db
        self._audit = audit

    def edit_account(self, user_id: str, request: EditAccountRequest) -> bool:
        update = AccountDatabaseUpdateRequest(
            userId=user_id,
            username=request.username,
            phone_number=request.phone_number,
            role=request.role,
            is_active=request.is_active,
        )
        success = self._db.update_account_info(update)
        if success:
            changed = [f for f in ("username", "phone_number", "role", "is_active")
                       if getattr(request, f) is not None]
            self._audit.update_audit_information(AuditInformationSchema(
                userId=user_id,
                EventType=AuditEventType.EDIT_ACCOUNT,
                EventDesc=f"Account fields updated: {', '.join(changed)}.",
                EventDate=_now(),
            ))
        return success


# ---------------------------------------------------------------------------
# AccountManagementController — Control layer
# ---------------------------------------------------------------------------

class AccountManagementController:
    def __init__(self):
        self._account_db     = AccountDatabase()
        self._audit_log      = AuditLogData()
        self._account_login  = AccountLogin(self._account_db, self._audit_log)
        self._account_create = CreateAccount(self._account_db, self._audit_log)
        self._account_view   = ViewAccount(self._account_db, self._audit_log)
        self._account_edit   = EditAccount(self._account_db, self._audit_log)
        self._abstraction    = AccountsAbstraction()

    async def initialise(self) -> None:
        logger.info("AccountManagementController initialised (Supabase backend).")

    async def shutdown(self) -> None:
        logger.info("AccountManagementController shut down.")

    # -----------------------------------------------------------------------
    # UML: login(email, password): boolean
    # -----------------------------------------------------------------------

    async def login(self, request: LoginRequest) -> LoginResponse:
        success, access_token, user_id = self._account_login.login(request.email, request.password)

        if success:
            info = self._account_db.retrieve_account_info(user_id)
            if info and not info.is_active:
                page = self._abstraction.build_error_page("login_page", "Account is deactivated.")
                return LoginResponse(success=False, message="Account is deactivated.", page=page)

            role = info.role if info else UserRole.PUBLIC_USER
            self._abstraction.set_active_session(user_id, role)
            page = self._abstraction.build_success_page("login_page", "Login successful.")
            return LoginResponse(
                success=True,
                user_id=user_id,
                access_token=access_token,
                role=role,
                message="Login successful.",
                page=page,
            )

        page = self._abstraction.build_error_page("login_page", "Invalid email or password.")
        return LoginResponse(success=False, message="Invalid email or password.", page=page)

    # -----------------------------------------------------------------------
    # UML: createAccount(...)
    # -----------------------------------------------------------------------

    async def create_account(self, request: CreateAccountRequest) -> CreateAccountResponse:
        user_id = self._account_create.create_account(request)

        if user_id:
            page = self._abstraction.build_success_page(
                "create_profile_page", f"Account '{request.username}' created successfully."
            )
            return CreateAccountResponse(success=True, user_id=user_id,
                                         message="Account created successfully.", page=page)

        page = self._abstraction.build_error_page(
            "create_profile_page",
            f"Could not create account — email '{request.email}' may already exist.",
        )
        return CreateAccountResponse(
            success=False,
            message=f"Account creation failed for email '{request.email}'.",
            page=page,
        )

    # -----------------------------------------------------------------------
    # UML: viewAccount()
    # -----------------------------------------------------------------------

    async def view_account(self, user_id: str) -> ViewAccountResponse:
        info = self._account_view.view_account(user_id)
        if info is None:
            raise ValueError(f"Account '{user_id}' not found.")

        account_response = AccountInfoResponse(**info.model_dump())
        self._abstraction.set_current_account(account_response)
        page = self._abstraction.build_info_page("account_page", f"Viewing account '{user_id}'.")
        return ViewAccountResponse(account_info=account_response, page=page)

    # -----------------------------------------------------------------------
    # UML: editAccount(...)
    # -----------------------------------------------------------------------

    async def edit_account(self, user_id: str, request: EditAccountRequest) -> EditAccountResponse:
        success = self._account_edit.edit_account(user_id, request)

        if success:
            page = self._abstraction.build_success_page("account_success", "Account updated successfully.")
            return EditAccountResponse(success=True, message="Account updated successfully.", page=page)

        page = self._abstraction.build_error_page(
            "account_error", f"Could not update account '{user_id}'."
        )
        return EditAccountResponse(
            success=False, message=f"Account update failed for user_id '{user_id}'.", page=page
        )

    # -----------------------------------------------------------------------
    # Audit log accessors
    # -----------------------------------------------------------------------

    def get_audit_log(
        self, user_id: Optional[str] = None, page: int = 1, page_size: int = 20
    ) -> AuditLogPageResponse:
        all_events = self._audit_log.get_audit_information(user_id=user_id, limit=page_size * page)
        start = (page - 1) * page_size
        entries = [
            AuditLogEntryResponse(
                userId=e.userId, EventType=e.EventType,
                EventDesc=e.EventDesc, EventDate=e.EventDate,
            )
            for e in all_events[start: start + page_size]
        ]
        return AuditLogPageResponse(entries=entries, total=len(all_events), page=page, page_size=page_size)

    def get_audit_event_display(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[AuditLogEntryResponse]:
        return self._abstraction.get_audit_events(limit=limit, user_id=user_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> int:
    return int(time.time())

def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

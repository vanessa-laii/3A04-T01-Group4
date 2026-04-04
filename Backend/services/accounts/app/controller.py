"""
Accounts Agent Service — AccountManagementController
PAC Architecture: Control layer of the Accounts Agent.

Implements the four core UML operations of AccountManagement:
  login(userId, password)                            -> boolean
  createAccount(userId, password, email, phone, role) -> boolean
  viewAccount()                                      -> void
  editAccount(password, email, phone-num)            -> boolean

Also contains the concrete implementations of UML classes that are
owned by / composed into AccountManagement:
  AccountLogin      — encapsulates login logic
  CreateAccount     — encapsulates account creation logic
  ViewAccount       — encapsulates account retrieval logic
  EditAccount       — encapsulates account update logic
  AccountDatabase   — persistence layer (composes AccountInfo)
  AuditLogData      — audit event persistence (composes AuditInformation)

Presentation layer classes (LoginPage, CreateProfilePage, AccountError,
AccountSuccess) are represented via PageDisplaySchema and produced by the
AccountsAbstraction layer — the controller never constructs them directly.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.orm_models import AccountInfoORM, AuditLogORM

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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AccountDatabase
# Persistence layer — composes AccountInfo (UML composition arrow).
# Replace the in-memory dict with async DB calls (SQLAlchemy, asyncpg).
# ---------------------------------------------------------------------------

class AccountDatabase:
    def __init__(self, session: AsyncSession):
        self._session = session          # injected, not created here

    async def retrieve_account_info(self, user_id: str):
        result = await self._session.execute(
            select(AccountInfoORM).where(AccountInfoORM.userId == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return AccountInfoSchema(
            userId=row.userId, email=row.email,
            phoneNum=row.phoneNum, role=row.role
        )

    async def update_account_info(self, request):
        result = await self._session.execute(
            select(AccountInfoORM).where(AccountInfoORM.userId == request.userId)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        if request.email:    row.email    = request.email
        if request.phone_num: row.phoneNum = request.phone_num
        if request.password: row.password = _hash_password(request.password)
        await self._session.commit()
        return True

    async def create_record(self, info, hashed_password: str) -> bool:
        self._session.add(AccountInfoORM(
            userId=info.userId, password=hashed_password,
            phoneNum=info.phoneNum, email=info.email, role=info.role
        ))
        await self._session.commit()
        return True

    async def verify_credentials(self, user_id: str, password: str) -> bool:
        result = await self._session.execute(
            select(AccountInfoORM).where(AccountInfoORM.userId == user_id)
        )
        row = result.scalar_one_or_none()
        return row is not None and row.password == _hash_password(password)

# ---------------------------------------------------------------------------
# AuditLogData
# Composes AuditInformation (UML composition).
# ---------------------------------------------------------------------------

class AuditLogData:
    def __init__(self, session: AsyncSession):
        self._session = session

    def update_audit_information(self, info: AuditInformationSchema) -> None:
        # Fire-and-forget append — use asyncio.create_task in production
        self._session.add(AuditLogORM(
            userId=info.userId, EventType=info.EventType.value,
            EventDesc=info.EventDesc, EventDate=info.EventDate
        ))
        # Note: commit happens at end of request via session lifecycle

    async def get_audit_information(self, user_id=None, limit=100):
        q = select(AuditLogORM).order_by(AuditLogORM.EventDate.desc()).limit(limit)
        if user_id:
            q = q.where(AuditLogORM.userId == user_id)
        result = await self._session.execute(q)
        return [
            AuditInformationSchema(
                userId=r.userId, EventType=r.EventType,
                EventDesc=r.EventDesc, EventDate=r.EventDate
            )
            for r in result.scalars()
        ]


# ---------------------------------------------------------------------------
# Operation classes — AccountLogin, CreateAccount, ViewAccount, EditAccount
# Each encapsulates the logic for one UML operation and delegates to
# AccountDatabase and AuditLogData.
# ---------------------------------------------------------------------------

class AccountLogin:
    """UML: AccountLogin — login(userId, password): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db = db
        self._audit = audit

    async def login(self, user_id: str, password: str) -> bool:
        result = await self._db.verify_credentials(user_id, password)
        event_type = AuditEventType.LOGIN if result else AuditEventType.LOGIN_FAILED
        desc = (
            "User logged in successfully."
            if result
            else "Login attempt failed — invalid credentials."
        )
        self._audit.update_audit_information(
            AuditInformationSchema(
                userId=user_id,
                EventType=event_type,
                EventDesc=desc,
                EventDate=_now(),
            )
        )
        return result


class CreateAccount:
    """UML: CreateAccount — createAccount(...): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db = db
        self._audit = audit

    async def create_account(self, request: CreateAccountRequest) -> bool:
        if await self._db.user_exists(request.userId):
            logger.warning(
                "createAccount: userId='%s' already exists.", request.userId
            )
            return False

        info = AccountInfoSchema(
            userId=request.userId,
            email=request.email,
            phoneNum=request.phone_num,
            role=request.role,
        )
        success = await self._db.create_record(
            info, _hash_password(request.password)
        )

        if success:
            self._audit.update_audit_information(
                AuditInformationSchema(
                    userId=request.userId,
                    EventType=AuditEventType.CREATE_ACCOUNT,
                    EventDesc=f"Account created with role '{request.role}'.",
                    EventDate=_now(),
                )
            )
        return success


class ViewAccount:
    """UML: ViewAccount — viewAccount(): void"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db = db
        self._audit = audit

    async def view_account(self, user_id: str) -> Optional[AccountInfoSchema]:
        info = await self._db.retrieve_account_info(user_id)
        if info:
            self._audit.update_audit_information(
                AuditInformationSchema(
                    userId=user_id,
                    EventType=AuditEventType.VIEW_ACCOUNT,
                    EventDesc="Account details viewed.",
                    EventDate=_now(),
                )
            )
        return info


class EditAccount:
    """UML: EditAccount — editAccount(password, email, phone-num): boolean"""

    def __init__(self, db: AccountDatabase, audit: AuditLogData):
        self._db = db
        self._audit = audit

    async def edit_account(
        self, user_id: str, request: EditAccountRequest
    ) -> bool:
        update = AccountDatabaseUpdateRequest(
            userId=user_id,
            password=request.password,
            email=request.email,
            phone_num=request.phone_num,
        )
        success = await self._db.update_account_info(update)

        if success:
            changed = [
                f for f in ("password", "email", "phone_num")
                if getattr(request, f) is not None
            ]
            self._audit.update_audit_information(
                AuditInformationSchema(
                    userId=user_id,
                    EventType=AuditEventType.EDIT_ACCOUNT,
                    EventDesc=f"Account fields updated: {', '.join(changed)}.",
                    EventDate=_now(),
                )
            )
        return success


# ---------------------------------------------------------------------------
# AccountManagementController — Control layer
# ---------------------------------------------------------------------------

class AccountManagementController:
    """
    Control layer of the Accounts PAC Agent.

    Owns and wires together all UML sub-components:
      - accountLogin:   AccountLogin
      - accountCreate:  CreateAccount
      - accountView:    ViewAccount (UML: accountView: AccountLogin — typo in UML,
                        treated as ViewAccount)
      - accountPage:    AccountPageDisplay  (via abstraction layer)
      - accountMessage: AccountMessagesDisplay (via abstraction layer)
      - accountDb:      AccountDatabase
      - accountLog:     AuditLogData
    """

    def __init__(self, session: AsyncSession):
        # Shared persistence components
        self._account_db = AccountDatabase(session)
        self._audit_log = AuditLogData(session)

        self._account_db   = AccountDatabase(session)
        self._audit_log    = AuditLogData(session)
        self._account_login  = AccountLogin(self._account_db, self._audit_log)

        # Operation classes
        self._account_login = AccountLogin(self._account_db, self._audit_log)
        self._account_create = CreateAccount(self._account_db, self._audit_log)
        self._account_view = ViewAccount(self._account_db, self._audit_log)
        self._account_edit = EditAccount(self._account_db, self._audit_log)

        # PAC abstraction layer
        self._abstraction = AccountsAbstraction()

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    async def initialise(self) -> None:
        """
        Called once at startup. Wire up DB connection pools here.
        TODO: initialise async DB engine / session factory.
        """
        logger.info("AccountManagementController initialised.")

    async def shutdown(self) -> None:
        """Called once at shutdown. Close DB connections here."""
        logger.info("AccountManagementController shut down.")

    # -----------------------------------------------------------------------
    # UML: login(userId, password): boolean
    # -----------------------------------------------------------------------

    async def login(self, request: LoginRequest) -> LoginResponse:
        success = await self._account_login.login(request.userId, request.password)

        if success:
            info = await self._account_db.retrieve_account_info(request.userId)
            role = info.role if info else UserRole.PUBLIC
            self._abstraction.set_active_session(request.userId, role)

            page = self._abstraction.build_success_page(
                "login_page", "Login successful."
            )
            return LoginResponse(
                success=True,
                userId=request.userId,
                role=role,
                message="Login successful.",
                page=page,
            )

        page = self._abstraction.build_error_page(
            "login_page", "Invalid userId or password."
        )
        return LoginResponse(
            success=False,
            message="Invalid userId or password.",
            page=page,
        )

    # -----------------------------------------------------------------------
    # UML: createAccount(userId, password, email, phone-num, role): boolean
    # -----------------------------------------------------------------------

    async def create_account(
        self, request: CreateAccountRequest
    ) -> CreateAccountResponse:
        success = await self._account_create.create_account(request)

        if success:
            page = self._abstraction.build_success_page(
                "create_profile_page",
                f"Account '{request.userId}' created successfully.",
            )
            return CreateAccountResponse(
                success=True,
                userId=request.userId,
                message="Account created successfully.",
                page=page,
            )

        page = self._abstraction.build_error_page(
            "create_profile_page",
            f"Could not create account — userId '{request.userId}' may already exist.",
        )
        return CreateAccountResponse(
            success=False,
            message=f"Account creation failed for userId '{request.userId}'.",
            page=page,
        )

    # -----------------------------------------------------------------------
    # UML: viewAccount(): void
    # -----------------------------------------------------------------------

    async def view_account(self, user_id: str) -> ViewAccountResponse:
        info = await self._account_view.view_account(user_id)

        if info is None:
            page = self._abstraction.build_error_page(
                "account_error",
                f"Account '{user_id}' not found.",
            )
            raise ValueError(f"Account '{user_id}' not found.")

        account_response = AccountInfoResponse(**info.model_dump())
        self._abstraction.set_current_account(account_response)

        page = self._abstraction.build_info_page(
            "account_page", f"Viewing account '{user_id}'."
        )
        return ViewAccountResponse(account_info=account_response, page=page)

    # -----------------------------------------------------------------------
    # UML: editAccount(password, email, phone-num): boolean
    # -----------------------------------------------------------------------

    async def edit_account(
        self, user_id: str, request: EditAccountRequest
    ) -> EditAccountResponse:
        success = await self._account_edit.edit_account(user_id, request)

        if success:
            page = self._abstraction.build_success_page(
                "account_success", "Account updated successfully."
            )
            return EditAccountResponse(
                success=True,
                message="Account updated successfully.",
                page=page,
            )

        page = self._abstraction.build_error_page(
            "account_error",
            f"Could not update account '{user_id}' — account may not exist.",
        )
        return EditAccountResponse(
            success=False,
            message=f"Account update failed for userId '{user_id}'.",
            page=page,
        )

    # -----------------------------------------------------------------------
    # AuditLogData / AuditLogView accessors
    # UML: getAuditInformation() / updateAuditInformation()
    # -----------------------------------------------------------------------

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogPageResponse:
        """
        AuditLogView.updatePage() — returns a paginated audit log.
        Combines the durable AuditLogData store with the abstraction buffer.
        """
        all_events = self._audit_log.get_audit_information(
            user_id=user_id, limit=page_size * page
        )
        start = (page - 1) * page_size
        end = start + page_size
        page_events = all_events[start:end]

        entries = [
            AuditLogEntryResponse(
                userId=e.userId,
                EventType=e.EventType,
                EventDesc=e.EventDesc,
                EventDate=e.EventDate,
            )
            for e in page_events
        ]

        return AuditLogPageResponse(
            entries=entries,
            total=len(all_events),
            page=page,
            page_size=page_size,
        )

    def get_audit_event_display(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[AuditLogEntryResponse]:
        """AuditLogView.displayMessage() — returns recent audit events."""
        return self._abstraction.get_audit_events(limit=limit, user_id=user_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """
    Simple SHA-256 hash for boilerplate purposes.
    Replace with bcrypt / argon2 in production:
      pip install bcrypt
      hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    """
    return hashlib.sha256(password.encode()).hexdigest()


def _now() -> int:
    """Return the current Unix timestamp (seconds)."""
    return int(time.time())
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
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
 
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.abstraction import AccountsAbstraction
from app.orm_models import AccountInformation, AuditLogData
from app.models import (
    AccountDatabaseUpdateRequest,
    AccountInfoResponse,
    AccountInfoSchema,
    AuditEventType,
    AuditInformationSchema,
    AuditLogEntryResponse,
    AuditLogPageResponse,
    AuditStatus,
    CreateAccountRequest,
    CreateAccountResponse,
    EditAccountRequest,
    EditAccountResponse,
    LoginRequest,
    LoginResponse,
    UserRole,
    ViewAccountResponse,
    SuccessResponse,
)
 
logger = logging.getLogger(__name__)
 
 
# ---------------------------------------------------------------------------
# AccountDatabase
# ---------------------------------------------------------------------------
 
class AccountDatabase:
    """
    Persistence layer backed by the account_information table.
 
    Column mapping (DB → UML / schema):
      accountinfo_id → primary key (UUID)
      username       → userId equivalent
      password_hash  → hashed password
      phone_number   → phoneNum
      role           → UserRole string
    """
 
    def __init__(self, session: AsyncSession):
        self._session = session
 
    async def retrieve_by_username(
        self, username: str
    ) -> Optional[AccountInformation]:
        """SELECT * FROM account_information WHERE username = :username"""
        result = await self._session.execute(
            select(AccountInformation).where(
                AccountInformation.username == username
            )
        )
        return result.scalar_one_or_none()
 
    async def retrieve_by_id(
        self, accountinfo_id: uuid.UUID
    ) -> Optional[AccountInformation]:
        """SELECT * FROM account_information WHERE accountinfo_id = :id"""
        result = await self._session.execute(
            select(AccountInformation).where(
                AccountInformation.accountinfo_id == accountinfo_id
            )
        )
        return result.scalar_one_or_none()
 
    async def retrieve_account_info(
        self, username: str
    ) -> Optional[AccountInfoSchema]:
        """UML: retrieveAccountInfo() — returns schema object or None."""
        row = await self.retrieve_by_username(username)
        if row is None:
            return None
        return _row_to_schema(row)
 
    async def update_account_info(
        self, request: AccountDatabaseUpdateRequest
    ) -> bool:
        """
        UML: updateAccountInfo() — partial update.
        Snapshots old values for the audit log before applying changes.
        Returns (success, old_values, new_values).
        """
        row = await self.retrieve_by_id(request.accountinfo_id)
        if row is None:
            return False
 
        old_values: Dict[str, Any] = {}
        new_values: Dict[str, Any] = {}
 
        if request.password:
            old_values["password_hash"] = "REDACTED"
            row.password_hash = _hash_password(request.password)
            new_values["password_hash"] = "REDACTED"
        if request.email:
            old_values["email"] = row.email
            row.email = request.email
            new_values["email"] = request.email
        if request.phone_number:
            old_values["phone_number"] = row.phone_number
            row.phone_number = request.phone_number
            new_values["phone_number"] = request.phone_number
 
        row.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        logger.info("AccountInformation updated: accountinfo_id=%s", request.accountinfo_id)
        return True
 
    async def create_record(
        self, request: CreateAccountRequest
    ) -> Optional[AccountInformation]:
        """
        INSERT INTO account_information (...) VALUES (...)
        Returns the created ORM row (with DB-generated accountinfo_id),
        or None if username/email already exists.
        """
        # Check uniqueness manually — DB constraint will also catch it,
        # but this gives a cleaner error message
        existing = await self.retrieve_by_username(request.username)
        if existing:
            return None
 
        row = AccountInformation(
            username=request.username,
            password_hash=_hash_password(request.password),
            email=request.email,
            role=request.role.value,
            phone_number=request.phone_number,
        )
        self._session.add(row)
        await self._session.flush()   # populates accountinfo_id from DB default
        await self._session.commit()
        await self._session.refresh(row)
        logger.info("AccountInformation created: username=%s id=%s", row.username, row.accountinfo_id)
        return row
 
    async def verify_credentials(
        self, username: str, password: str
    ) -> Optional[AccountInformation]:
        """
        Returns the ORM row if credentials are valid, None otherwise.
        Also updates last_login on success.
        """
        row = await self.retrieve_by_username(username)
        if row is None:
            return None
        if row.password_hash != _hash_password(password):
            return None
 
        row.last_login = datetime.now(timezone.utc)
        await self._session.commit()
        return row
 
    async def user_exists(self, username: str) -> bool:
        row = await self.retrieve_by_username(username)
        return row is not None
 
 
# ---------------------------------------------------------------------------
# AuditLogData
# ---------------------------------------------------------------------------
 
class AuditLogDataClass:
    """
    Append-only audit log backed by the audit_log_data table.
 
    The real schema is richer than the UML design:
      - entity_type / entity_id track what was acted on
      - old_values / new_values store JSONB snapshots
      - status tracks success / failure / partial
      - ip_address / user_agent for request context
      - retention_until set automatically by DB (now + 1 year)
    """
 
    def __init__(self, session: AsyncSession):
        self._session = session
 
    async def update_audit_information(
        self, info: AuditInformationSchema
    ) -> None:
        """
        UML: updateAuditInformation(Info): void
        Inserts a new audit_log_data row.
        timestamp and retention_until are set by DB defaults.
        """
        row = AuditLogData(
            event_type=info.event_type.value,
            action_description=info.action_description,
            user_id=info.user_id,
            entity_type=info.entity_type,
            entity_id=info.entity_id,
            old_values=info.old_values,
            new_values=info.new_values,
            status=info.status.value,
            ip_address=info.ip_address,
            user_agent=info.user_agent,
        )
        self._session.add(row)
        await self._session.flush()
        logger.info(
            "Audit event: type=%s user_id=%s status=%s",
            info.event_type.value, info.user_id, info.status.value,
        )
 
    async def get_audit_information(
        self,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> List[AuditLogData]:
        """
        UML: getAuditInformation(): AuditInformation
        SELECT ... ORDER BY timestamp DESC LIMIT :limit
        """
        q = (
            select(AuditLogData)
            .order_by(AuditLogData.timestamp.desc())
            .limit(limit)
        )
        if user_id:
            q = q.where(AuditLogData.user_id == user_id)
        result = await self._session.execute(q)
        return list(result.scalars().all())
 
 
# ---------------------------------------------------------------------------
# Operation classes — thin delegation layer (unchanged structure)
# ---------------------------------------------------------------------------
 
class AccountLogin:
    def __init__(self, db: AccountDatabase, audit: AuditLogDataClass):
        self._db    = db
        self._audit = audit
 
    async def login(
        self, username: str, password: str
    ) -> Optional[AccountInformation]:
        row = await self._db.verify_credentials(username, password)
        success = row is not None
 
        await self._audit.update_audit_information(
            AuditInformationSchema(
                event_type=AuditEventType.USER_LOGIN if success else AuditEventType.USER_LOGIN,
                action_description=(
                    "User logged in successfully."
                    if success
                    else "Login attempt failed — invalid credentials."
                ),
                user_id=row.accountinfo_id if row else None,
                entity_type="account",
                entity_id=username,
                status=AuditStatus.SUCCESS if success else AuditStatus.FAILURE,
            )
        )
        return row
 
 
class CreateAccount:
    def __init__(self, db: AccountDatabase, audit: AuditLogDataClass):
        self._db    = db
        self._audit = audit
 
    async def create_account(
        self, request: CreateAccountRequest
    ) -> Optional[AccountInformation]:
        row = await self._db.create_record(request)
        if row:
            await self._audit.update_audit_information(
                AuditInformationSchema(
                    event_type=AuditEventType.USER_CREATED,
                    action_description=f"Account created with role '{request.role.value}'.",
                    user_id=row.accountinfo_id,
                    entity_type="account",
                    entity_id=str(row.accountinfo_id),
                    new_values={
                        "username": row.username,
                        "email": row.email,
                        "role": row.role,
                    },
                    status=AuditStatus.SUCCESS,
                )
            )
        return row
 
 
class ViewAccount:
    def __init__(self, db: AccountDatabase, audit: AuditLogDataClass):
        self._db    = db
        self._audit = audit
 
    async def view_account(
        self, username: str
    ) -> Optional[AccountInformation]:
        row = await self._db.retrieve_by_username(username)
        if row:
            await self._audit.update_audit_information(
                AuditInformationSchema(
                    event_type=AuditEventType.DATA_ACCESS,
                    action_description="Account details viewed.",
                    user_id=row.accountinfo_id,
                    entity_type="account",
                    entity_id=str(row.accountinfo_id),
                    status=AuditStatus.SUCCESS,
                )
            )
        return row
 
 
class EditAccount:
    def __init__(self, db: AccountDatabase, audit: AuditLogDataClass):
        self._db    = db
        self._audit = audit
 
    async def edit_account(
        self,
        accountinfo_id: uuid.UUID,
        request: EditAccountRequest,
        actor_id: Optional[uuid.UUID] = None,
    ) -> bool:
        # Capture old values before update for audit log
        row = await self._db.retrieve_by_id(accountinfo_id)
        if row is None:
            return False
 
        old_snap: Dict[str, Any] = {}
        new_snap: Dict[str, Any] = {}
        if request.email:
            old_snap["email"] = row.email
            new_snap["email"] = request.email
        if request.phone_number:
            old_snap["phone_number"] = row.phone_number
            new_snap["phone_number"] = request.phone_number
        if request.password:
            old_snap["password_hash"] = "REDACTED"
            new_snap["password_hash"] = "REDACTED"
 
        db_request = AccountDatabaseUpdateRequest(
            accountinfo_id=accountinfo_id,
            password=request.password,
            email=request.email,
            phone_number=request.phone_number,
        )
        success = await self._db.update_account_info(db_request)
 
        if success:
            await self._audit.update_audit_information(
                AuditInformationSchema(
                    event_type=AuditEventType.USER_MODIFIED,
                    action_description=f"Account fields updated: {', '.join(new_snap.keys())}.",
                    user_id=actor_id or accountinfo_id,
                    entity_type="account",
                    entity_id=str(accountinfo_id),
                    old_values=old_snap,
                    new_values=new_snap,
                    status=AuditStatus.SUCCESS,
                )
            )
        return success
 
 
# ---------------------------------------------------------------------------
# AccountManagementController
# ---------------------------------------------------------------------------
 
class AccountManagementController:
    """
    Control layer of the Accounts PAC Agent.
    Accepts an AsyncSession and wires all sub-components together.
    """
 
    def __init__(self, session: AsyncSession):
        self._account_db    = AccountDatabase(session)
        self._audit_log     = AuditLogDataClass(session)
        self._account_login  = AccountLogin(self._account_db, self._audit_log)
        self._account_create = CreateAccount(self._account_db, self._audit_log)
        self._account_view   = ViewAccount(self._account_db, self._audit_log)
        self._account_edit   = EditAccount(self._account_db, self._audit_log)
        self._abstraction    = AccountsAbstraction()
 
    # -----------------------------------------------------------------------
    # UML: login(userId, password): boolean
    # -----------------------------------------------------------------------
 
    async def login(self, request: LoginRequest) -> LoginResponse:
        row = await self._account_login.login(request.username, request.password)
 
        if row:
            role = UserRole(row.role)
            self._abstraction.set_active_session(row.accountinfo_id, role)
            page = self._abstraction.build_success_page("login_page", "Login successful.")
            return LoginResponse(
                success=True,
                accountinfo_id=row.accountinfo_id,
                username=row.username,
                role=role,
                message="Login successful.",
                page=page,
            )
 
        page = self._abstraction.build_error_page("login_page", "Invalid username or password.")
        return LoginResponse(
            success=False,
            message="Invalid username or password.",
            page=page,
        )
 
    # -----------------------------------------------------------------------
    # UML: createAccount(userId, password, email, phone-num, role): boolean
    # -----------------------------------------------------------------------
 
    async def create_account(
        self, request: CreateAccountRequest
    ) -> CreateAccountResponse:
        row = await self._account_create.create_account(request)
 
        if row:
            page = self._abstraction.build_success_page(
                "create_profile_page",
                f"Account '{request.username}' created successfully.",
            )
            return CreateAccountResponse(
                success=True,
                accountinfo_id=row.accountinfo_id,
                username=row.username,
                message="Account created successfully.",
                page=page,
            )
 
        page = self._abstraction.build_error_page(
            "create_profile_page",
            f"Username '{request.username}' or email is already in use.",
        )
        return CreateAccountResponse(
            success=False,
            message=f"Account creation failed for username '{request.username}'.",
            page=page,
        )
 
    # -----------------------------------------------------------------------
    # UML: viewAccount(): void
    # -----------------------------------------------------------------------
 
    async def view_account(self, username: str) -> ViewAccountResponse:
        row = await self._account_view.view_account(username)
        if row is None:
            raise ValueError(f"Account '{username}' not found.")
 
        account_response = _row_to_response(row)
        self._abstraction.set_current_account(account_response)
        page = self._abstraction.build_info_page("account_page", f"Viewing account '{username}'.")
        return ViewAccountResponse(account_info=account_response, page=page)
 
    # -----------------------------------------------------------------------
    # UML: editAccount(password, email, phone-num): boolean
    # -----------------------------------------------------------------------
 
    async def edit_account(
        self, username: str, request: EditAccountRequest
    ) -> EditAccountResponse:
        row = await self._account_db.retrieve_by_username(username)
        if row is None:
            page = self._abstraction.build_error_page("account_error", f"Account '{username}' not found.")
            return EditAccountResponse(success=False, message=f"Account '{username}' not found.", page=page)
 
        success = await self._account_edit.edit_account(
            accountinfo_id=row.accountinfo_id,
            request=request,
            actor_id=row.accountinfo_id,
        )
 
        if success:
            page = self._abstraction.build_success_page("account_success", "Account updated successfully.")
            return EditAccountResponse(success=True, message="Account updated successfully.", page=page)
 
        page = self._abstraction.build_error_page("account_error", "Account update failed.")
        return EditAccountResponse(success=False, message="Account update failed.", page=page)
 
    # -----------------------------------------------------------------------
    # AuditLogView
    # -----------------------------------------------------------------------
 
    async def get_audit_log(
        self,
        user_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AuditLogPageResponse:
        all_rows = await self._audit_log.get_audit_information(
            user_id=user_id, limit=page_size * page
        )
        start   = (page - 1) * page_size
        end     = start + page_size
        entries = [_audit_row_to_response(r) for r in all_rows[start:end]]
        return AuditLogPageResponse(
            entries=entries, total=len(all_rows), page=page, page_size=page_size
        )
 
    async def get_audit_event_display(
        self,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 20,
    ) -> List[AuditLogEntryResponse]:
        rows = await self._audit_log.get_audit_information(user_id=user_id, limit=limit)
        return [_audit_row_to_response(r) for r in rows]
    
    async def initialise(self) -> None:
        """
        Prepare the controller for operation. 
        This is called during the FastAPI lifespan startup.
        """
        # If AccountDatabase or AuditLogDataClass need to 
        # warm up a connection pool or check DB health, do it here.
        # Example: await self._account_db.verify_connection()
        pass

    async def shutdown(self) -> None:
        """
        Gracefully shut down sub-components.
        This is called during the FastAPI lifespan shutdown.
        """
        # Clear the in-memory abstraction cache on shutdown
        self._abstraction.clear_session()
        
        # If you added an HTTP client or a specific worker to 
        # any sub-component, close it here.
        # Example: await self._audit_log.close_session()
        pass
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _hash_password(password: str) -> str:
    """
    SHA-256 placeholder. Replace with bcrypt/argon2 in production:
      pip install bcrypt
      bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    """
    return hashlib.sha256(password.encode()).hexdigest()
 
 
def _row_to_schema(row: AccountInformation) -> AccountInfoSchema:
    return AccountInfoSchema(
        accountinfo_id=row.accountinfo_id,
        username=row.username,
        email=row.email,
        role=UserRole(row.role),
        phone_number=row.phone_number,
        is_active=row.is_active or True,
        created_at=row.created_at,
        updated_at=row.updated_at,
        last_login=row.last_login,
        user_id=row.user_id,
    )
 
 
def _row_to_response(row: AccountInformation) -> AccountInfoResponse:
    return AccountInfoResponse(
        accountinfo_id=row.accountinfo_id,
        username=row.username,
        email=row.email,
        role=UserRole(row.role),
        phone_number=row.phone_number,
        is_active=row.is_active or True,
        created_at=row.created_at,
        last_login=row.last_login,
    )
 
 
def _audit_row_to_response(row: AuditLogData) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        log_id=row.log_id,
        event_type=AuditEventType(row.event_type),
        action_description=row.action_description,
        user_id=row.user_id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        status=AuditStatus(row.status or "success"),
        ip_address=row.ip_address,
        timestamp=row.timestamp,
    )
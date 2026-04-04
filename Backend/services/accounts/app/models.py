"""
Accounts Agent Service — Pydantic Models
Defines request bodies, response schemas, and internal data-transfer
objects for the full account management and audit logging pipeline.

The hierarchy mirrors the UML directly:
  AccountInfo           — core user data stored in AccountDatabase
  AuditInformation      — single audit event record
  AccountLogin          — login operation request/response
  CreateAccount         — account creation request/response
  ViewAccount           — account view response
  EditAccount           — account edit request/response
  AccountPageDisplay    — presentation layer page responses
  AccountMessagesDisplay — presentation layer message responses
  AuditLogView          — audit log presentation responses
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Annotated

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """
    Roles a user account can hold within the SCEMAS system.
    Determines which agents and operations are accessible.
    """
    ADMIN = "admin"               # full system access
    CITY_OPERATOR = "city_operator"   # city dashboard + alert management
    ANALYST = "analyst"           # read-only data access
    PUBLIC = "public"             # public feed only (minimal access)


class AuditEventType(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    EDIT_ACCOUNT = "EDIT_ACCOUNT"
    VIEW_ACCOUNT = "VIEW_ACCOUNT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"


class PageMessageType(str, Enum):
    """Classifies the type of feedback message shown in the presentation layer."""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"


# ---------------------------------------------------------------------------
# AccountInfo — core user data (stored in AccountDatabase)
# ---------------------------------------------------------------------------

class AccountInfoSchema(BaseModel):
    """
    Represents the AccountInfo object stored and retrieved by AccountDatabase.
    Passwords are never returned in responses — only accepted in requests.
    """
    userId: Annotated[str, Field(example="user-001")]
    phoneNum: Annotated[str, Field(example="+1-416-555-0100")]
    email: Annotated[EmailStr, Field(example="operator@scemas.city")]
    role: Annotated[UserRole, Field(example=UserRole.CITY_OPERATOR)]


class AccountInfoResponse(AccountInfoSchema):
    """Safe account info returned to callers — no password field."""
    pass


# ---------------------------------------------------------------------------
# AuditInformation — single audit event
# ---------------------------------------------------------------------------

class AuditInformationSchema(BaseModel):
    """
    Mirrors the UML AuditInformation class.
    Represents one auditable event associated with a user account.
    """
    userId: Annotated[str, Field(example="user-001")]
    EventType: AuditEventType
    EventDesc: Annotated[str, Field(example="User logged in successfully.")]
    EventDate: Annotated[int, Field(
        description="Unix timestamp (seconds since epoch).",
        example=1748736000
    )]


# ---------------------------------------------------------------------------
# AccountLogin — UML: login(userId, password): boolean
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    userId: Annotated[str, Field(example="user-001")]
    password: Annotated[str, Field(min_length=8, example="SecurePass123!")]


class LoginResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    role: Optional[UserRole] = None
    message: str = ""
    # page: what the presentation layer should show next
    page: Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# CreateAccount — UML: createAccount(userId, password, email, phone-num, role)
# ---------------------------------------------------------------------------

class CreateAccountRequest(BaseModel):
    userId: Annotated[str, Field(example="user-002")]
    password: Annotated[str, Field(min_length=8, example="SecurePass123!")]
    email: Annotated[EmailStr, Field(example="newuser@scemas.city")]
    phone_num: Annotated[str, Field(example="+1-416-555-0101")]
    role: Annotated[UserRole, Field(example=UserRole.ANALYST)]


class CreateAccountResponse(BaseModel):
    success: bool
    userId: Optional[str] = None
    message: str = ""
    page: Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# ViewAccount — UML: viewAccount(): void
# Presented via AccountPageDisplay
# ---------------------------------------------------------------------------

class ViewAccountResponse(BaseModel):
    account_info: AccountInfoResponse
    page: Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# EditAccount — UML: editAccount(password, email, phone-num): boolean
# ---------------------------------------------------------------------------

class EditAccountRequest(BaseModel):
    """
    All fields are optional — only supplied fields are updated.
    userId is not editable; it is taken from the path parameter.
    """
    password: Optional[str] = Field(None, min_length=8)
    email: Optional[EmailStr] = None
    phone_num: Optional[str] = None


class EditAccountResponse(BaseModel):
    success: bool
    message: str = ""
    page: Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# Presentation layer — AccountPageDisplay and AccountMessagesDisplay
#
# LoginPage, CreateProfilePage   → implement AccountPageDisplay
# AccountError, AccountSuccess   → implement AccountMessagesDisplay
#
# These are modelled as a unified PageDisplaySchema so the API can return
# a consistent structure regardless of which concrete page is active.
# ---------------------------------------------------------------------------

class PageDisplaySchema(BaseModel):
    """
    Unified representation of the presentation layer page/message state.
    Maps to whichever concrete class (LoginPage, CreateProfilePage,
    AccountError, AccountSuccess) is appropriate for the operation.
    """
    page_type: Annotated[str, Field(
        description=(
            "Which concrete presentation class is active: "
            "'login_page', 'create_profile_page', 'account_error', 'account_success'."
        ),
        example="account_success"
    )]
    message_type: PageMessageType
    message: Annotated[str, Field(example="Account created successfully.")]


# ---------------------------------------------------------------------------
# AuditLogView — UML: displayMessage(): void, updatePage(): void
# Interface for presenting audit log data
# ---------------------------------------------------------------------------

class AuditLogEntryResponse(BaseModel):
    """Single audit log entry as returned by AuditLogView.displayMessage()."""
    userId: str
    EventType: AuditEventType
    EventDesc: str
    EventDate: int


class AuditLogPageResponse(BaseModel):
    """
    Paginated audit log view — AuditLogView.updatePage().
    Returned by the /audit routes.
    """
    entries: List[AuditLogEntryResponse]
    total: int
    page: int = 1
    page_size: int = 20


# ---------------------------------------------------------------------------
# AccountDatabase operation schemas
# Internal request/response types for database layer interactions.
# ---------------------------------------------------------------------------

class AccountDatabaseUpdateRequest(BaseModel):
    """Payload for AccountDatabase.updateAccountInfo()."""
    userId: str
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_num: Optional[str] = None


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str


# Resolve forward references
LoginResponse.model_rebuild()
CreateAccountResponse.model_rebuild()
ViewAccountResponse.model_rebuild()
EditAccountResponse.model_rebuild()
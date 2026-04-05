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
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    """
    Roles a user account can hold within the SCEMAS system.
    Values match the role constraint in the Supabase account_information table.
    """
    SYSTEM_ADMINISTRATOR = "System Administrator"
    CITY_OPERATOR        = "City Operator"
    PUBLIC_USER          = "Public User"


class AuditEventType(str, Enum):
    LOGIN           = "LOGIN"
    LOGOUT          = "LOGOUT"
    CREATE_ACCOUNT  = "CREATE_ACCOUNT"
    EDIT_ACCOUNT    = "EDIT_ACCOUNT"
    VIEW_ACCOUNT    = "VIEW_ACCOUNT"
    LOGIN_FAILED    = "LOGIN_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"


class PageMessageType(str, Enum):
    """Classifies the type of feedback message shown in the presentation layer."""
    SUCCESS = "success"
    ERROR   = "error"
    INFO    = "info"


# ---------------------------------------------------------------------------
# AccountInfo — core user data (stored in AccountDatabase / account_information)
# ---------------------------------------------------------------------------

class AccountInfoSchema(BaseModel):
    """
    Represents one row in the account_information table.
    Passwords are never returned in responses.
    """
    accountinfo_id: str = Field(..., example="uuid-here")
    user_id:        str = Field(..., example="auth-uuid-here")
    username:       str = Field(..., example="jdoe")
    email:          EmailStr = Field(..., example="operator@scemas.city")
    phone_number:   Optional[str] = Field(None, example="+1-416-555-0100")
    role:           UserRole = Field(..., example=UserRole.CITY_OPERATOR)
    is_active:      bool = Field(default=True)


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
    userId:    str = Field(..., example="auth-uuid-here")
    EventType: AuditEventType
    EventDesc: str = Field(..., example="User logged in successfully.")
    EventDate: int = Field(
        ...,
        description="Unix timestamp (seconds since epoch).",
        example=1748736000,
    )


# ---------------------------------------------------------------------------
# AccountLogin — UML: login(userId, password): boolean
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email:    EmailStr = Field(..., example="operator@scemas.city")
    password: str      = Field(..., min_length=6, example="SecurePass123!")


class LoginResponse(BaseModel):
    success:      bool
    user_id:      Optional[str] = None
    access_token: Optional[str] = None   # Supabase JWT — stored by the frontend
    role:         Optional[UserRole] = None
    message:      str = ""
    page:         Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# CreateAccount — UML: createAccount(userId, password, email, phone-num, role)
# ---------------------------------------------------------------------------

class CreateAccountRequest(BaseModel):
    username:     str      = Field(..., example="jdoe")
    email:        EmailStr = Field(..., example="newuser@scemas.city")
    password:     str      = Field(..., min_length=6, example="SecurePass123!")
    phone_number: Optional[str] = Field(None, example="+1-416-555-0101")
    role:         UserRole = Field(..., example=UserRole.CITY_OPERATOR)


class CreateAccountResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    message: str = ""
    page:    Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# ViewAccount — UML: viewAccount(): void
# Presented via AccountPageDisplay
# ---------------------------------------------------------------------------

class ViewAccountResponse(BaseModel):
    account_info: AccountInfoResponse
    page:         Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# EditAccount — UML: editAccount(password, email, phone-num): boolean
# All fields optional — only supplied fields are updated.
# ---------------------------------------------------------------------------

class EditAccountRequest(BaseModel):
    username:     Optional[str]      = None
    phone_number: Optional[str]      = None
    role:         Optional[UserRole] = None
    is_active:    Optional[bool]     = None


class EditAccountResponse(BaseModel):
    success: bool
    message: str = ""
    page:    Optional["PageDisplaySchema"] = None


# ---------------------------------------------------------------------------
# Presentation layer — AccountPageDisplay and AccountMessagesDisplay
# ---------------------------------------------------------------------------

class PageDisplaySchema(BaseModel):
    page_type:    str
    message_type: PageMessageType
    message:      str


# ---------------------------------------------------------------------------
# AuditLogView — UML: displayMessage(): void, updatePage(): void
# ---------------------------------------------------------------------------

class AuditLogEntryResponse(BaseModel):
    userId:    str
    EventType: AuditEventType
    EventDesc: str
    EventDate: int


class AuditLogPageResponse(BaseModel):
    entries:   List[AuditLogEntryResponse]
    total:     int
    page:      int = 1
    page_size: int = 20


# ---------------------------------------------------------------------------
# AccountDatabase operation schemas
# ---------------------------------------------------------------------------

class AccountDatabaseUpdateRequest(BaseModel):
    """Payload for AccountDatabase.updateAccountInfo()."""
    userId:       str
    username:     Optional[str]      = None
    phone_number: Optional[str]      = None
    role:         Optional[UserRole] = None
    is_active:    Optional[bool]     = None


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

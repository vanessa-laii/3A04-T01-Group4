"""
Accounts Agent Service — AccountsAbstraction
PAC Architecture: Abstraction layer of the Accounts Agent.

AccountsAbstraction sits between the AccountManagementController (control)
and the presentation layer (routes / page display classes). It holds:
  - The currently active user session state (post-login).
  - The most recently retrieved AccountInfo for display purposes.
  - A short in-memory buffer of recent audit events for the AuditLogView
    presentation layer, avoiding redundant DB reads for the same session.

The AccountDatabase is the durable store; this layer caches only what is
needed for the current request/session cycle.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from app.models import (
    AccountInfoResponse,
    AuditInformationSchema,
    AuditLogEntryResponse,
    PageDisplaySchema,
    PageMessageType,
    UserRole,
)


# Maximum audit events kept in the in-memory buffer per service instance
_AUDIT_BUFFER_SIZE = 100


class AccountsAbstraction:
    """
    Abstraction layer of the Accounts PAC Agent.

    Responsibilities:
    - Cache the most recently viewed/edited AccountInfo for fast reads.
    - Maintain the active session state (userId + role after login).
    - Buffer recent AuditLogData entries for the AuditLogView interface.
    - Produce the correct PageDisplaySchema for the presentation layer
      based on the outcome of each operation.
    """

    def __init__(self):
        # Active session (set on successful login, cleared on logout)
        self._active_user_id: Optional[str] = None
        self._active_user_role: Optional[UserRole] = None

        # Most recently retrieved AccountInfo (for viewAccount / editAccount)
        self._current_account: Optional[AccountInfoResponse] = None

        # Audit log buffer — AuditLogView presentation layer cache
        self._audit_buffer: Deque[AuditInformationSchema] = deque(
            maxlen=_AUDIT_BUFFER_SIZE
        )

        # Current presentation layer page state
        self._current_page: Optional[PageDisplaySchema] = None

    # -----------------------------------------------------------------------
    # Session state
    # -----------------------------------------------------------------------

    def set_active_session(self, userId: str, role: UserRole) -> None:
        """Called by the controller on successful login."""
        self._active_user_id = userId
        self._active_user_role = role

    def clear_session(self) -> None:
        """Called on logout or session expiry."""
        self._active_user_id = None
        self._active_user_role = None
        self._current_account = None

    def get_active_user_id(self) -> Optional[str]:
        return self._active_user_id

    def get_active_user_role(self) -> Optional[UserRole]:
        return self._active_user_role

    def is_authenticated(self) -> bool:
        return self._active_user_id is not None

    # -----------------------------------------------------------------------
    # AccountInfo cache
    # -----------------------------------------------------------------------

    def set_current_account(self, account: AccountInfoResponse) -> None:
        self._current_account = account

    def get_current_account(self) -> Optional[AccountInfoResponse]:
        return self._current_account

    # -----------------------------------------------------------------------
    # Presentation layer — AccountPageDisplay / AccountMessagesDisplay
    # Produces the correct PageDisplaySchema for LoginPage, CreateProfilePage,
    # AccountError, and AccountSuccess concrete classes.
    # -----------------------------------------------------------------------

    def build_success_page(self, page_type: str, message: str) -> PageDisplaySchema:
        """Maps to AccountSuccess / successful AccountPageDisplay."""
        page = PageDisplaySchema(
            page_type=page_type,
            message_type=PageMessageType.SUCCESS,
            message=message,
        )
        self._current_page = page
        return page

    def build_error_page(self, page_type: str, message: str) -> PageDisplaySchema:
        """Maps to AccountError."""
        page = PageDisplaySchema(
            page_type=page_type,
            message_type=PageMessageType.ERROR,
            message=message,
        )
        self._current_page = page
        return page

    def build_info_page(self, page_type: str, message: str) -> PageDisplaySchema:
        """Maps to a neutral AccountPageDisplay (e.g. LoginPage prompt)."""
        page = PageDisplaySchema(
            page_type=page_type,
            message_type=PageMessageType.INFO,
            message=message,
        )
        self._current_page = page
        return page

    def get_current_page(self) -> Optional[PageDisplaySchema]:
        return self._current_page

    # -----------------------------------------------------------------------
    # Audit log buffer — AuditLogView interface
    # -----------------------------------------------------------------------

    def record_audit_event(self, event: AuditInformationSchema) -> None:
        """Append a new audit event to the rolling buffer."""
        self._audit_buffer.appendleft(event)

    def get_audit_events(
        self,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[AuditLogEntryResponse]:
        """
        Return buffered audit events as AuditLogView presentation objects.
        Optionally filter by userId.
        """
        events = list(self._audit_buffer)

        if user_id:
            events = [e for e in events if e.userId == user_id]

        return [
            AuditLogEntryResponse(
                userId=e.userId,
                EventType=e.EventType,
                EventDesc=e.EventDesc,
                EventDate=e.EventDate,
            )
            for e in events[:limit]
        ]
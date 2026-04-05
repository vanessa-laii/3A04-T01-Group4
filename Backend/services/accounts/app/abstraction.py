"""
Accounts Agent Service — AccountsAbstraction
PAC Architecture: Abstraction layer of the Accounts Agent.
"""

from __future__ import annotations

import uuid
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
    """

    def __init__(self):
        # FIXED: Changed type to uuid.UUID to match AccountInfoResponse.accountinfo_id
        self._active_user_id: Optional[uuid.UUID] = None
        self._active_user_role: Optional[UserRole] = None

        # Most recently retrieved AccountInfo
        self._current_account: Optional[AccountInfoResponse] = None

        # Audit log buffer
        self._audit_buffer: Deque[AuditInformationSchema] = deque(
            maxlen=_AUDIT_BUFFER_SIZE
        )

        # Current presentation layer page state
        self._current_page: Optional[PageDisplaySchema] = None

    # -----------------------------------------------------------------------
    # Session state
    # -----------------------------------------------------------------------

    def set_active_session(self, user_id: uuid.UUID, role: UserRole) -> None:
        """Called by the controller on successful login."""
        self._active_user_id = user_id
        self._active_user_role = role

    def clear_session(self) -> None:
        """Called on logout or session expiry."""
        self._active_user_id = None
        self._active_user_role = None
        self._current_account = None

    def get_active_user_id(self) -> Optional[uuid.UUID]:
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
    # Presentation layer
    # -----------------------------------------------------------------------

    def build_success_page(self, page_type: str, message: str) -> PageDisplaySchema:
        page = PageDisplaySchema(
            page_type=page_type,
            message_type=PageMessageType.SUCCESS,
            message=message,
        )
        self._current_page = page
        return page

    def build_error_page(self, page_type: str, message: str) -> PageDisplaySchema:
        page = PageDisplaySchema(
            page_type=page_type,
            message_type=PageMessageType.ERROR,
            message=message,
        )
        self._current_page = page
        return page

    def build_info_page(self, page_type: str, message: str) -> PageDisplaySchema:
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
        user_id: Optional[uuid.UUID] = None,
    ) -> List[AuditLogEntryResponse]:
        """
        Return buffered audit events as AuditLogView presentation objects.
        """
        events = list(self._audit_buffer)

        # FIXED: Changed attribute access from .userId to .user_id
        if user_id:
            events = [e for e in events if e.user_id == user_id]

        # FIXED: Mapped AuditInformationSchema fields to AuditLogEntryResponse fields
        # Models.py uses snake_case: log_id, event_type, action_description, timestamp, status
        return [
            AuditLogEntryResponse(
                log_id=e.log_id or uuid.uuid4(), # Handle Optional log_id
                event_type=e.event_type,
                action_description=e.action_description,
                user_id=e.user_id,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                status=e.status,
                ip_address=e.ip_address,
                timestamp=e.timestamp,
            )
            for e in events[:limit]
        ]
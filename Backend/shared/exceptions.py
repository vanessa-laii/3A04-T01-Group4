"""
SCEMAS Shared — Exception Types
Common exception hierarchy shared across all five agents.

Defining exceptions here means agents can raise and catch the same
exception types across service boundaries (e.g. in tests, or if agents
ever share an in-process layer). Each agent's routes.py maps these to
the appropriate HTTP status codes via FastAPI exception handlers.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class SCEMASException(Exception):
    """Base exception for all SCEMAS agent errors."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail or message

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------

class NotFoundError(SCEMASException):
    """
    Raised when a requested resource does not exist.
    Maps to HTTP 404.

    Examples:
      - Alert rule ID not found in ConfiguredAlertsDatabase
      - User account not found in AccountDatabase
      - Sensor record not found in SensorDatabase
    """
    pass


# ---------------------------------------------------------------------------
# Validation / bad input
# ---------------------------------------------------------------------------

class ValidationError(SCEMASException):
    """
    Raised when input data fails domain validation (beyond Pydantic).
    Maps to HTTP 422.

    Examples:
      - Sensor payload missing required fields after processJSONData
      - Unknown metric type in raw sensor JSON
    """
    pass


# ---------------------------------------------------------------------------
# Conflict / duplicate
# ---------------------------------------------------------------------------

class ConflictError(SCEMASException):
    """
    Raised when an operation would create a duplicate or violate a
    uniqueness constraint.
    Maps to HTTP 409.

    Examples:
      - Attempting to create an alert rule with an existing alertID
      - Attempting to register an account with an existing userId
    """
    pass


# ---------------------------------------------------------------------------
# State / workflow
# ---------------------------------------------------------------------------

class InvalidStateError(SCEMASException):
    """
    Raised when an operation is not valid for the current state of a
    resource.
    Maps to HTTP 409.

    Examples:
      - Trying to acknowledge an alert that is not ACTIVE
      - Trying to edit a RESOLVED alert rule
      - Trying to approve an alert not in the pending approvals queue
    """
    pass


class UnauthorisedError(SCEMASException):
    """
    Raised when a caller does not have permission to perform an operation.
    Maps to HTTP 403.

    Examples:
      - A PUBLIC role user attempting to approve an alert rule
      - An operator attempting to access audit logs without ADMIN role
    """
    pass


# ---------------------------------------------------------------------------
# Inter-service communication
# ---------------------------------------------------------------------------

class ServiceUnavailableError(SCEMASException):
    """
    Raised when an inter-service HTTP call fails (network error or
    non-2xx response from a downstream agent).
    Maps to HTTP 503.

    Examples:
      - City agent unable to reach the Public agent to forward an alert
      - DataProcessing unable to reach the City agent in sendToController
    """
    pass


class ForwardingError(ServiceUnavailableError):
    """
    Specialisation of ServiceUnavailableError for cases where data was
    successfully processed / stored but could not be forwarded upstream.
    The operation is considered partially successful.

    Examples:
      - SensorData stored in DB but sendToController returned False
      - Alert approved but forwarding to City agent failed
    """

    def __init__(self, message: str, resource_id: str = ""):
        super().__init__(message)
        self.resource_id = resource_id


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

class DatabaseError(SCEMASException):
    """
    Raised when a database operation fails unexpectedly.
    Maps to HTTP 500.

    Examples:
      - importDataDB raises an unexpected exception
      - AccountDatabase.updateAccountInfo fails at the DB layer
    """
    pass
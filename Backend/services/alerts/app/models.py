"""
Alerts Agent Service — Pydantic Models

Mirrors the UML class structure directly:
  TriggeredAlerts         — core alert data class with all UML fields
  ConfiguredAlertsDatabase — persistence layer schema
  AlertPresentation       — interface; represented as a response schema
  AlertManagement         — operation request/response schemas
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AlertSeverity(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertStatus(int, Enum):
    """
    Maps to the UML TriggeredAlerts.status: int field.
    Tracks an alert through its full lifecycle.
    """
    PENDING_APPROVAL = 0   # rule created, awaiting approval
    ACTIVE = 1             # approved and live
    ACKNOWLEDGED = 2       # operator has acknowledged it
    RESOLVED = 3           # no longer active
    REJECTED = 4           # approval was denied


class EnvironmentalType(str, Enum):
    """Maps to TriggeredAlerts.environmentalType: string."""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PARTICULATE_MATTER = "particulate_matter"
    AIR_QUALITY = "air_quality"
    NOISE_LEVEL = "noise_level"


# ---------------------------------------------------------------------------
# TriggeredAlerts — core UML data class
# UML fields:
#   - alertID: String
#   - threshold: double
#   - environmentalType: string
#   - region: String
#   - severity: int
#   - publiclyVisible: boolean
#   - time: String
#   - status: int
# UML methods (represented as computed properties / response fields):
#   + getAlertID(): string
#   + getSeverity(): int
#   + getStatus(): String
#   + getActions(): String
# ---------------------------------------------------------------------------

class TriggeredAlertsSchema(BaseModel):
    """
    Full representation of a TriggeredAlerts object.
    Used for DB storage and internal inter-service communication.
    """
    alertID: Annotated[str, Field(example="alert-001")]
    threshold: Annotated[float, Field(
        description="The threshold value that triggered this alert.",
        example=150.0
    )]
    environmentalType: EnvironmentalType
    region: Annotated[str, Field(example="Downtown")]
    severity: AlertSeverity
    publiclyVisible: bool = Field(
        ...,
        description="Whether this alert should be forwarded to the Public agent.",
    )
    time: Annotated[str, Field(
        description="ISO 8601 timestamp when the alert was triggered.",
        example="2025-06-01T14:30:00Z",
    )]
    status: AlertStatus = AlertStatus.PENDING_APPROVAL

    # UML: getAlertID()
    def get_alert_id(self) -> str:
        return self.alertID

    # UML: getSeverity()
    def get_severity(self) -> int:
        return self.severity.value

    # UML: getStatus()
    def get_status(self) -> str:
        return self.status.name

    # UML: getActions()
    def get_actions(self) -> str:
        """
        Returns a human-readable string describing available actions
        for this alert given its current status.
        """
        action_map = {
            AlertStatus.PENDING_APPROVAL: "approve, reject",
            AlertStatus.ACTIVE: "acknowledge, resolve",
            AlertStatus.ACKNOWLEDGED: "resolve",
            AlertStatus.RESOLVED: "none",
            AlertStatus.REJECTED: "none",
        }
        return action_map.get(self.status, "none")


class TriggeredAlertsResponse(TriggeredAlertsSchema):
    """
    TriggeredAlerts as returned to API consumers.
    Adds the computed UML method outputs as response fields.
    """
    actions: str = ""

    @classmethod
    def from_schema(cls, alert: TriggeredAlertsSchema) -> "TriggeredAlertsResponse":
        data = alert.model_dump()
        data["actions"] = alert.get_actions()
        return cls(**data)


# ---------------------------------------------------------------------------
# AlertPresentation — UML <<interface>>
# UML fields / methods:
#   - triggeredAlerts: TriggeredAlerts
#   + update(AlertPresentation)
# Modelled as a response schema representing the current presentation state.
# ---------------------------------------------------------------------------

class AlertPresentationSchema(BaseModel):
    """
    Represents the AlertPresentation interface state.
    Holds the currently active/relevant alert for display purposes.
    """
    triggered_alert: Optional[TriggeredAlertsResponse] = None
    presentation_message: Annotated[str, Field(
        description="Human-readable message for the presentation layer.",
        example="CRITICAL: Air quality threshold exceeded in Downtown.",
    )]
    last_updated: Annotated[str, Field(example="2025-06-01T14:30:05Z")]


# ---------------------------------------------------------------------------
# ConfiguredAlertsDatabase — UML persistence class
# UML: + TriggeredAlerts: TriggeredAlerts
# ---------------------------------------------------------------------------

class ConfiguredAlertsDatabaseRecord(BaseModel):
    """A single record as stored in ConfiguredAlertsDatabase."""
    record_id: Annotated[str, Field(..., example="db-rec-001")]
    stored_at: Annotated[str, Field(..., example="2025-06-01T14:30:01Z")]
    alert: TriggeredAlertsSchema


class AlertDatabaseQueryParams(BaseModel):
    """Query filters for ConfiguredAlertsDatabase."""
    region: Annotated[Optional[str], Field(example="Downtown")]
    environmental_type: Optional[EnvironmentalType] = None
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    publicly_visible: Optional[bool] = None
    limit: int = Field(100, ge=1, le=1000)


class AlertDatabaseQueryResponse(BaseModel):
    records: List[ConfiguredAlertsDatabaseRecord]
    total: int


# ---------------------------------------------------------------------------
# AlertManagement operation request / response schemas
# One schema pair per UML method.
# ---------------------------------------------------------------------------

# createAlertRule(alertID, environmentalType, Region, threshold, time, visibility)
class CreateAlertRuleRequest(BaseModel):
    alertID: Annotated[str, Field(example="alert-001")]
    environmentalType: EnvironmentalType
    region: Annotated[str, Field(example="Downtown")]
    threshold: Annotated[float, Field(example=150.0)]
    severity: AlertSeverity = AlertSeverity.MEDIUM
    time: Annotated[str, Field( example="2025-06-01T14:30:00Z")]
    publiclyVisible: bool = False


class CreateAlertRuleResponse(BaseModel):
    success: bool
    alertID: Optional[str] = None
    status: Optional[AlertStatus] = None
    message: str = ""
    presentation: Optional[AlertPresentationSchema] = None


# sendForApproval(alertID): void
class SendForApprovalResponse(BaseModel):
    success: bool
    alertID: str
    message: str = ""
    presentation: Optional[AlertPresentationSchema] = None


# editAlertRule(alertID, updates): boolean
class EditAlertRuleRequest(BaseModel):
    """All fields optional — only supplied values are updated."""
    threshold: Optional[float] = None
    severity: Optional[AlertSeverity] = None
    region: Optional[str] = None
    time: Optional[str] = None
    publiclyVisible: Optional[bool] = None


class EditAlertRuleResponse(BaseModel):
    success: bool
    alertID: str
    message: str = ""
    presentation: Optional[AlertPresentationSchema] = None


# deleteAlertRule(alertID): boolean
class DeleteAlertRuleResponse(BaseModel):
    success: bool
    alertID: str
    message: str = ""


# acknowledgeAlert(alertID, operatorID): void
class AcknowledgeAlertRequest(BaseModel):
    operatorID: Annotated[str, Field(example="operator-001")]


class AcknowledgeAlertResponse(BaseModel):
    success: bool
    alertID: str
    operatorID: str
    message: str = ""
    presentation: Optional[AlertPresentationSchema] = None


# approveAlertRule(alertID): boolean
class ApproveAlertRuleResponse(BaseModel):
    success: bool
    alertID: str
    forwarded_to_city: bool = False
    message: str = ""
    presentation: Optional[AlertPresentationSchema] = None


# Reject (complement to approve — not in UML but needed for workflow)
class RejectAlertRuleResponse(BaseModel):
    success: bool
    alertID: str
    message: str = ""


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str
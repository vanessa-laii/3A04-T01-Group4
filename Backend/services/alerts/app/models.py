"""
Alerts Agent Service — Pydantic Models

Mirrors the UML class structure directly:
  TriggeredAlerts         — core alert data class with all UML fields
  ConfiguredAlertsDatabase — persistence layer schema
  AlertPresentation       — interface; represented as a response schema
  AlertManagement         — operation request/response schemas
"""

from __future__ import annotations
 
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Annotated
 
from pydantic import BaseModel, Field
 
 
# ---------------------------------------------------------------------------
# Enums — values match DB CHECK constraints exactly
# ---------------------------------------------------------------------------
 
class EnvironmentalMetric(str, Enum):
    """Matches: ARRAY['Air Quality','Temperature','Humidity','Noise Levels','UV Levels']"""
    AIR_QUALITY    = "Air Quality"
    TEMPERATURE    = "Temperature"
    HUMIDITY       = "Humidity"
    NOISE_LEVELS   = "Noise Levels"
    UV_LEVELS      = "UV Levels"
 
 
class AlertVisibility(str, Enum):
    """Matches: ARRAY['Internal','Public Facing']"""
    INTERNAL      = "Internal"
    PUBLIC_FACING = "Public Facing"
 
 
class ConfiguredAlertStatus(str, Enum):
    """Matches: ARRAY['pending','approved','rejected']"""
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
 
 
class TriggeredAlertSeverity(str, Enum):
    """Matches: ARRAY['Low','Medium','High','Critical']"""
    LOW      = "Low"
    MEDIUM   = "Medium"
    HIGH     = "High"
    CRITICAL = "Critical"
 
 
class TriggeredAlertStatus(str, Enum):
    """Matches: ARRAY['active','acknowledged','resolved','dismissed']"""
    ACTIVE       = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED     = "resolved"
    DISMISSED    = "dismissed"
 
 
# ---------------------------------------------------------------------------
# ConfiguredAlerts schemas
# ---------------------------------------------------------------------------
 
class ConfiguredAlertSchema(BaseModel):
    """Full representation of a configured_alerts record."""
    alert_id:             Optional[uuid.UUID]    = None   # set by DB
    operator_id:          uuid.UUID              = Field(..., description="accountinfo_id of the operator who created this rule.")
    environmental_metric: EnvironmentalMetric
    geographic_area:      Annotated[str  , Field(example="Downtown")]
    threshold_value:      Annotated[float, Field(example=150.0)]
    timeframe_minutes:    Annotated[int  , Field(example=15)]
    alert_visibility:     AlertVisibility
    alert_name:           Annotated[str  , Field(example="Downtown AQI High Alert")]
    threshold_value_max:  Optional[float]        = None
    condition:            str                    = 'ABOVE'
    description:          Optional[str]          = None
    is_active:            bool                   = True
    created_at:           Optional[datetime]     = None
    updated_at:           Optional[datetime]     = None
    approved_by:          Optional[uuid.UUID]    = None
    approval_date:        Optional[datetime]     = None
    status:               ConfiguredAlertStatus  = ConfiguredAlertStatus.PENDING
 
 
class CreateAlertRuleRequest(BaseModel):
    """Request to create a new configured alert rule."""
    operator_id:          uuid.UUID
    environmental_metric: EnvironmentalMetric
    geographic_area:      Annotated[str  , Field(example="Downtown")]
    threshold_value:      Annotated[float, Field(example=150.0)]
    timeframe_minutes:    Annotated[int  , Field(example=15)]
    alert_visibility:     AlertVisibility
    alert_name:           Annotated[str  , Field(example="Downtown AQI High Alert")]
    threshold_value_max:  Optional[float] = None
    condition:            str             = 'ABOVE'
    description:          Optional[str]   = None
 
 
class CreateAlertRuleResponse(BaseModel):
    success:  bool
    alert_id: Optional[uuid.UUID] = None
    status:   Optional[ConfiguredAlertStatus] = None
    message:  str = ""
    presentation: Optional["AlertPresentationSchema"] = None
 
 
class EditAlertRuleRequest(BaseModel):
    """Partial update — only supplied fields are changed."""
    threshold_value:      Optional[float]              = None
    threshold_value_max:  Optional[float]              = None
    timeframe_minutes:    Optional[int]                = None
    geographic_area:      Optional[str]                = None
    environmental_metric: Optional[EnvironmentalMetric] = None
    alert_visibility:     Optional[AlertVisibility]    = None
    alert_name:           Optional[str]                = None
    condition:            Optional[str]                = None
    description:          Optional[str]                = None
    is_active:            Optional[bool]               = None
 
 
class EditAlertRuleResponse(BaseModel):
    success:  bool
    alert_id: uuid.UUID
    message:  str = ""
    presentation: Optional["AlertPresentationSchema"] = None
 
 
class SendForApprovalResponse(BaseModel):
    success:  bool
    alert_id: uuid.UUID
    message:  str = ""
    presentation: Optional["AlertPresentationSchema"] = None
 
 
class ApproveAlertRuleResponse(BaseModel):
    success:              bool
    alert_id:             uuid.UUID
    forwarded_to_city:    bool = False
    message:              str = ""
    presentation:         Optional["AlertPresentationSchema"] = None
 
 
class RejectAlertRuleResponse(BaseModel):
    success:  bool
    alert_id: uuid.UUID
    message:  str = ""
 
 
class DeleteAlertRuleResponse(BaseModel):
    success:  bool
    alert_id: uuid.UUID
    message:  str = ""
 
 
# ---------------------------------------------------------------------------
# TriggeredAlerts schemas
# ---------------------------------------------------------------------------
 
class TriggeredAlertSchema(BaseModel):
    """Full representation of a triggered_alerts record."""
    triggered_alert_id: Optional[uuid.UUID]          = None   # set by DB
    alert_id:           uuid.UUID                    = Field(..., description="FK to configured_alerts.alert_id")
    triggered_value:    Annotated[float, Field(example=162.4)]
    sensor_id:          Optional[str]                = None
    region:             Optional[str]                = None
    triggered_at:       Optional[datetime]           = None
    acknowledged_at:    Optional[datetime]           = None
    acknowledged_by:    Optional[uuid.UUID]          = None
    is_false_alarm:     bool                         = False
    alert_severity:     Optional[TriggeredAlertSeverity] = None
    is_public:          bool                         = False
    status:             TriggeredAlertStatus         = TriggeredAlertStatus.ACTIVE
 
    # UML method equivalents — computed from schema fields
    def get_alert_id(self) -> str:
        return str(self.alert_id)
 
    def get_severity(self) -> str:
        return self.alert_severity.value if self.alert_severity else "Unknown"
 
    def get_status(self) -> str:
        return self.status.value
 
    def get_actions(self) -> str:
        action_map = {
            TriggeredAlertStatus.ACTIVE:       "acknowledge, resolve, dismiss",
            TriggeredAlertStatus.ACKNOWLEDGED: "resolve, dismiss",
            TriggeredAlertStatus.RESOLVED:     "none",
            TriggeredAlertStatus.DISMISSED:    "none",
        }
        return action_map.get(self.status, "none")
 
 
class AcknowledgeAlertRequest(BaseModel):
    operator_id: uuid.UUID = Field(..., description="accountinfo_id of the acknowledging operator.")
 
 
class AcknowledgeAlertResponse(BaseModel):
    success:            bool
    triggered_alert_id: uuid.UUID
    operator_id:        uuid.UUID
    message:            str = ""
    presentation:       Optional["AlertPresentationSchema"] = None
 
 
# ---------------------------------------------------------------------------
# AlertPresentation — interface state schema
# ---------------------------------------------------------------------------
 
class AlertPresentationSchema(BaseModel):
    """Current AlertPresentation state held by the abstraction layer."""
    configured_alert:  Optional[ConfiguredAlertSchema]  = None
    triggered_alert:   Optional[TriggeredAlertSchema]   = None
    presentation_message: str = ""
    last_updated:      str = ""
 
 
# ---------------------------------------------------------------------------
# Database query schemas
# ---------------------------------------------------------------------------
 
class AlertDatabaseQueryParams(BaseModel):
    geographic_area:      Optional[str]                      = None
    environmental_metric: Optional[EnvironmentalMetric]      = None
    configured_status:    Optional[ConfiguredAlertStatus]    = None
    triggered_status:     Optional[TriggeredAlertStatus]     = None
    severity:             Optional[TriggeredAlertSeverity]   = None
    is_public:            Optional[bool]                     = None
    limit:                int = Field(100, ge=1, le=1000)
 
 
class ConfiguredAlertsDatabaseRecord(BaseModel):
    alert:      ConfiguredAlertSchema
    triggered:  List[TriggeredAlertSchema] = []
 
 
class AlertDatabaseQueryResponse(BaseModel):
    records: List[ConfiguredAlertsDatabaseRecord]
    total:   int
 
 
# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------
 
class SuccessResponse(BaseModel):
    success: bool
    message: str = ""
 
 
class ErrorResponse(BaseModel):
    detail: str
 
 
# Resolve forward references
CreateAlertRuleResponse.model_rebuild()
EditAlertRuleResponse.model_rebuild()
SendForApprovalResponse.model_rebuild()
ApproveAlertRuleResponse.model_rebuild()
AcknowledgeAlertResponse.model_rebuild()
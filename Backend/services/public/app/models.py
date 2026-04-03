"""
Public Agent Service — Pydantic Models
Defines request bodies, response schemas, and inter-service data-transfer
objects used across routes, the controller, and the abstraction layer.

All schemas here represent data that has been approved for public
visibility — no sensitive operational data is exposed.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SensorMetricType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PARTICULATE_MATTER = "particulate_matter"
    AIR_QUALITY = "air_quality"
    NOISE_LEVEL = "noise_level"


class AlertSeverity(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertStatus(int, Enum):
    ACTIVE = 1
    RESOLVED = 3


# ---------------------------------------------------------------------------
# Sensor data schemas
# Mirrors the shared SensorData / SensorMetrics structure but scoped to
# what the public surface should expose (no internal DB identifiers, etc.)
# ---------------------------------------------------------------------------

class SensorMetricSchema(BaseModel):
    metric_type: SensorMetricType
    value: float
    unit: Annotated[str, Field(example="celsius")]


class SensorDataSchema(BaseModel):
    timestamp: Annotated[str, Field(example="2025-06-01T12:00:00Z")]
    region: Annotated[str, Field(example="Downtown")]
    gps_location: Annotated[str, Field(example="43.6532,-79.3832")]
    metrics: List[SensorMetricSchema]


# ---------------------------------------------------------------------------
# PublicAbstraction schema
# What the abstraction layer surfaces to the presentation layer (PublicAPI)
# ---------------------------------------------------------------------------

class PublicAbstractionSchema(BaseModel):
    """Current public-approved sensor data held by PublicAbstraction."""
    sensor_data: SensorDataSchema
    region: str
    last_updated: Annotated[str, Field(example="2025-06-01T12:00:00Z")]


# ---------------------------------------------------------------------------
# PublicAPI schemas (Presentation layer / concrete PublicObserver)
# ---------------------------------------------------------------------------

class PublicAPISnapshot(BaseModel):
    """
    Full snapshot exposed by a PublicAPI observer instance.
    This is what external consumers (citizens, third-party apps) receive.
    """
    sensor_data: SensorDataSchema
    public_alerts: List["PublicAlertSchema"] = []


# ---------------------------------------------------------------------------
# Public Alerts
# Only alerts with publicly_visible=True reach this service
# ---------------------------------------------------------------------------

class PublicAlertSchema(BaseModel):
    alert_id: Annotated[str, Field(example="alert-001")]
    severity: AlertSeverity
    status: AlertStatus
    region: Annotated[str, Field(example="Downtown")]
    environmental_type: Annotated[str, Field(example="air_quality")]
    description: Annotated[str, Field(
        example="Air quality index has exceeded safe thresholds.",
    )]
    time: Annotated[str, Field(example="2025-06-01T11:45:00Z")]


# ---------------------------------------------------------------------------
# Observer management
# ---------------------------------------------------------------------------

class ObserverRegisterRequest(BaseModel):
    """Register a new PublicObserver."""
    observer_id: Annotated[str, Field(example="public-api-01")]
    callback_url: Annotated[Optional[str], Field(
        description="Webhook URL for remote observers (e.g. third-party apps).",
        example="http://third-party-app.example.com/api/scemas-update"
    )]


class ObserverListResponse(BaseModel):
    observers: List[str]


# ---------------------------------------------------------------------------
# Inbound inter-service schemas
# Received FROM the City agent
# ---------------------------------------------------------------------------

class InboundSensorData(BaseModel):
    """
    Payload sent by the City agent when new public-approved sensor data
    is available (mirrors ProcessedDataNotification on the city side).
    """
    sensor_data: SensorDataSchema
    source_service: str = "city"


class InboundAlertNotification(BaseModel):
    """
    Payload sent by the City agent when a publicly visible alert is
    triggered (forwarded from the Alerts agent via the City agent).
    """
    alert_id: str
    severity: AlertSeverity
    status: AlertStatus
    region: str
    environmental_type: str
    threshold: float
    time: str
    publicly_visible: bool = True  # always True by the time it reaches here


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class LocationRequest(BaseModel):
    region: Annotated[Optional[str], Field(example="Downtown")]


class LocationResponse(BaseModel):
    region: str
    gps_location: str


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str


# Resolve forward reference
PublicAPISnapshot.model_rebuild()
"""
City Agent Service — Pydantic Models
Defines request bodies, response schemas, and internal data-transfer
objects used across routes, the controller, and inter-service calls.
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
    PENDING = 0
    ACTIVE = 1
    ACKNOWLEDGED = 2
    RESOLVED = 3


# ---------------------------------------------------------------------------
# Sensor / SensorData schemas
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
# CityAbstraction — what the controller exposes to the dashboard layer
# ---------------------------------------------------------------------------

class CityAbstractionSchema(BaseModel):
    """Wraps SensorData as returned by CityAbstraction.getData()."""
    sensor_data: SensorDataSchema


# ---------------------------------------------------------------------------
# CityDashboard schemas
# ---------------------------------------------------------------------------

class DashboardLayoutSchema(BaseModel):
    """Payload for editing the city dashboard layout."""
    layout_config: Annotated[dict, Field(
        example={"widgets": ["air_quality_map", "alert_feed"]},
    )]


class DashboardSchema(BaseModel):
    """Snapshot of the current city dashboard state."""
    sensor_data: Optional[SensorDataSchema] = None
    layout_config: Optional[dict] = None


# ---------------------------------------------------------------------------
# Observer management
# ---------------------------------------------------------------------------

class ObserverRegisterRequest(BaseModel):
    """Register a new CityObserver (e.g. a dashboard instance or service)."""
    observer_id: Annotated[str, Field(example="dashboard-01")]
    callback_url: Annotated[Optional[str], Field(
        description="Webhook URL to POST updates to for remote observers.",
        example="http://webapp:3000/api/city-update",
    )]


class ObserverListResponse(BaseModel):
    observers: List[str]


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class LocationResponse(BaseModel):
    """Response from getUserLocation()."""
    region: str
    gps_location: str


class LocationRequest(BaseModel):
    """Optional filter — request location data for a specific region."""
    region: Annotated[Optional[str], Field(example="Downtown")]


# ---------------------------------------------------------------------------
# Inter-service call schemas
# (sent TO / received FROM AccountManagement, DataProcessing, etc.)
# ---------------------------------------------------------------------------

class ProcessedDataNotification(BaseModel):
    """
    Payload the DataProcessing service sends to the City service
    when new sensor data has been processed and stored.
    """
    sensor_data: SensorDataSchema
    source_service: str = "data_processing"


class AlertNotification(BaseModel):
    """
    Payload the Alerts service sends to the City service
    when a new alert has been triggered.
    """
    alert_id: str
    severity: AlertSeverity
    status: AlertStatus
    region: str
    environmental_type: str
    threshold: float
    time: str
    publicly_visible: bool


# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str
"""
Data Processing Agent Service — Pydantic Models
Defines request bodies, response schemas, and internal data-transfer
objects for the data ingestion and transformation pipeline.

The hierarchy mirrors the UML directly:
  ExternalSensorData  →  raw JSON from sensors (inbound)
  SensorData          →  structured, validated output
  SensorMetrics       →  abstract base; concrete subclasses per metric type
  SensorDatabase      →  persistence layer schema
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Annotated

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SensorMetricType(str, Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PARTICULATE_MATTER = "particulate_matter"
    AIR_QUALITY = "air_quality"
    NOISE_LEVEL = "noise_level"


class ProcessingStatus(str, Enum):
    """Tracks the state of a data batch through the pipeline."""
    RECEIVED = "received"       # raw JSON arrived
    PROCESSING = "processing"   # being parsed / validated
    STORED = "stored"           # persisted to SensorDatabase
    FORWARDED = "forwarded"     # sent to City agent
    FAILED = "failed"           # error at any stage


# ---------------------------------------------------------------------------
# Raw inbound payload — ExternalSensorData
# This is what physical sensors / gateway devices POST to this service.
# Intentionally loose (Dict) because sensor vendors vary; validation
# happens inside DataProcessing.processJSONData().
# ---------------------------------------------------------------------------

class RawSensorPayload(BaseModel):
    """
    Raw JSON payload arriving from ExternalSensorData.send_raw_JSON().
    The sensor_data field is an arbitrary dict — processJSONData() is
    responsible for parsing and validating its contents.
    """
    source_id: Annotated[
        str,
        Field(description="Unique identifier of the sensor or gateway device.",
        example="sensor-node-042")
    ]
    sensor_data: Annotated[
        Dict[str, Any], 
        Field(
        description="Raw sensor reading as collected by ExternalSensorData.",
        example={
            "timestamp": "2025-06-01T12:00:00Z",
            "region": "Downtown",
            "gps_location": "43.6532,-79.3832",
            "metrics": [
                {"type": "temperature", "value": 22.5, "unit": "celsius"},
                {"type": "air_quality", "value": 47.0, "unit": "AQI"},
            ],
        }),
    ]


# ---------------------------------------------------------------------------
# Structured sensor metric schemas — SensorMetrics hierarchy
# ---------------------------------------------------------------------------

class SensorMetricSchema(BaseModel):
    """Single structured metric reading (maps to a SensorMetrics subclass)."""
    metric_type: SensorMetricType
    value: float
    unit: Annotated[str, Field(..., example="celsius")]

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("Metric value must be a finite number.")
        return v


class TemperatureSchema(SensorMetricSchema):
    metric_type: SensorMetricType = SensorMetricType.TEMPERATURE
    unit: str = "celsius"


class HumiditySchema(SensorMetricSchema):
    metric_type: SensorMetricType = SensorMetricType.HUMIDITY
    unit: str = "percent"


class ParticulateMatterSchema(SensorMetricSchema):
    metric_type: SensorMetricType = SensorMetricType.PARTICULATE_MATTER
    unit: str = "µg/m³"


class AirQualitySchema(SensorMetricSchema):
    metric_type: SensorMetricType = SensorMetricType.AIR_QUALITY
    unit: str = "AQI"


class NoiseLevelSchema(SensorMetricSchema):
    metric_type: SensorMetricType = SensorMetricType.NOISE_LEVEL
    unit: str = "dB"


# ---------------------------------------------------------------------------
# SensorData — structured output of processJSONData()
# ---------------------------------------------------------------------------

class SensorDataSchema(BaseModel):
    """
    Fully validated, structured sensor reading.
    Produced by DataProcessing.processJSONData() and stored by importDataDB().
    """
    timestamp: Annotated[str, Field(..., example="2025-06-01T12:00:00Z")]
    region: Annotated[str, Field(..., example="Downtown")]
    gps_location: Annotated[str, Field(..., example="43.6532,-79.3832")]
    source_id: Annotated[str, Field(..., example="sensor-node-042")]
    metrics: List[SensorMetricSchema]

    @field_validator("metrics")
    @classmethod
    def metrics_must_not_be_empty(
        cls, v: List[SensorMetricSchema]
    ) -> List[SensorMetricSchema]:
        if not v:
            raise ValueError("SensorData must contain at least one metric.")
        return v


# ---------------------------------------------------------------------------
# SensorDatabase schemas — persistence layer
# ---------------------------------------------------------------------------

class SensorDatabaseRecord(BaseModel):
    """
    A single record as stored in / retrieved from the SensorDatabase.
    Wraps SensorDataSchema with a database-assigned ID and storage timestamp.
    """
    record_id: Annotated[str, Field(..., example="rec-00142")]
    stored_at: Annotated[str, Field(..., example="2025-06-01T12:00:05Z")]
    sensor_data: SensorDataSchema


class SensorDatabaseQueryParams(BaseModel):
    """Query filters for retrieving historical records from SensorDatabase."""
    region: Annotated[Optional[str], Field(None, example="Downtown")]
    metric_type: Optional[SensorMetricType] = None
    from_timestamp: Annotated[Optional[str], Field(None, example="2025-06-01T00:00:00Z")]
    to_timestamp: Annotated[Optional[str], Field(None, example="2025-06-01T23:59:59Z")]
    limit: int = Field(100, ge=1, le=1000)


class SensorDatabaseQueryResponse(BaseModel):
    records: List[SensorDatabaseRecord]
    total: int


# ---------------------------------------------------------------------------
# Pipeline processing response
# Returned after a full ingest cycle: receive → parse → store → forward
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    """
    Describes the outcome of a full data processing pipeline run triggered
    by a single RawSensorPayload.
    """
    source_id: str
    status: ProcessingStatus
    record_id: Optional[str] = None       # set if STORED
    forwarded_to_city: bool = False        # set if FORWARDED
    validation_errors: List[str] = []
    message: str = ""


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

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
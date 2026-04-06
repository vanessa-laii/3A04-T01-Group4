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
 
import uuid
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Annotated
 
from pydantic import BaseModel, Field, field_validator
import math
 
 
# ---------------------------------------------------------------------------
# Enums — values match DB CHECK constraints exactly
# ---------------------------------------------------------------------------
 
class MetricType(str, Enum):
    """Matches: ARRAY['Air Quality','Temperature','Humidity','Noise Levels','UV Levels']"""
    AIR_QUALITY  = "Air Quality"
    TEMPERATURE  = "Temperature"
    HUMIDITY     = "Humidity"
    NOISE_LEVELS = "Noise Levels"
    UV_LEVELS    = "UV Levels"
 
 
class DataQualityFlag(str, Enum):
    """Matches: ARRAY['valid','questionable','invalid']"""
    VALID        = "valid"
    QUESTIONABLE = "questionable"
    INVALID      = "invalid"
 
 
class ProcessingStatus(str, Enum):
    RECEIVED   = "received"
    PROCESSING = "processing"
    STORED     = "stored"
    FORWARDED  = "forwarded"
    FAILED     = "failed"
 
 
# ---------------------------------------------------------------------------
# SensorMetadata — static sensor registry
# ---------------------------------------------------------------------------
 
class SensorMetadataSchema(BaseModel):
    sensor_id:            str
    sensor_name:          Annotated[str  , Field(example="AQI Sensor Node 042")]
    geographic_zone:      Annotated[str  , Field(example="Downtown")]
    latitude:             Annotated[float, Field(example=43.6532)]
    longitude:            Annotated[float, Field(example=-79.3832)]
    sensor_type:          Annotated[str  , Field(example="Air Quality")]
    location_description: Optional[str]      = None
    installation_date:    Optional[datetime] = None
    is_active:            bool               = True
    last_maintenance:     Optional[datetime] = None
    manufacturer:         Optional[str]      = None
    model:                Optional[str]      = None
    created_at:           Optional[datetime] = None
 
 
# ---------------------------------------------------------------------------
# Individual metric reading — maps to one TimeSeriesSensorData row
# ---------------------------------------------------------------------------
 
class TimeSeriesReadingSchema(BaseModel):
    """
    A single metric reading row from time_series_sensor_data.
    This is the atomic unit of storage in the real schema.
    """
    data_id:             Optional[uuid.UUID]    = None   # set by DB
    sensor_id:           str
    metric_type:         MetricType
    metric_value:        float
    unit:                Annotated[str, Field(example="AQI")]
    recorded_at:         datetime
    geographic_zone:     Annotated[str, Field(example="Downtown")]
    data_quality_flag:   DataQualityFlag = DataQualityFlag.VALID
    additional_metadata: Optional[Dict[str, Any]] = None
    ingested_at:         Optional[datetime] = None
 
    @field_validator("metric_value")
    @classmethod
    def must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("metric_value must be finite.")
        return v
 
 
# ---------------------------------------------------------------------------
# Inbound API contract — raw sensor payload
# One payload produces N TimeSeriesReadingSchema rows (one per metric).
# This is what sensors POST to /sensor/ingest.
# ---------------------------------------------------------------------------
 
class RawSensorPayload(BaseModel):
    """
    Raw JSON payload from ExternalSensorData.send_raw_JSON().
    The sensor_data dict is intentionally loose — processJSONData()
    handles validation and normalisation.
    """
    source_id:   Annotated[str, Field(example="sensor-node-042")]
    sensor_data: Annotated[Dict[str, Any], Field(
        example={
            "recorded_at":    "2025-06-01T12:00:00Z",
            "geographic_zone": "Downtown",
            "metrics": [
                {"metric_type": "Air Quality", "value": 162.4, "unit": "AQI"},
                {"metric_type": "Temperature", "value": 28.1,  "unit": "celsius"},
            ],
        },
    )]
 
 
# ---------------------------------------------------------------------------
# SensorData — grouped view of one sensor payload across multiple rows
# Used internally and for forwarding to the City agent.
# ---------------------------------------------------------------------------
 
class SensorDataSchema(BaseModel):
    """
    Logical grouping of multiple TimeSeriesReadingSchema rows that arrived
    together from the same sensor at the same recorded_at timestamp.
    This is the unit forwarded to the City agent.
    """
    sensor_id:       str
    geographic_zone: str
    recorded_at:     datetime
    readings:        List[TimeSeriesReadingSchema]
 
    def get_reading(self, metric_type: MetricType) -> Optional[TimeSeriesReadingSchema]:
        for r in self.readings:
            if r.metric_type == metric_type:
                return r
        return None
 
 
# ---------------------------------------------------------------------------
# Database query schemas
# ---------------------------------------------------------------------------
 
class SensorDatabaseQueryParams(BaseModel):
    geographic_zone:   Optional[str]              = None
    metric_type:       Optional[MetricType]        = None
    sensor_id:         Optional[str]               = None
    from_recorded_at:  Optional[datetime]          = None
    to_recorded_at:    Optional[datetime]          = None
    data_quality_flag: Optional[DataQualityFlag]   = None
    limit:             int = Field(100, ge=1, le=1000)
 
 
class SensorDatabaseQueryResponse(BaseModel):
    readings: List[TimeSeriesReadingSchema]
    total:    int
 
 
# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------
 
class TriggeredAlertRecord(BaseModel):
    """
    Describes a single triggered_alerts row created during run_pipeline().
    Included in PipelineResult so callers know which rules fired.
    """
    alert_id:        uuid.UUID
    alert_name:      str
    environmental_metric: str
    geographic_area: str
    threshold_value: float
    triggered_value: float
    severity:        str
    is_public:       bool
 
 
class PipelineResult(BaseModel):
    source_id:          str
    status:             ProcessingStatus
    rows_inserted:      int = 0            # number of time_series rows created
    alerts_triggered:   List[TriggeredAlertRecord] = []  # rules that fired
    forwarded_to_city:  bool = False
    validation_errors:  List[str] = []
    message:            str = ""
 
 
# ---------------------------------------------------------------------------
# Location response
# Now derived from SensorMetadata (lat/lon) not from SensorData
# ---------------------------------------------------------------------------
 
class LocationResponse(BaseModel):
    sensor_id:       str
    sensor_name:     str
    geographic_zone: str
    latitude:        float
    longitude:       float
 
 
# ---------------------------------------------------------------------------
# Generic responses
# ---------------------------------------------------------------------------
 
class SuccessResponse(BaseModel):
    success: bool
    message: str = ""
 
 
class ErrorResponse(BaseModel):
    detail: str
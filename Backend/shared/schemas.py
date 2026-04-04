"""
SCEMAS Shared — Common Pydantic Schemas
Canonical API-boundary schemas used across multiple agents.

Any schema that appears in more than one agent's models.py should
live here instead. Each agent's models.py imports from this module
and extends or aliases as needed.

Current shared schemas:
  SensorMetricSchema   — single metric reading (request/response)
  SensorDataSchema     — full sensor reading (request/response)
  SuccessResponse      — generic boolean + message response
  ErrorResponse        — generic error detail response
  LocationResponse     — region + GPS (used by city, public, data_processing)
  LocationRequest      — optional region filter
"""

from __future__ import annotations

import math
from enum import Enum
from typing import List, Optional, Annotated

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SensorMetricType(str, Enum):
    """
    Canonical metric type enum. Import this in agent models.py files
    rather than redefining it locally.
    """
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PARTICULATE_MATTER = "particulate_matter"
    AIR_QUALITY = "air_quality"
    NOISE_LEVEL = "noise_level"


# ---------------------------------------------------------------------------
# Sensor schemas
# ---------------------------------------------------------------------------

class SensorMetricSchema(BaseModel):
    """
    Single structured metric reading.
    Shared between data_processing (output of processJSONData),
    city (abstraction layer), and public (feed).
    """
    metric_type: SensorMetricType
    value: float
    unit: Annotated[str, Field(example="celsius")]

    @field_validator("value")
    @classmethod
    def value_must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Metric value must be a finite number.")
        return v


class SensorDataSchema(BaseModel):
    """
    Fully structured sensor reading.
    This is the canonical inter-service representation of SensorData —
    used in HTTP payloads between data_processing → city → public.
    """
    timestamp: Annotated[str, Field(example="2025-06-01T12:00:00Z")]
    region: Annotated[str, Field(example="Downtown")]
    gps_location: Annotated[str, Field(example="43.6532,-79.3832")]
    source_id: Annotated[str, Field(example="sensor-node-042")]
    metrics: List[SensorMetricSchema]

    @field_validator("metrics")
    @classmethod
    def metrics_must_not_be_empty(
        cls, v: List[SensorMetricSchema]
    ) -> List[SensorMetricSchema]:
        if not v:
            raise ValueError("SensorData must contain at least one metric.")
        return v

    def get_metric(self, metric_type: SensorMetricType) -> Optional[SensorMetricSchema]:
        """Return the first metric matching the given type, or None."""
        for m in self.metrics:
            if m.metric_type == metric_type:
                return m
        return None


# ---------------------------------------------------------------------------
# Location schemas
# Shared between city, public, and data_processing agents.
# ---------------------------------------------------------------------------

class LocationRequest(BaseModel):
    region: Annotated[Optional[str], Field(example="Downtown")]


class LocationResponse(BaseModel):
    region: Annotated[str, Field(..., example="Downtown")]
    gps_location: Annotated[str, Field(..., example="43.6532,-79.3832")]


# ---------------------------------------------------------------------------
# Generic responses
# Shared across all five agents.
# ---------------------------------------------------------------------------

class SuccessResponse(BaseModel):
    success: bool
    message: str = ""


class ErrorResponse(BaseModel):
    detail: str
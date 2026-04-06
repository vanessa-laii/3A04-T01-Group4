"""
SCEMAS Shared Package
Exports the public API of the shared module so agents can import cleanly.

Usage in any agent:
    from shared import SensorData, SensorDataSchema, CityObserver
    from shared.exceptions import NotFoundError, ConflictError
"""

# Domain model classes
from shared.sensor_data import (
    Metric,
    SensorMetrics,
    Temperature,
    Humidity,
    ParticulateMatter,
    AirQuality,
    NoiseLevels,
    SensorData,
    SensorDatabaseInterface,
    make_metric,
)

# Observer pattern interfaces
from shared.observer import (
    CityObserver,
    CitySubject,
    PublicObserver,
    PublicSubject,
)

# Common Pydantic schemas
from shared.schemas import (
    SensorMetricType,
    SensorMetricSchema,
    SensorDataSchema,
    LocationRequest,
    LocationResponse,
    SuccessResponse,
    ErrorResponse,
)

# Exceptions
from shared.exceptions import (
    SCEMASException,
    NotFoundError,
    ValidationError,
    ConflictError,
    InvalidStateError,
    UnauthorisedError,
    ServiceUnavailableError,
    ForwardingError,
    DatabaseError,
)

__all__ = [
    # sensor_data
    "Metric",
    "SensorMetrics",
    "Temperature",
    "Humidity",
    "ParticulateMatter",
    "AirQuality",
    "NoiseLevels",
    "SensorData",
    "SensorDatabaseInterface",
    "make_metric",
    # observer
    "CityObserver",
    "CitySubject",
    "PublicObserver",
    "PublicSubject",
    # schemas
    "SensorMetricType",
    "SensorMetricSchema",
    "SensorDataSchema",
    "LocationRequest",
    "LocationResponse",
    "SuccessResponse",
    "ErrorResponse",
    # exceptions
    "SCEMASException",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "InvalidStateError",
    "ServiceUnavailableError",
    "ForwardingError",
    "DatabaseError",
]
"""
SCEMAS Shared — Sensor Data Classes
The canonical Python class definitions for the SensorMetrics hierarchy
and SensorData, shared across the data_processing, city, public, and
alerts agents.

UML classes defined here:
  SensorMetrics (<<Abstract Class>>) + all five concrete subclasses
  SensorData
  SensorDatabase (interface contract only — each agent has its own DB)

These are the domain model classes. For API-boundary Pydantic schemas
(used in FastAPI request/response bodies) see shared/schemas.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Metric — base value type (UML: Metric in SensorMetrics)
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    """
    Base value container for a single sensor reading.
    Subclasses or direct instances carry the raw numeric value and unit.
    """
    value: float = 0.0
    unit: str = ""

    def __repr__(self) -> str:
        return f"Metric(value={self.value}, unit={self.unit!r})"


# ---------------------------------------------------------------------------
# SensorMetrics — <<Abstract Class>>
# UML: + Metric: Metric
# ---------------------------------------------------------------------------

class SensorMetrics(ABC):
    """
    <<Abstract Class>> SensorMetrics

    Base class for all environmental sensor metric types.
    Each concrete subclass represents one measurable environmental
    dimension (temperature, humidity, etc.).

    UML attribute:
      + Metric: Metric
    """

    def __init__(self, value: float, unit: str):
        self.Metric = Metric(value=value, unit=unit)

    @property
    def value(self) -> float:
        return self.Metric.value

    @property
    def unit(self) -> str:
        return self.Metric.unit

    @abstractmethod
    def metric_type(self) -> str:
        """Return the string name of this metric type."""
        pass

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"value={self.value}, unit={self.unit!r})"
        )


# ---------------------------------------------------------------------------
# Concrete SensorMetrics subclasses
# UML: Temperature, Humidity, ParticulateMatter, AirQuality, NoiseLevels
# ---------------------------------------------------------------------------

class Temperature(SensorMetrics):
    """
    UML: Temperature
      + temperature_celsius: Float
    """

    def __init__(self, temperature_celsius: float):
        super().__init__(value=temperature_celsius, unit="celsius")
        self.temperature_celsius = temperature_celsius

    def metric_type(self) -> str:
        return "temperature"


class Humidity(SensorMetrics):
    """
    UML: Humidity
      + humidity_percent: Float
    """

    def __init__(self, humidity_percent: float):
        super().__init__(value=humidity_percent, unit="percent")
        self.humidity_percent = humidity_percent

    def metric_type(self) -> str:
        return "humidity"


class ParticulateMatter(SensorMetrics):
    """
    UML: Particulate matter
      + particulate_matter: Float
    """

    def __init__(self, particulate_matter: float):
        super().__init__(value=particulate_matter, unit="µg/m³")
        self.particulate_matter = particulate_matter

    def metric_type(self) -> str:
        return "particulate_matter"


class AirQuality(SensorMetrics):
    """
    UML: Air Quality
      + air_quality_index: Float
    """

    def __init__(self, air_quality_index: float):
        super().__init__(value=air_quality_index, unit="AQI")
        self.air_quality_index = air_quality_index

    def metric_type(self) -> str:
        return "air_quality"


class NoiseLevels(SensorMetrics):
    """
    UML: Noise levels
      + noise_level_db: Float
    """

    def __init__(self, noise_level_db: float):
        super().__init__(value=noise_level_db, unit="dB")
        self.noise_level_db = noise_level_db

    def metric_type(self) -> str:
        return "noise_level"


# ---------------------------------------------------------------------------
# Factory — build a SensorMetrics subclass from a type string
# Used by DataProcessing.processJSONData() to instantiate the right class
# ---------------------------------------------------------------------------

_METRIC_CLASS_MAP: dict[str, type] = {
    "temperature": Temperature,
    "humidity": Humidity,
    "particulate_matter": ParticulateMatter,
    "air_quality": AirQuality,
    "noise_level": NoiseLevels,
}


def make_metric(metric_type: str, value: float) -> SensorMetrics:
    """
    Factory function — given a metric type string and value, return
    the appropriate SensorMetrics subclass instance.

    Raises ValueError for unknown metric types.
    """
    cls = _METRIC_CLASS_MAP.get(metric_type)
    if cls is None:
        raise ValueError(
            f"Unknown metric type '{metric_type}'. "
            f"Valid types: {list(_METRIC_CLASS_MAP.keys())}"
        )
    return cls(value)


# ---------------------------------------------------------------------------
# SensorData
# UML:
#   + TimeStamp: String
#   + Region: String
#   + GPSLocation: String
#   + Metrics: SensorMetrics   (composition — SensorData owns its metrics)
# ---------------------------------------------------------------------------

@dataclass
class SensorData:
    """
    UML: SensorData

    The canonical sensor reading object. Produced by
    DataProcessing.processJSONData() and consumed by CityController,
    PublicController, and the alerts pipeline.

    UML shows a composition relationship: SensorData → SensorMetrics,
    modelled here as a list since a single reading can include multiple
    metric types simultaneously.
    """
    TimeStamp: str = ""
    Region: str = ""
    GPSLocation: str = ""
    Metrics: List[SensorMetrics] = field(default_factory=list)
    source_id: str = ""

    def get_metric(self, metric_type: str) -> Optional[SensorMetrics]:
        """Return the first metric matching the given type string, or None."""
        for m in self.Metrics:
            if m.metric_type() == metric_type:
                return m
        return None

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for inter-service HTTP payloads)."""
        return {
            "timestamp": self.TimeStamp,
            "region": self.Region,
            "gps_location": self.GPSLocation,
            "source_id": self.source_id,
            "metrics": [
                {
                    "metric_type": m.metric_type(),
                    "value": m.value,
                    "unit": m.unit,
                }
                for m in self.Metrics
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SensorData":
        """Deserialise from a plain dict (e.g. received from HTTP)."""
        metrics = [
            make_metric(m["metric_type"], m["value"])
            for m in data.get("metrics", [])
        ]
        return cls(
            TimeStamp=data.get("timestamp", ""),
            Region=data.get("region", ""),
            GPSLocation=data.get("gps_location", ""),
            source_id=data.get("source_id", ""),
            Metrics=metrics,
        )


# ---------------------------------------------------------------------------
# SensorDatabase — interface contract
# The full implementation lives in each agent's controller.py.
# This ABC ensures every agent's database class exposes the same contract.
# UML:
#   + SensorData: SensorData
#   + importData(SensorData): boolean
# ---------------------------------------------------------------------------

class SensorDatabaseInterface(ABC):
    """
    Interface contract for SensorDatabase implementations.
    Each agent that needs to persist SensorData should subclass this.
    """

    @abstractmethod
    async def import_data(self, sensor_data: SensorData) -> bool:
        """Persist a SensorData object. Returns True on success."""
        pass

    @abstractmethod
    async def get_latest(self) -> Optional[SensorData]:
        """Return the most recently stored SensorData object."""
        pass
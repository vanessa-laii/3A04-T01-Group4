"""
Data Processing Agent Service — DataAbstraction
PAC Architecture: Abstraction layer of the Data Processing Agent.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

# FIXED: Removed SensorDatabaseRecord (missing in models.py) 
# and added TimeSeriesReadingSchema if needed for granular tracking.
from app.models import (
    PipelineResult,
    ProcessingStatus,
    SensorDataSchema,
    TimeSeriesReadingSchema, 
)


# Maximum number of recent pipeline results kept in memory
_RESULT_BUFFER_SIZE = 50


class DataAbstraction:
    """
    Abstraction layer of the Data Processing PAC Agent.

    Responsibilities:
    - Cache the most recently processed SensorData for fast reads.
    - Maintain a rolling buffer of recent PipelineResults for status queries.
    - Track the overall pipeline status.
    - Provide a clean interface so routes never touch raw internal state.
    """

    def __init__(self):
        self._latest_sensor_data: Optional[SensorDataSchema] = None
        # FIXED: Changed type from SensorDatabaseRecord to TimeSeriesReadingSchema
        self._latest_readings: List[TimeSeriesReadingSchema] = []
        self._pipeline_status: ProcessingStatus = ProcessingStatus.RECEIVED
        self._result_buffer: Deque[PipelineResult] = deque(
            maxlen=_RESULT_BUFFER_SIZE
        )

    # -----------------------------------------------------------------------
    # Latest sensor data
    # -----------------------------------------------------------------------

    def set_latest_sensor_data(
        self,
        sensor_data: SensorDataSchema,
    ) -> None:
        """Update the cached sensor data after a successful processJSONData."""
        self._latest_sensor_data = sensor_data
        # Automatically update the associated readings from the schema
        self._latest_readings = sensor_data.readings

    def get_latest_sensor_data(self) -> Optional[SensorDataSchema]:
        return self._latest_sensor_data

    def get_latest_readings(self) -> List[TimeSeriesReadingSchema]:
        return self._latest_readings

    def has_data(self) -> bool:
        return self._latest_sensor_data is not None

    # -----------------------------------------------------------------------
    # Pipeline status
    # -----------------------------------------------------------------------

    def set_status(self, status: ProcessingStatus) -> None:
        self._pipeline_status = status

    def get_status(self) -> ProcessingStatus:
        return self._pipeline_status

    # -----------------------------------------------------------------------
    # Result buffer — rolling log of recent pipeline runs
    # -----------------------------------------------------------------------

    def record_result(self, result: PipelineResult) -> None:
        """Append a PipelineResult to the rolling buffer."""
        self._result_buffer.appendleft(result)

    def get_recent_results(self, limit: int = 20) -> List[PipelineResult]:
        """Return the most recent pipeline results, newest first."""
        return list(self._result_buffer)[:limit]

    def get_result_by_source(self, source_id: str) -> Optional[PipelineResult]:
        """Return the most recent result for a given sensor source_id."""
        for result in self._result_buffer:
            if result.source_id == source_id:
                return result
        return None
"""
Data Processing Agent Service — DataAbstraction
PAC Architecture: Abstraction layer of the Data Processing Agent.

DataAbstraction sits between the DataProcessingController (control) and
the presentation layer (pipeline status / query endpoints).  It holds:
  - The most recently processed SensorData snapshot.
  - A short in-memory ring buffer of recent pipeline results, useful for
    status polling without hitting the database.
  - The current processing status of the pipeline.

The SensorDatabase itself is the durable store; this abstraction layer
is intentionally lightweight and in-memory, acting as a fast-access
cache and status tracker for the control layer.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional

from app.models import (
    PipelineResult,
    ProcessingStatus,
    SensorDataSchema,
    SensorDatabaseRecord,
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
        self._latest_record: Optional[SensorDatabaseRecord] = None
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
        record: Optional[SensorDatabaseRecord] = None,
    ) -> None:
        """Update the cached sensor data after a successful processJSONData."""
        self._latest_sensor_data = sensor_data
        if record:
            self._latest_record = record

    def get_latest_sensor_data(self) -> Optional[SensorDataSchema]:
        return self._latest_sensor_data

    def get_latest_record(self) -> Optional[SensorDatabaseRecord]:
        return self._latest_record

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
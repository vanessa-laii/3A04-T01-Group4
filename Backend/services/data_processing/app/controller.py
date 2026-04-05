"""
Data Processing Agent Service — DataProcessingController
PAC Architecture: Control layer of the Data Processing Agent.

Implements the three core UML operations of DataProcessing:
  processJSONData(JSONData) -> SensorData
  importDataDB(SensorData)  -> boolean
  sendToController(SensorData) -> boolean

And orchestrates the full pipeline:
  ExternalSensorData.send_raw_JSON()
      → processJSONData()
          → importDataDB()
              → sendToController()  (City agent)

Also contains:
  SensorDatabase  — persistence abstraction (thin wrapper; real DB calls
                    go here once a database driver is wired in)
  ExternalSensorData — models the sensor-side data collection step
"""

from __future__ import annotations
 
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Annotated
 
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.abstraction import DataAbstraction
from app.orm_models import SensorMetadata, TimeSeriesSensorData
from app.models import (
    DataQualityFlag,
    LocationResponse,
    MetricType,
    PipelineResult,
    ProcessingStatus,
    RawSensorPayload,
    SensorDataSchema,
    SensorDatabaseQueryParams,
    SensorDatabaseQueryResponse,
    SensorMetadataSchema,
    TimeSeriesReadingSchema,
)
 
logger = logging.getLogger(__name__)
 
 
# ---------------------------------------------------------------------------
# ExternalSensorData — stateless, no changes needed
# ---------------------------------------------------------------------------
 
class ExternalSensorData:
    def collect_data_from_sensors(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "Active polling not implemented. POST to /api/v1/sensor/ingest."
        )
 
    def send_raw_JSON(self, raw_payload: RawSensorPayload) -> RawSensorPayload:
        return raw_payload
 
 
# ---------------------------------------------------------------------------
# SensorDatabase — two-table persistence layer
# ---------------------------------------------------------------------------
 
class SensorDatabase:
    """
    UML: SensorDatabase
      + importData(SensorData): boolean
 
    Now writes to sensor_metadata and time_series_sensor_data.
    """
 
    def __init__(self, session: AsyncSession):
        self._session = session
 
    async def upsert_metadata(
        self,
        sensor_id: str,
        geographic_zone: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        sensor_type: str = "Unknown",
    ) -> SensorMetadata:
        """
        INSERT sensor_metadata if not exists, otherwise leave it alone.
        Sensor metadata is managed separately from readings.
        """
        result = await self._session.execute(
            select(SensorMetadata).where(SensorMetadata.sensor_id == sensor_id)
        )
        row = result.scalar_one_or_none()
 
        if row is None:
            row = SensorMetadata(
                sensor_id=sensor_id,
                sensor_name=sensor_id,          # default; update via admin API
                geographic_zone=geographic_zone,
                latitude=latitude or 0.0,
                longitude=longitude or 0.0,
                sensor_type=sensor_type,
            )
            self._session.add(row)
            await self._session.flush()
            logger.info("SensorMetadata created: sensor_id=%s", sensor_id)
 
        return row
 
    async def import_data(
        self, sensor_data: SensorDataSchema
    ) -> List[TimeSeriesSensorData]:
        """
        INSERT one time_series_sensor_data row per metric reading.
        Returns the list of inserted ORM rows.
        """
        rows = []
        for reading in sensor_data.readings:
            row = TimeSeriesSensorData(
                sensor_id=sensor_data.sensor_id,
                metric_type=reading.metric_type.value,
                metric_value=reading.metric_value,
                unit=reading.unit,
                recorded_at=sensor_data.recorded_at,
                geographic_zone=sensor_data.geographic_zone,
                data_quality_flag=reading.data_quality_flag.value,
                additional_metadata=reading.additional_metadata,
            )
            self._session.add(row)
            rows.append(row)
 
        await self._session.flush()
        await self._session.commit()
        logger.info(
            "Inserted %d time_series rows: sensor_id=%s zone=%s",
            len(rows), sensor_data.sensor_id, sensor_data.geographic_zone,
        )
        return rows
 
    async def query(
        self, params: SensorDatabaseQueryParams
    ) -> SensorDatabaseQueryResponse:
        """
        SELECT from time_series_sensor_data with optional filters.
        """
        conditions = []
        if params.geographic_zone:
            conditions.append(TimeSeriesSensorData.geographic_zone == params.geographic_zone)
        if params.metric_type:
            conditions.append(TimeSeriesSensorData.metric_type == params.metric_type.value)
        if params.sensor_id:
            conditions.append(TimeSeriesSensorData.sensor_id == params.sensor_id)
        if params.from_recorded_at:
            conditions.append(TimeSeriesSensorData.recorded_at >= params.from_recorded_at)
        if params.to_recorded_at:
            conditions.append(TimeSeriesSensorData.recorded_at <= params.to_recorded_at)
        if params.data_quality_flag:
            conditions.append(TimeSeriesSensorData.data_quality_flag == params.data_quality_flag.value)
 
        q = (
            select(TimeSeriesSensorData)
            .order_by(TimeSeriesSensorData.recorded_at.desc())
            .limit(params.limit)
        )
        if conditions:
            q = q.where(and_(*conditions))
 
        result = await self._session.execute(q)
        rows = result.scalars().all()
        readings = [_row_to_reading(r) for r in rows]
        return SensorDatabaseQueryResponse(readings=readings, total=len(readings))
 
    async def get_sensor_metadata(
        self, sensor_id: str
    ) -> Optional[SensorMetadata]:
        result = await self._session.execute(
            select(SensorMetadata).where(SensorMetadata.sensor_id == sensor_id)
        )
        return result.scalar_one_or_none()
 
    async def get_all_metadata(self) -> List[SensorMetadata]:
        result = await self._session.execute(select(SensorMetadata))
        return list(result.scalars().all())
 
 
# ---------------------------------------------------------------------------
# DataProcessingController — Control layer
# ---------------------------------------------------------------------------
 
class DataProcessingController:
    """
    UML methods:
      processJSONData(JSONData) → SensorDataSchema
      importDataDB(SensorData)  → boolean
      sendToController(SensorData) → boolean
    """
 
    def __init__(
        self,
        session: AsyncSession,
        city_service_url: str,
        http_client: httpx.AsyncClient,
    ):
        self._database    = SensorDatabase(session)
        self._external    = ExternalSensorData()
        self._abstraction = DataAbstraction()
        self._city_url    = city_service_url
        self._http_client = http_client
 
    # -----------------------------------------------------------------------
    # UML: processJSONData(JSONData) → SensorData
    # -----------------------------------------------------------------------
 
    def process_json_data(self, raw_payload: RawSensorPayload) -> SensorDataSchema:
        """
        Parse raw sensor JSON into a SensorDataSchema (grouped view).
        Raises ValueError with descriptive messages on validation failure.
        """
        data = raw_payload.sensor_data
        errors: List[str] = []

        recorded_at_raw = data.get("recorded_at")
        geographic_zone = data.get("geographic_zone")
        raw_metrics = data.get("metrics", [])

        if recorded_at_raw is None:
            errors.append("Missing field: 'recorded_at'")
        if not isinstance(geographic_zone, str):
            errors.append("Field 'geographic_zone' must be a non-empty string")
        if not raw_metrics:
            errors.append("Missing or empty field: 'metrics'")

        if errors:
            raise ValueError(f"Invalid sensor payload: {'; '.join(errors)}")

        recorded_at: datetime
        try:
            if isinstance(recorded_at_raw, datetime):
                recorded_at = recorded_at_raw
            elif isinstance(recorded_at_raw, str):
                # Safe to call .replace() now because we confirmed it's a str
                iso_string = recorded_at_raw.replace("Z", "+00:00")
                recorded_at = datetime.fromisoformat(iso_string)
            else:
                raise ValueError("Must be a string or datetime object")
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(f"Invalid 'recorded_at' format: '{recorded_at_raw}'")

        readings: List[TimeSeriesReadingSchema] = []
        for i, raw_m in enumerate(raw_metrics):
            # Ensure raw_m is a dict before calling .get()
            if not isinstance(raw_m, dict):
                errors.append(f"Metric[{i}]: Expected dictionary, got {type(raw_m).__name__}")
                continue

            raw_type = raw_m.get("metric_type") or raw_m.get("type")
            value = raw_m.get("value")
            unit = str(raw_m.get("unit", ""))

            if raw_type is None or value is None:
                errors.append(f"Metric[{i}]: missing 'metric_type' or 'value'.")
                continue

            try:
                metric_type = MetricType(raw_type)
                readings.append(
                    TimeSeriesReadingSchema(
                        sensor_id=raw_payload.source_id,
                        metric_type=metric_type,
                        metric_value=float(value),
                        unit=unit,
                        recorded_at=recorded_at,
                        geographic_zone=str(geographic_zone), # Explicit cast for type safety
                    )
                )
            except (ValueError, TypeError):
                errors.append(f"Metric[{i}]: Invalid type or value.")

        if errors:
            raise ValueError(f"Metric parsing errors: {'; '.join(errors)}")

        return SensorDataSchema(
            sensor_id=raw_payload.source_id,
            geographic_zone=str(geographic_zone),
            recorded_at=recorded_at,
            readings=readings,
        )
 
    # -----------------------------------------------------------------------
    # UML: importDataDB(SensorData) → boolean
    # -----------------------------------------------------------------------
 
    async def import_data_db(
        self, sensor_data: SensorDataSchema
    ) -> Optional[int]:
        """
        Upserts sensor_metadata and inserts one time_series_sensor_data
        row per metric. Returns the number of rows inserted, or None on failure.
        """
        try:
            await self._database.upsert_metadata(
                sensor_id=sensor_data.sensor_id,
                geographic_zone=sensor_data.geographic_zone,
            )
            rows = await self._database.import_data(sensor_data)
            self._abstraction.set_latest_sensor_data(sensor_data)
            self._abstraction.set_status(ProcessingStatus.STORED)
            return len(rows)
        except Exception as exc:
            logger.error("importDataDB failed: %s", exc)
            self._abstraction.set_status(ProcessingStatus.FAILED)
            return None
 
    # -----------------------------------------------------------------------
    # UML: sendToController(SensorData) → boolean
    # -----------------------------------------------------------------------
 
    async def send_to_controller(self, sensor_data: SensorDataSchema) -> bool:
        payload = {
            "sensor_data": {
                "sensor_id":       sensor_data.sensor_id,
                "geographic_zone": sensor_data.geographic_zone,
                "recorded_at":     sensor_data.recorded_at.isoformat(),
                "timestamp":       sensor_data.recorded_at.isoformat(),
                "region":          sensor_data.geographic_zone,
                "gps_location":    "",
                "source_id":       sensor_data.sensor_id,
                "metrics": [
                    {
                        "metric_type": r.metric_type.value,
                        "value":       r.metric_value,
                        "unit":        r.unit,
                    }
                    for r in sensor_data.readings
                ],
            },
            "source_service": "data_processing",
        }
        try:
            resp = await self._http_client.post(
                f"{self._city_url}/api/v1/data/inbound", json=payload
            )
            resp.raise_for_status()
            self._abstraction.set_status(ProcessingStatus.FORWARDED)
            logger.info(
                "SensorData forwarded to City agent: sensor_id=%s zone=%s",
                sensor_data.sensor_id, sensor_data.geographic_zone,
            )
            return True
        except httpx.RequestError as exc:
            logger.error("sendToController failed (network): %s", exc)
            return False
        except httpx.HTTPStatusError as exc:
            logger.error("sendToController failed (HTTP %s): %s", exc.response.status_code, exc)
            return False
 
    # -----------------------------------------------------------------------
    # Full pipeline
    # -----------------------------------------------------------------------
 
    async def run_pipeline(self, raw_payload: RawSensorPayload) -> PipelineResult:
        self._abstraction.set_status(ProcessingStatus.RECEIVED)
        normalised = self._external.send_raw_JSON(raw_payload)
 
        self._abstraction.set_status(ProcessingStatus.PROCESSING)
        try:
            sensor_data = self.process_json_data(normalised)
        except ValueError as exc:
            result = PipelineResult(
                source_id=raw_payload.source_id,
                status=ProcessingStatus.FAILED,
                validation_errors=str(exc).split("; "),
                message="Payload failed validation in processJSONData.",
            )
            self._abstraction.record_result(result)
            return result
 
        rows_inserted = await self.import_data_db(sensor_data)
        if rows_inserted is None:
            result = PipelineResult(
                source_id=raw_payload.source_id,
                status=ProcessingStatus.FAILED,
                message="importDataDB failed — data not persisted.",
            )
            self._abstraction.record_result(result)
            return result
 
        forwarded = await self.send_to_controller(sensor_data)
        result = PipelineResult(
            source_id=raw_payload.source_id,
            status=ProcessingStatus.FORWARDED if forwarded else ProcessingStatus.STORED,
            rows_inserted=rows_inserted,
            forwarded_to_city=forwarded,
            message=(
                f"Pipeline complete. {rows_inserted} row(s) stored."
                + (" Forwarded to City agent." if forwarded else "")
            ),
        )
        self._abstraction.record_result(result)
        return result
 
    # -----------------------------------------------------------------------
    # Abstraction accessors
    # -----------------------------------------------------------------------
 
    def get_latest_sensor_data(self) -> Optional[SensorDataSchema]:
        return self._abstraction.get_latest_sensor_data()
 
    def get_pipeline_status(self) -> ProcessingStatus:
        return self._abstraction.get_status()
 
    def get_recent_results(self, limit: int = 20) -> List[PipelineResult]:
        return self._abstraction.get_recent_results(limit)
 
    def get_result_by_source(self, source_id: str) -> Optional[PipelineResult]:
        return self._abstraction.get_result_by_source(source_id)
 
    # -----------------------------------------------------------------------
    # Database passthroughs
    # -----------------------------------------------------------------------
 
    async def query_database(
        self, params: SensorDatabaseQueryParams
    ) -> SensorDatabaseQueryResponse:
        return await self._database.query(params)
 
    async def get_sensor_metadata(
        self, sensor_id: str
    ) -> Optional[SensorMetadataSchema]:
        row = await self._database.get_sensor_metadata(sensor_id)
        return _metadata_row_to_schema(row) if row else None
 
    async def get_all_metadata(self) -> List[SensorMetadataSchema]:
        rows = await self._database.get_all_metadata()
        return [_metadata_row_to_schema(r) for r in rows]
 
    # -----------------------------------------------------------------------
    # Location — now from SensorMetadata
    # -----------------------------------------------------------------------
 
    async def get_location(
        self, sensor_id: Optional[str] = None, geographic_zone: Optional[str] = None
    ) -> Optional[LocationResponse]:
        if sensor_id:
            row = await self._database.get_sensor_metadata(sensor_id)
            if row:
                return _metadata_to_location(row)
            return None
 
        # Fall back to first sensor in requested zone
        if geographic_zone:
            rows = await self._database.get_all_metadata()
            for row in rows:
                if row.geographic_zone == geographic_zone:
                    return _metadata_to_location(row)
 
        # Fall back to latest abstraction data
        latest = self._abstraction.get_latest_sensor_data()
        if latest:
            row = await self._database.get_sensor_metadata(latest.sensor_id)
            if row:
                return _metadata_to_location(row)
 
        return None
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _row_to_reading(row: TimeSeriesSensorData) -> TimeSeriesReadingSchema:
    return TimeSeriesReadingSchema(
        data_id=row.data_id,
        sensor_id=row.sensor_id,
        metric_type=MetricType(row.metric_type),
        metric_value=row.metric_value,
        unit=row.unit,
        recorded_at=row.recorded_at,
        geographic_zone=row.geographic_zone,
        data_quality_flag=DataQualityFlag(row.data_quality_flag or "valid"),
        additional_metadata=row.additional_metadata,
        ingested_at=row.ingested_at,
    )
 
 
def _metadata_row_to_schema(row: SensorMetadata) -> SensorMetadataSchema:
    return SensorMetadataSchema(
        sensor_id=row.sensor_id,
        sensor_name=row.sensor_name,
        geographic_zone=row.geographic_zone,
        latitude=row.latitude,
        longitude=row.longitude,
        sensor_type=row.sensor_type,
        location_description=row.location_description,
        installation_date=row.installation_date,
        is_active=row.is_active or True,
        last_maintenance=row.last_maintenance,
        manufacturer=row.manufacturer,
        model=row.model,
        created_at=row.created_at,
    )
 
 
def _metadata_to_location(row: SensorMetadata) -> LocationResponse:
    return LocationResponse(
        sensor_id=row.sensor_id,
        sensor_name=row.sensor_name,
        geographic_zone=row.geographic_zone,
        latitude=row.latitude,
        longitude=row.longitude,
    )
 
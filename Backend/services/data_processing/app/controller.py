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
from typing import Any, Dict, List, Optional

import httpx

from app.abstraction import DataAbstraction
from app.models import (
    AirQualitySchema,
    HumiditySchema,
    LocationResponse,
    NoiseLevelSchema,
    ParticulateMatterSchema,
    PipelineResult,
    ProcessingStatus,
    RawSensorPayload,
    SensorDataSchema,
    SensorDatabaseQueryParams,
    SensorDatabaseQueryResponse,
    SensorDatabaseRecord,
    SensorMetricSchema,
    SensorMetricType,
    SuccessResponse,
    TemperatureSchema,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric type → schema class mapping
# Used by processJSONData to instantiate the correct SensorMetrics subclass
# ---------------------------------------------------------------------------

_METRIC_SCHEMA_MAP: Dict[str, type] = {
    SensorMetricType.TEMPERATURE: TemperatureSchema,
    SensorMetricType.HUMIDITY: HumiditySchema,
    SensorMetricType.PARTICULATE_MATTER: ParticulateMatterSchema,
    SensorMetricType.AIR_QUALITY: AirQualitySchema,
    SensorMetricType.NOISE_LEVEL: NoiseLevelSchema,
}


# ---------------------------------------------------------------------------
# ExternalSensorData
# Models the sensor-side data collection described in the UML.
# In production this class would manage connections to physical sensors
# or an IoT gateway. Here it validates and normalises the raw payload
# before handing it to DataProcessing.
# ---------------------------------------------------------------------------

class ExternalSensorData:
    """
    Represents the external sensor data source.

    UML methods:
      collect_data_from_sensors() -> JSON
      send_raw_JSON(JSON)         -> None

    In this microservice the sensors POST directly to the /sensor/ingest
    endpoint, so collect_data_from_sensors() is a passive receive rather
    than an active poll. send_raw_JSON() is modelled as the normalisation
    step before the data enters the processing pipeline.
    """

    def collect_data_from_sensors(self) -> Dict[str, Any]:
        """
        Active collection — would poll sensor hardware or an IoT broker
        (e.g. MQTT) in a real implementation.
        Raises NotImplementedError until the sensor integration is built.
        """
        raise NotImplementedError(
            "Active sensor polling is not yet implemented. "
            "Sensors should POST directly to /api/v1/sensor/ingest."
        )

    def send_raw_JSON(self, raw_payload: RawSensorPayload) -> RawSensorPayload:
        """
        Normalise the incoming raw payload before pipeline processing.
        Currently a pass-through; add vendor-specific transformation here.
        """
        return raw_payload


# ---------------------------------------------------------------------------
# SensorDatabase
# Thin persistence abstraction — replace method bodies with real DB calls
# (SQLAlchemy async, asyncpg, etc.) once the database is wired in.
# ---------------------------------------------------------------------------

class SensorDatabase:
    """
    Persistence layer for processed SensorData.

    UML attributes / methods:
      + SensorData: SensorData
      + importData(SensorData): boolean
    """

    def __init__(self):
        # In-memory store — replace with DB session in production
        self._records: Dict[str, SensorDatabaseRecord] = {}

    async def import_data(self, sensor_data: SensorDataSchema) -> SensorDatabaseRecord:
        """
        Persist a SensorData object and return the resulting record.
        Raises RuntimeError on failure (caller maps this to a False return
        as described in the UML boolean return type).
        """
        record_id = f"rec-{uuid.uuid4().hex[:8]}"
        stored_at = datetime.now(timezone.utc).isoformat()

        record = SensorDatabaseRecord(
            record_id=record_id,
            stored_at=stored_at,
            sensor_data=sensor_data,
        )

        # TODO: replace with async DB insert, e.g.:
        # async with db_session() as session:
        #     session.add(SensorDataORM.from_schema(record))
        #     await session.commit()
        self._records[record_id] = record

        logger.info(
            "SensorData stored: record_id=%s region=%s timestamp=%s",
            record_id,
            sensor_data.region,
            sensor_data.timestamp,
        )
        return record

    async def query(
        self, params: SensorDatabaseQueryParams
    ) -> SensorDatabaseQueryResponse:
        """
        Retrieve historical records matching the given filters.
        TODO: replace with parameterised DB query.
        """
        results = list(self._records.values())

        if params.region:
            results = [
                r for r in results if r.sensor_data.region == params.region
            ]
        if params.metric_type:
            results = [
                r for r in results
                if any(
                    m.metric_type == params.metric_type
                    for m in r.sensor_data.metrics
                )
            ]
        # Timestamp filtering omitted for brevity — add date parsing here
        results = results[: params.limit]

        return SensorDatabaseQueryResponse(records=results, total=len(results))

    async def get_record(self, record_id: str) -> Optional[SensorDatabaseRecord]:
        return self._records.get(record_id)


# ---------------------------------------------------------------------------
# DataProcessingController — Control layer
# ---------------------------------------------------------------------------

class DataProcessingController:
    """
    Control layer of the Data Processing PAC Agent.

    Core UML responsibilities:
      processJSONData(JSONData: dict)  -> SensorData
      importDataDB(SensorData)         -> boolean
      sendToController(SensorData)     -> boolean   (to City agent)

    Orchestrates the full pipeline and keeps the DataAbstraction layer
    up to date so that status / query routes always have fresh data.
    """

    def __init__(self, city_service_url: str):
        self._city_url = city_service_url

        # PAC layers
        self._abstraction = DataAbstraction()
        self._external = ExternalSensorData()
        self._database = SensorDatabase()

        # Shared async HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    async def initialise(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("DataProcessingController initialised.")

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        logger.info("DataProcessingController shut down.")

    # -----------------------------------------------------------------------
    # Core UML method 1: processJSONData(JSONData) -> SensorData
    # -----------------------------------------------------------------------

    def process_json_data(self, raw_payload: RawSensorPayload) -> SensorDataSchema:
        """
        Parse and validate a raw sensor JSON payload into a structured
        SensorData object.

        Raises ValueError with descriptive messages if the payload does
        not conform to the expected schema — callers should catch this and
        mark the pipeline result as FAILED.
        """
        data = raw_payload.sensor_data
        errors: List[str] = []

        # --- Required top-level fields ---
        timestamp = data.get("timestamp")
        region = data.get("region")
        gps_location = data.get("gps_location")
        raw_metrics = data.get("metrics", [])

        if not timestamp:
            errors.append("Missing field: 'timestamp'")
        if not region:
            errors.append("Missing field: 'region'")
        if not gps_location:
            errors.append("Missing field: 'gps_location'")
        if not raw_metrics:
            errors.append("Missing or empty field: 'metrics'")

        if errors:
            raise ValueError(f"Invalid sensor payload: {'; '.join(errors)}")

        # --- Parse metrics ---
        parsed_metrics: List[SensorMetricSchema] = []
        for i, raw_metric in enumerate(raw_metrics):
            raw_type = raw_metric.get("type") or raw_metric.get("metric_type")
            value = raw_metric.get("value")
            unit = raw_metric.get("unit", "")

            if raw_type is None or value is None:
                errors.append(
                    f"Metric[{i}]: missing 'type' or 'value'."
                )
                continue

            # Normalise type string to enum
            try:
                metric_type = SensorMetricType(raw_type)
            except ValueError:
                errors.append(
                    f"Metric[{i}]: unknown metric type '{raw_type}'. "
                    f"Valid types: {[e.value for e in SensorMetricType]}"
                )
                continue

            # Instantiate the correct subclass
            schema_cls = _METRIC_SCHEMA_MAP.get(metric_type, SensorMetricSchema)
            parsed_metrics.append(
                schema_cls(metric_type=metric_type, value=float(value), unit=unit)
            )

        if errors:
            raise ValueError(f"Metric parsing errors: {'; '.join(errors)}")

        return SensorDataSchema(
            timestamp=timestamp,
            region=region,
            gps_location=gps_location,
            source_id=raw_payload.source_id,
            metrics=parsed_metrics,
        )

    # -----------------------------------------------------------------------
    # Core UML method 2: importDataDB(SensorData) -> boolean
    # -----------------------------------------------------------------------

    async def import_data_db(
        self, sensor_data: SensorDataSchema
    ) -> Optional[SensorDatabaseRecord]:
        """
        Persist processed SensorData to the SensorDatabase.
        Returns the resulting SensorDatabaseRecord on success, or None on
        failure (maps to the UML boolean return — None == False).
        """
        try:
            record = await self._database.import_data(sensor_data)
            self._abstraction.set_latest_sensor_data(sensor_data, record)
            self._abstraction.set_status(ProcessingStatus.STORED)
            return record
        except Exception as exc:
            logger.error("importDataDB failed: %s", exc)
            self._abstraction.set_status(ProcessingStatus.FAILED)
            return None

    # -----------------------------------------------------------------------
    # Core UML method 3: sendToController(SensorData) -> boolean
    # -----------------------------------------------------------------------

    async def send_to_controller(self, sensor_data: SensorDataSchema) -> bool:
        """
        Forward processed SensorData to the City agent via HTTP POST.
        Returns True on success, False on failure.
        """
        if not self._http_client:
            logger.error("HTTP client not initialised — cannot forward data.")
            return False

        payload = {
            "sensor_data": sensor_data.model_dump(),
            "source_service": "data_processing",
        }

        try:
            response = await self._http_client.post(
                f"{self._city_url}/api/v1/data/inbound",
                json=payload,
            )
            response.raise_for_status()
            self._abstraction.set_status(ProcessingStatus.FORWARDED)
            logger.info(
                "SensorData forwarded to City agent: region=%s timestamp=%s",
                sensor_data.region,
                sensor_data.timestamp,
            )
            return True
        except httpx.RequestError as exc:
            logger.error("sendToController failed (network error): %s", exc)
            return False
        except httpx.HTTPStatusError as exc:
            logger.error(
                "sendToController failed (HTTP %s): %s",
                exc.response.status_code,
                exc,
            )
            return False

    # -----------------------------------------------------------------------
    # Full pipeline orchestration
    # Ties together all three UML methods into one atomic operation.
    # Called by the /sensor/ingest route.
    # -----------------------------------------------------------------------

    async def run_pipeline(self, raw_payload: RawSensorPayload) -> PipelineResult:
        """
        Execute the full data processing pipeline for one sensor payload:
          1. ExternalSensorData.send_raw_JSON() — normalise raw input
          2. processJSONData()                  — parse → SensorData
          3. importDataDB()                     — persist to SensorDatabase
          4. sendToController()                 — forward to City agent

        Returns a PipelineResult describing the outcome of each stage.
        """
        self._abstraction.set_status(ProcessingStatus.RECEIVED)

        # Stage 1 — normalise
        normalised = self._external.send_raw_JSON(raw_payload)

        # Stage 2 — parse
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

        # Stage 3 — persist
        record = await self.import_data_db(sensor_data)
        if record is None:
            result = PipelineResult(
                source_id=raw_payload.source_id,
                status=ProcessingStatus.FAILED,
                message="importDataDB failed — sensor data not persisted.",
            )
            self._abstraction.record_result(result)
            return result

        # Stage 4 — forward
        forwarded = await self.send_to_controller(sensor_data)

        result = PipelineResult(
            source_id=raw_payload.source_id,
            status=ProcessingStatus.FORWARDED if forwarded else ProcessingStatus.STORED,
            record_id=record.record_id,
            forwarded_to_city=forwarded,
            message=(
                "Pipeline completed successfully."
                if forwarded
                else "Data stored but forwarding to City agent failed."
            ),
        )
        self._abstraction.record_result(result)
        return result

    # -----------------------------------------------------------------------
    # Abstraction layer accessors (used by routes)
    # -----------------------------------------------------------------------

    def get_latest_sensor_data(self) -> Optional[SensorDataSchema]:
        return self._abstraction.get_latest_sensor_data()

    def get_latest_record(self) -> Optional[SensorDatabaseRecord]:
        return self._abstraction.get_latest_record()

    def get_pipeline_status(self) -> ProcessingStatus:
        return self._abstraction.get_status()

    def get_recent_results(self, limit: int = 20) -> List[PipelineResult]:
        return self._abstraction.get_recent_results(limit)

    def get_result_by_source(self, source_id: str) -> Optional[PipelineResult]:
        return self._abstraction.get_result_by_source(source_id)

    # -----------------------------------------------------------------------
    # SensorDatabase query passthrough (used by routes)
    # -----------------------------------------------------------------------

    async def query_database(
        self, params: SensorDatabaseQueryParams
    ) -> SensorDatabaseQueryResponse:
        return await self._database.query(params)

    async def get_record(self, record_id: str) -> Optional[SensorDatabaseRecord]:
        return await self._database.get_record(record_id)

    # -----------------------------------------------------------------------
    # Location
    # -----------------------------------------------------------------------

    def get_location(self, region: Optional[str] = None) -> Optional[LocationResponse]:
        """
        Return location data from the most recently processed SensorData.
        If region is specified, only return a match if the cached data is
        for that region.
        """
        data = self._abstraction.get_latest_sensor_data()
        if data is None:
            return None
        if region and data.region != region:
            return None
        return LocationResponse(
            region=data.region,
            gps_location=data.gps_location,
        )
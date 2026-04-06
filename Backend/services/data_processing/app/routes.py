"""
Data Processing Agent Service — Routes
All API endpoints exposed by the Data Processing Agent.

Route groups:
  /sensor          — raw sensor data ingestion (ExternalSensorData entry point)
  /pipeline        — pipeline status and recent result log
  /data            — structured SensorData queries (abstraction layer)
  /database        — SensorDatabase historical record queries
  /location        — location data derived from latest sensor readings
"""

from __future__ import annotations

from typing import List, Optional

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controller import DataProcessingController
from app.dependencies import get_data_processing_controller
from app.models import (
    LocationResponse,
    PipelineResult,
    ProcessingStatus,
    RawSensorPayload,
    SensorDataSchema,
    SensorDatabaseQueryParams,
    SensorDatabaseQueryResponse,
    SuccessResponse,
    DataQualityFlag,
    MetricType
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Sensor ingestion — ExternalSensorData entry point
# This is where physical sensors / IoT gateways POST their raw data.
# Triggers the full pipeline: processJSONData → importDataDB → sendToController
# ---------------------------------------------------------------------------

@router.post(
    "/sensor/ingest",
    response_model=PipelineResult,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Sensor Ingestion"],
    summary="Ingest raw sensor data (full pipeline)",
    description=(
        "Primary ingestion endpoint for physical sensors and IoT gateways "
        "(ExternalSensorData.send_raw_JSON). Triggers the full pipeline: "
        "parse → validate → store in SensorDatabase → forward to City agent. "
        "Returns a PipelineResult describing the outcome of each stage."
    ),
)
async def ingest_sensor_data(
    payload: RawSensorPayload,
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> PipelineResult:
    return await controller.run_pipeline(payload)


@router.post(
    "/sensor/process",
    response_model=SensorDataSchema,
    status_code=status.HTTP_200_OK,
    tags=["Sensor Ingestion"],
    summary="Parse and validate raw sensor JSON (processJSONData only)",
    description=(
        "Runs processJSONData() on the supplied raw payload and returns the "
        "resulting SensorData without persisting or forwarding it. Useful for "
        "testing sensor payload formats before going live."
    ),
)
async def process_only(
    payload: RawSensorPayload,
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> SensorDataSchema:
    try:
        return controller.process_json_data(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Pipeline status and result log
# ---------------------------------------------------------------------------

@router.get(
    "/pipeline/status",
    tags=["Pipeline"],
    summary="Get the current pipeline processing status",
    description=(
        "Returns the current ProcessingStatus of the pipeline "
        "(RECEIVED → PROCESSING → STORED → FORWARDED, or FAILED)."
    ),
)
async def get_pipeline_status(
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> dict:
    return {"status": controller.get_pipeline_status().value}


@router.get(
    "/pipeline/results",
    response_model=List[PipelineResult],
    tags=["Pipeline"],
    summary="Get recent pipeline results",
    description=(
        "Returns a rolling log of the most recent pipeline run results, "
        "newest first. Useful for monitoring ingestion health without "
        "querying the full database."
    ),
)
async def get_recent_results(
    limit: int = Query(20, ge=1, le=50, description="Number of results to return."),
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> List[PipelineResult]:
    return controller.get_recent_results(limit=limit)


@router.get(
    "/pipeline/results/{source_id}",
    response_model=PipelineResult,
    tags=["Pipeline"],
    summary="Get the latest pipeline result for a specific sensor",
    description="Returns the most recent PipelineResult for the given sensor source_id.",
)
async def get_result_by_source(
    source_id: str,
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> PipelineResult:
    result = controller.get_result_by_source(source_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pipeline result found for source_id '{source_id}'.",
        )
    return result


# ---------------------------------------------------------------------------
# Structured SensorData — abstraction layer
# Fast reads from the in-memory abstraction cache
# ---------------------------------------------------------------------------

@router.get(
    "/data/latest",
    response_model=SensorDataSchema,
    tags=["Sensor Data"],
    summary="Get the latest processed SensorData",
    description=(
        "Returns the most recently processed and validated SensorData object "
        "from the abstraction layer cache. Does not query the database."
    ),
)
async def get_latest_sensor_data(
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> SensorDataSchema:
    data = controller.get_latest_sensor_data()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sensor data has been processed yet.",
        )
    return data


@router.get(
    "/data/latest/record",
    response_model=SensorDataSchema,
    tags=["Sensor Data"],
    summary="Get the latest SensorDatabase record",
    description=(
        "Returns the SensorDatabaseRecord for the most recently stored "
        "sensor reading, including the database-assigned record_id and "
        "stored_at timestamp."
    ),
)
async def get_latest_record(
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> SensorDataSchema:
    record = controller.get_latest_sensor_data()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No records stored yet.",
        )
    return record


# ---------------------------------------------------------------------------
# SensorDatabase — historical queries
# ---------------------------------------------------------------------------

@router.get(
    "/database/records",
    response_model=SensorDatabaseQueryResponse,
    tags=["Database"],
    summary="Query historical SensorDatabase records",
    description=(
        "Query the SensorDatabase for historical sensor readings. "
        "Supports filtering by region, metric type, and timestamp range."
    ),
)
async def query_database(
    region: Optional[str] = Query(None, example="Downtown"),
    metric_type: Optional[MetricType] = Query(None),
    sensor_id: Optional[str] = None,
    from_timestamp: Optional[datetime] = Query(None, example="2025-06-01T00:00:00Z"),
    to_timestamp: Optional[datetime] = Query(None, example="2025-06-01T23:59:59Z"),
    data_quality_flag: Optional[DataQualityFlag] = None,
    limit: int = Query(100, ge=1, le=1000),
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> SensorDatabaseQueryResponse:
    params = SensorDatabaseQueryParams(
        geographic_zone=region,
        metric_type=metric_type,
        sensor_id=sensor_id,
        from_recorded_at=from_timestamp,
        to_recorded_at=to_timestamp,
        data_quality_flag=data_quality_flag,
        limit=limit,
    )
    return await controller.query_database(params)


@router.get(
    "/database/records/{record_id}",
    response_model=PipelineResult,
    tags=["Database"],
    summary="Get a specific SensorDatabase record by ID",
)
async def get_record(
    record_id: str,
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> PipelineResult:
    record = controller.get_result_by_source(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found.",
        )
    return record


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

@router.get(
    "/location",
    response_model=LocationResponse,
    tags=["Location"],
    summary="Get location data from the latest sensor reading",
    description=(
        "Returns the region and GPS location from the most recently "
        "processed SensorData. Optionally filter by region name. "
        "Called by the City and Public agents as a location fallback."
    ),
)
async def get_location(
    sensor_id: Optional[str] = None, 
    geographic_zone: Optional[str] = None,
    controller: DataProcessingController = Depends(get_data_processing_controller),
) -> LocationResponse:
    location = await controller.get_location(sensor_id=sensor_id, geographic_zone=geographic_zone)
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No location data available"
                + (f" for region '{geographic_zone}'." if geographic_zone else ".")
            ),
        )
    return location
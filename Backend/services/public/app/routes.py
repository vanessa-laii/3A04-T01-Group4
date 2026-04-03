"""
Public Agent Service — Routes
All API endpoints exposed by the Public Agent.

Route groups:
  /observers        — register / remove PublicObservers
  /abstraction      — current approved sensor data (abstraction layer)
  /feed             — PublicAPI snapshot: sensor data + active alerts
  /alerts           — public alert queries and inbound notifications
  /data             — inbound sensor data from the City agent
  /location         — public location queries (requestUserLocation)
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controller import PublicController
from app.dependencies import get_public_controller
from app.models import (
    InboundAlertNotification,
    InboundSensorData,
    LocationRequest,
    LocationResponse,
    ObserverListResponse,
    ObserverRegisterRequest,
    PublicAbstractionSchema,
    PublicAlertSchema,
    PublicAPISnapshot,
    SuccessResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Observer management
# PublicController implements PublicSubject: addObserver / removeObserver
# ---------------------------------------------------------------------------

@router.post(
    "/observers",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Observers"],
    summary="Register a PublicObserver",
    description=(
        "Register a new observer that will receive notifications when the "
        "public sensor data or alert list changes. Provide a callback_url to "
        "receive HTTP POST webhooks (e.g. a third-party app), or omit it to "
        "create a local PublicAPI observer instance."
    ),
)
async def register_observer(
    request: ObserverRegisterRequest,
    controller: PublicController = Depends(get_public_controller),
) -> SuccessResponse:
    return controller.add_observer(request)


@router.delete(
    "/observers/{observer_id}",
    response_model=SuccessResponse,
    tags=["Observers"],
    summary="Remove a PublicObserver",
)
async def remove_observer(
    observer_id: str,
    controller: PublicController = Depends(get_public_controller),
) -> SuccessResponse:
    return controller.remove_observer(observer_id)


@router.get(
    "/observers",
    response_model=ObserverListResponse,
    tags=["Observers"],
    summary="List all registered PublicObservers",
)
async def list_observers(
    controller: PublicController = Depends(get_public_controller),
) -> ObserverListResponse:
    return ObserverListResponse(observers=controller.list_observer_ids())


# ---------------------------------------------------------------------------
# Abstraction layer
# Current approved sensor data held by PublicAbstraction
# ---------------------------------------------------------------------------

@router.get(
    "/abstraction",
    response_model=PublicAbstractionSchema,
    tags=["Abstraction"],
    summary="Get the current public sensor data abstraction",
    description=(
        "Returns the latest approved SensorData snapshot held by "
        "PublicAbstraction. This is the internal abstraction layer view — "
        "most external consumers should use /feed instead."
    ),
)
async def get_abstraction(
    controller: PublicController = Depends(get_public_controller),
) -> PublicAbstractionSchema:
    snapshot = controller.get_abstraction_snapshot()
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No public data available yet.",
        )
    return snapshot


# ---------------------------------------------------------------------------
# PublicAPI feed (Presentation layer)
# The primary endpoint for external consumers — sensor data + active alerts
# ---------------------------------------------------------------------------

@router.get(
    "/feed",
    response_model=PublicAPISnapshot,
    tags=["Feed"],
    summary="Get the full public data feed",
    description=(
        "Primary endpoint for external consumers (citizens, third-party apps). "
        "Returns the current approved sensor data and all active public alerts. "
        "No authentication required."
    ),
)
async def get_public_feed(
    controller: PublicController = Depends(get_public_controller),
) -> PublicAPISnapshot:
    # Use the default PublicAPI observer if one is registered, otherwise
    # build the snapshot directly from the abstraction layer.
    snapshot = controller.get_api_snapshot("default")
    if snapshot is None:
        abstraction = controller.get_abstraction_snapshot()
        if abstraction is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No public data available yet.",
            )
        return PublicAPISnapshot(
            sensor_data=abstraction.sensor_data,
            public_alerts=controller.get_public_alerts(),
        )
    return snapshot


@router.get(
    "/feed/{api_id}",
    response_model=PublicAPISnapshot,
    tags=["Feed"],
    summary="Get the snapshot for a specific PublicAPI observer",
    description=(
        "Returns the current snapshot held by a named PublicAPI observer "
        "instance. Useful when multiple named public feeds are registered."
    ),
)
async def get_api_snapshot(
    api_id: str,
    controller: PublicController = Depends(get_public_controller),
) -> PublicAPISnapshot:
    snapshot = controller.get_api_snapshot(api_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PublicAPI observer '{api_id}' not found.",
        )
    return snapshot


# ---------------------------------------------------------------------------
# Public Alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts",
    response_model=List[PublicAlertSchema],
    tags=["Alerts"],
    summary="Get all active public alerts",
    description=(
        "Returns a list of all currently active alerts that have been approved "
        "for public visibility. Optionally filter by region."
    ),
)
async def get_public_alerts(
    region: Optional[str] = Query(
        None,
        description="Filter alerts by region name.",
        example="Downtown",
    ),
    controller: PublicController = Depends(get_public_controller),
) -> List[PublicAlertSchema]:
    return controller.get_public_alerts(region=region)


@router.post(
    "/alerts/inbound",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Alerts"],
    summary="Receive a public alert from the City agent",
    description=(
        "Internal endpoint called by the City agent to forward publicly "
        "visible alerts. Resolved alerts are removed from the public list; "
        "all others are added or updated."
    ),
)
async def receive_alert(
    notification: InboundAlertNotification,
    controller: PublicController = Depends(get_public_controller),
) -> SuccessResponse:
    return await controller.receive_alert(notification)


# ---------------------------------------------------------------------------
# Inbound sensor data
# Called by the City agent when new approved public sensor data is available
# ---------------------------------------------------------------------------

@router.post(
    "/data/inbound",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Data"],
    summary="Receive approved sensor data from the City agent",
    description=(
        "Internal endpoint called by the City agent. Updates the "
        "PublicAbstraction layer and notifies all registered PublicObservers."
    ),
)
async def receive_sensor_data(
    notification: InboundSensorData,
    controller: PublicController = Depends(get_public_controller),
) -> SuccessResponse:
    return await controller.receive_sensor_data(notification)


# ---------------------------------------------------------------------------
# Location — PublicController.requestUserLocation()
# ---------------------------------------------------------------------------

@router.post(
    "/location",
    response_model=LocationResponse,
    tags=["Location"],
    summary="Request public location data",
    description=(
        "Returns region and GPS data from the current public abstraction "
        "snapshot. Falls back to querying the City agent if no local data "
        "exists yet."
    ),
)
async def request_user_location(
    request: LocationRequest,
    controller: PublicController = Depends(get_public_controller),
) -> LocationResponse:
    try:
        return await controller.request_user_location(region=request.region)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not retrieve location data: {exc}",
        )
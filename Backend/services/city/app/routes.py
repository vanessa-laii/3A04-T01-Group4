"""
City Agent Service — Routes
All API endpoints exposed by the City Agent.

Route groups:
  /health          — liveness / readiness probes
  /observers       — register / remove CityObservers (Observer pattern)
  /dashboard       — city dashboard presentation layer
  /data            — inbound sensor data from DataProcessing agent
  /alerts          — inbound alert notifications from Alerts agent
  /location        — user / region location queries
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.controller import CityController
from app.dependencies import get_city_controller
from app.models import (
    AlertNotification,
    CityAbstractionSchema,
    DashboardLayoutSchema,
    DashboardSchema,
    ErrorResponse,
    LocationRequest,
    LocationResponse,
    ObserverListResponse,
    ObserverRegisterRequest,
    ProcessedDataNotification,
    SuccessResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Observer management
# CityController implements CitySubject: addObserver / removeObserver / notify
# ---------------------------------------------------------------------------

@router.post(
    "/observers",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Observers"],
    summary="Register a CityObserver",
    description=(
        "Register a new observer that will receive push notifications whenever "
        "the city's sensor data is updated.  Supply a callback_url to receive "
        "HTTP POST webhooks (remote observer), or omit it for a local dashboard."
    ),
)
async def register_observer(
    request: ObserverRegisterRequest,
    controller: CityController = Depends(get_city_controller),
) -> SuccessResponse:
    return controller.add_observer(request)


@router.delete(
    "/observers/{observer_id}",
    response_model=SuccessResponse,
    tags=["Observers"],
    summary="Remove a CityObserver",
)
async def remove_observer(
    observer_id: str,
    controller: CityController = Depends(get_city_controller),
) -> SuccessResponse:
    return controller.remove_observer(observer_id)


@router.get(
    "/observers",
    response_model=ObserverListResponse,
    tags=["Observers"],
    summary="List all registered observers",
)
async def list_observers(
    controller: CityController = Depends(get_city_controller),
) -> ObserverListResponse:
    local_ids = [o.dashboard_id for o in controller._observers]
    remote_ids = list(controller._remote_observer_urls.keys())
    return ObserverListResponse(observers=local_ids + remote_ids)


# ---------------------------------------------------------------------------
# City Abstraction layer
# Exposes the current SensorData snapshot held by CityAbstraction
# ---------------------------------------------------------------------------

@router.get(
    "/abstraction",
    response_model=CityAbstractionSchema,
    tags=["Abstraction"],
    summary="Get the current city sensor data abstraction",
    description="Returns the latest SensorData snapshot held by CityAbstraction.",
)
async def get_abstraction(
    controller: CityController = Depends(get_city_controller),
) -> CityAbstractionSchema:
    try:
        return controller.get_abstraction()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )


# ---------------------------------------------------------------------------
# Dashboard (Presentation layer)
# CityDashboard is the concrete CityObserver
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/{dashboard_id}",
    response_model=DashboardSchema,
    tags=["Dashboard"],
    summary="Get a city dashboard snapshot",
    description="Returns the current state of a registered CityDashboard observer.",
)
async def get_dashboard(
    dashboard_id: str,
    controller: CityController = Depends(get_city_controller),
) -> DashboardSchema:
    snapshot = controller.get_dashboard(dashboard_id)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_id}' not found.",
        )
    return snapshot


@router.patch(
    "/dashboard/{dashboard_id}/layout",
    response_model=SuccessResponse,
    tags=["Dashboard"],
    summary="Edit a city dashboard layout",
    description="Update the layout configuration for a specific dashboard (CityDashboard.editLayout).",
)
async def edit_dashboard_layout(
    dashboard_id: str,
    layout: DashboardLayoutSchema,
    controller: CityController = Depends(get_city_controller),
) -> SuccessResponse:
    return controller.edit_dashboard_layout(dashboard_id, layout)


# ---------------------------------------------------------------------------
# Inbound: DataProcessing → CityController
# Called by the data_processing microservice when new data is ready
# ---------------------------------------------------------------------------

@router.post(
    "/data/inbound",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Data"],
    summary="Receive processed sensor data from DataProcessing agent",
    description=(
        "Internal endpoint called by the DataProcessing microservice. "
        "Updates the CityAbstraction layer and notifies all observers."
    ),
)
async def receive_processed_data(
    notification: ProcessedDataNotification,
    controller: CityController = Depends(get_city_controller),
) -> SuccessResponse:
    return await controller.receive_processed_data(notification)


# ---------------------------------------------------------------------------
# Inbound: Alerts → CityController
# Called by the alerts microservice when an alert is triggered
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/inbound",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Alerts"],
    summary="Receive an alert notification from the Alerts agent",
    description=(
        "Internal endpoint called by the Alerts microservice. "
        "If the alert is publicly visible it is forwarded to the Public agent."
    ),
)
async def receive_alert(
    notification: AlertNotification,
    controller: CityController = Depends(get_city_controller),
) -> SuccessResponse:
    return await controller.receive_alert_notification(notification)


# ---------------------------------------------------------------------------
# Location — CityController.getUserLocation()
# ---------------------------------------------------------------------------

@router.post(
    "/location",
    response_model=LocationResponse,
    tags=["Location"],
    summary="Get user / region location data",
    description=(
        "Returns GPS and region data. Reads from the current abstraction "
        "layer snapshot, or proxies to the DataProcessing service if needed."
    ),
)
async def get_user_location(
    request: LocationRequest,
    controller: CityController = Depends(get_city_controller),
) -> LocationResponse:
    try:
        return await controller.get_user_location(region=request.region)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not retrieve location data: {exc}",
        )
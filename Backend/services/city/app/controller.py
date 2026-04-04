"""
City Agent Service — CityController
PAC Architecture: Control layer of the City Agent.

CityController implements CitySubject (Observer pattern) and is the central
coordinator for the smart city system.  It holds references to all
sub-agents and maintains a list of registered CityObservers (dashboards).

Inter-service communication is done via HTTP using httpx so that each
sub-agent (accounts, data_processing, alerts, public) remains independently
deployable as its own microservice.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.orm_models import AccountInfoORM, AuditLogORM


import httpx

from app.models import (
    AlertNotification,
    CityAbstractionSchema,
    DashboardLayoutSchema,
    DashboardSchema,
    LocationResponse,
    ObserverRegisterRequest,
    ProcessedDataNotification,
    SensorDataSchema,
    SuccessResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CityAbstraction
# Presentation-Abstraction-Control: Abstraction layer of the City Agent.
# Holds the current SensorData snapshot exposed to the presentation layer.
# ---------------------------------------------------------------------------

class CityAbstraction:
    """Wraps SensorData and exposes it to the dashboard / presentation layer."""

    def __init__(self, sensor_data: Optional[SensorDataSchema] = None):
        self._data: Optional[SensorDataSchema] = sensor_data

    def update_data(self, sensor_data: SensorDataSchema) -> None:
        self._data = sensor_data

    def get_data(self) -> Optional[SensorDataSchema]:
        return self._data


# ---------------------------------------------------------------------------
# CityDashboard — concrete CityObserver
# ---------------------------------------------------------------------------

class CityDashboard:
    """
    Presentation layer of the City Agent.
    Receives update notifications from CityController and holds the
    current rendered state of the dashboard.
    """

    def __init__(self, dashboard_id: str):
        self.dashboard_id = dashboard_id
        self._sensor_data: Optional[SensorDataSchema] = None
        self._layout_config: Optional[dict] = None

    # CityObserver interface
    def update(self, sensor_data: SensorDataSchema) -> None:
        """Called by CityController.notify_observers()."""
        self._sensor_data = sensor_data
        logger.info("Dashboard %s updated with new sensor data.", self.dashboard_id)

    def edit_layout(self, layout: DashboardLayoutSchema) -> None:
        self._layout_config = layout.layout_config
        logger.info("Dashboard %s layout updated.", self.dashboard_id)

    def get_snapshot(self) -> DashboardSchema:
        return DashboardSchema(
            sensor_data=self._sensor_data,
            layout_config=self._layout_config,
        )


# ---------------------------------------------------------------------------
# CityController — CitySubject
# ---------------------------------------------------------------------------

class CityController:
    """
    Top-level PAC Control agent.

    Responsibilities:
    - Maintain the list of CityObservers and notify them on data changes.
    - Delegate account operations to the Accounts microservice.
    - Delegate data ingestion to the DataProcessing microservice.
    - Delegate alert management to the Alerts microservice.
    - Delegate public-facing operations to the Public microservice.
    - Keep the CityAbstraction layer up to date.
    """

    def __init__(
        self,
        accounts_service_url: str,
        data_processing_service_url: str,
        alerts_service_url: str,
        public_service_url: str,
        session: AsyncSession,
    ):
        # Sub-agent service URLs
        self._accounts_url = accounts_service_url
        self._data_processing_url = data_processing_service_url
        self._alerts_url = alerts_service_url
        self._public_url = public_service_url

        # Observer pattern — registered dashboards / remote observers
        self._observers: List[CityDashboard] = []
        self._remote_observer_urls: dict[str, str] = {}  # id -> callback_url

        # Abstraction layer
        self._abstraction: CityAbstraction = CityAbstraction()

        # HTTP client (shared, kept open for the service lifetime)
        self._http_client: Optional[httpx.AsyncClient] = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def initialise(self) -> None:
        """Called once at startup (from main.py lifespan)."""
        self._http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("CityController initialised.")

    def shutdown(self) -> None:
        """Called once at shutdown (from main.py lifespan)."""
        if self._http_client:
            import asyncio
            asyncio.get_event_loop().run_until_complete(self._http_client.aclose())
        logger.info("CityController shut down.")

    # -----------------------------------------------------------------------
    # CitySubject — Observer pattern
    # -----------------------------------------------------------------------

    def add_observer(self, request: ObserverRegisterRequest) -> SuccessResponse:
        """
        Register a new observer.
        - If callback_url is provided the observer is remote (another service
          or the webapp) and will receive HTTP POST notifications.
        - Otherwise a local CityDashboard instance is created.
        """
        observer_id = request.observer_id

        if request.callback_url:
            self._remote_observer_urls[observer_id] = request.callback_url
            logger.info("Remote observer registered: %s", observer_id)
        else:
            existing_ids = [o.dashboard_id for o in self._observers]
            if observer_id not in existing_ids:
                self._observers.append(CityDashboard(observer_id))
                logger.info("Local dashboard observer registered: %s", observer_id)

        return SuccessResponse(success=True, message=f"Observer {observer_id} registered.")

    def remove_observer(self, observer_id: str) -> SuccessResponse:
        self._observers = [o for o in self._observers if o.dashboard_id != observer_id]
        self._remote_observer_urls.pop(observer_id, None)
        return SuccessResponse(success=True, message=f"Observer {observer_id} removed.")

    async def notify_observers(self, sensor_data: SensorDataSchema) -> None:
        """Push updated sensor data to all registered observers."""
        # Local observers
        for observer in self._observers:
            observer.update(sensor_data)

        # Remote observers (fire-and-forget HTTP POST)
        if self._http_client:
            for obs_id, url in self._remote_observer_urls.items():
                try:
                    await self._http_client.post(
                        url,
                        json=sensor_data.model_dump(),
                    )
                    logger.info("Notified remote observer %s at %s", obs_id, url)
                except httpx.RequestError as exc:
                    logger.warning(
                        "Failed to notify remote observer %s: %s", obs_id, exc
                    )

    # -----------------------------------------------------------------------
    # Abstraction layer
    # -----------------------------------------------------------------------

    def get_abstraction(self) -> CityAbstractionSchema:
        data = self._abstraction.get_data()
        if data is None:
            raise ValueError("No sensor data available yet.")
        return CityAbstractionSchema(sensor_data=data)

    def _update_abstraction(self, sensor_data: SensorDataSchema) -> None:
        self._abstraction.update_data(sensor_data)

    # -----------------------------------------------------------------------
    # Dashboard management (presentation layer helpers)
    # -----------------------------------------------------------------------

    def get_dashboard(self, dashboard_id: str) -> Optional[DashboardSchema]:
        for obs in self._observers:
            if obs.dashboard_id == dashboard_id:
                return obs.get_snapshot()
        return None

    def edit_dashboard_layout(
        self, dashboard_id: str, layout: DashboardLayoutSchema
    ) -> SuccessResponse:
        for obs in self._observers:
            if obs.dashboard_id == dashboard_id:
                obs.edit_layout(layout)
                return SuccessResponse(success=True, message="Layout updated.")
        return SuccessResponse(success=False, message=f"Dashboard {dashboard_id} not found.")

    # -----------------------------------------------------------------------
    # Inbound: DataProcessing service → CityController
    # Called when the data_processing service has new sensor data ready.
    # -----------------------------------------------------------------------

    async def receive_processed_data(
        self, notification: ProcessedDataNotification
    ) -> SuccessResponse:
        """
        Entry point for new sensor data arriving from the DataProcessing agent.
        Updates the abstraction layer and fans out to all observers.
        """
        sensor_data = notification.sensor_data
        self._update_abstraction(sensor_data)
        await self.notify_observers(sensor_data)
        logger.info(
            "Received and distributed sensor data for region '%s'.",
            sensor_data.region,
        )
        return SuccessResponse(success=True, message="Sensor data processed and observers notified.")

    # -----------------------------------------------------------------------
    # Inbound: Alerts service → CityController
    # -----------------------------------------------------------------------

    async def receive_alert_notification(
        self, notification: AlertNotification
    ) -> SuccessResponse:
        """
        Entry point for alert notifications from the Alerts agent.
        If the alert is publicly visible, forward to the Public service.
        """
        logger.warning(
            "Alert received: id=%s severity=%s region=%s",
            notification.alert_id,
            notification.severity,
            notification.region,
        )

        if notification.publicly_visible and self._http_client:
            try:
                await self._http_client.post(
                    f"{self._public_url}/api/v1/alerts/inbound",
                    json=notification.model_dump(),
                )
            except httpx.RequestError as exc:
                logger.warning("Failed to forward alert to Public service: %s", exc)

        return SuccessResponse(success=True, message="Alert received.")

    # -----------------------------------------------------------------------
    # Location
    # -----------------------------------------------------------------------

    async def get_user_location(self, region: Optional[str] = None) -> LocationResponse:
        """
        Retrieves location data for a given region from the DataProcessing
        service, or returns the most recently known location from the
        abstraction layer.
        """
        current_data = self._abstraction.get_data()

        if current_data:
            target_region = region or current_data.region
            if current_data.region == target_region:
                return LocationResponse(
                    region=current_data.region,
                    gps_location=current_data.gps_location,
                )

        # Fall back to querying the DataProcessing service
        if self._http_client:
            params = {"region": region} if region else {}
            try:
                response = await self._http_client.get(
                    f"{self._data_processing_url}/api/v1/location",
                    params=params,
                )
                response.raise_for_status()
                return LocationResponse(**response.json())
            except httpx.RequestError as exc:
                logger.error("Error fetching location from DataProcessing: %s", exc)
                raise

        raise RuntimeError("HTTP client not initialised.")

    # -----------------------------------------------------------------------
    # Delegation helpers — proxy calls to sub-agent services
    # Each method below is a thin pass-through so that routes stay clean.
    # -----------------------------------------------------------------------

    async def _proxy_get(self, base_url: str, path: str, **params) -> dict:
        assert self._http_client, "HTTP client not initialised."
        response = await self._http_client.get(f"{base_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    async def _proxy_post(self, base_url: str, path: str, body: dict) -> dict:
        assert self._http_client, "HTTP client not initialised."
        response = await self._http_client.post(f"{base_url}{path}", json=body)
        response.raise_for_status()
        return response.json()
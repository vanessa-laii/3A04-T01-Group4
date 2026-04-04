"""
Public Agent Service — PublicController
PAC Architecture: Control layer of the Public Agent.

PublicController implements PublicSubject (Observer pattern) and is
responsible for:
- Receiving approved sensor data and public alerts from the City agent.
- Maintaining the PublicAbstraction layer.
- Maintaining the list of PublicObservers (PublicAPI instances and remote
  webhook subscribers) and notifying them on data changes.
- Exposing location data to public consumers.

PublicAPI is the concrete PublicObserver — it holds the current public
snapshot (sensor data + active alerts) and is what external consumers
ultimately query.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.orm_models import AccountInfoORM, AuditLogORM


import httpx

from app.abstraction import PublicAbstraction
from app.models import (
    AlertStatus,
    InboundAlertNotification,
    InboundSensorData,
    LocationResponse,
    ObserverRegisterRequest,
    PublicAbstractionSchema,
    PublicAlertSchema,
    PublicAPISnapshot,
    SensorDataSchema,
    SuccessResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PublicAPI — concrete PublicObserver (Presentation layer)
# ---------------------------------------------------------------------------

class PublicAPI:
    """
    Presentation layer of the Public PAC Agent.
    Concrete implementation of the PublicObserver interface.

    Each registered PublicAPI instance holds its own snapshot of the
    current public-facing sensor data and alerts.  External consumers
    query this layer — not the abstraction or controller directly.
    """

    def __init__(self, api_id: str):
        self.api_id = api_id
        self._sensor_data: Optional[SensorDataSchema] = None
        self._public_alerts: List[PublicAlertSchema] = []

    # PublicObserver interface
    def update(self, snapshot: PublicAPISnapshot) -> None:
        """
        Called by PublicController.notify_observers() whenever approved
        sensor data or a new public alert is received.
        """
        self._sensor_data = snapshot.sensor_data
        self._public_alerts = snapshot.public_alerts
        logger.info("PublicAPI '%s' updated.", self.api_id)

    def get_snapshot(self) -> PublicAPISnapshot:
        return PublicAPISnapshot(
            sensor_data=self._sensor_data,
            public_alerts=self._public_alerts,
        )


# ---------------------------------------------------------------------------
# PublicController — PublicSubject
# ---------------------------------------------------------------------------

class PublicController:
    """
    Control layer of the Public PAC Agent.

    Implements PublicSubject:
      - add_observer()
      - remove_observer()
      - notify_observers()

    All data received here has already been approved for public visibility
    by the City / Alerts agents upstream.
    """

    def __init__(self, city_service_url: str, session: AsyncSession):
        self._city_url = city_service_url

        # Abstraction layer — single instance, owned by the controller
        self._abstraction: PublicAbstraction = PublicAbstraction()

        # Local PublicAPI observers (in-process)
        self._observers: List[PublicAPI] = []

        # Remote observers: observer_id -> callback_url
        self._remote_observer_urls: Dict[str, str] = {}

        # Shared async HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def initialise(self) -> None:
        """Called once at startup from main.py lifespan."""
        self._http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("PublicController initialised.")

    async def shutdown(self) -> None:
        """Called once at shutdown from main.py lifespan."""
        if self._http_client:
            await self._http_client.aclose()
        logger.info("PublicController shut down.")

    # -----------------------------------------------------------------------
    # PublicSubject — Observer pattern
    # -----------------------------------------------------------------------

    def add_observer(self, request: ObserverRegisterRequest) -> SuccessResponse:
        """
        Register a PublicObserver.
        - Remote observers supply a callback_url and receive HTTP POST
          webhooks when data changes.
        - Local observers are PublicAPI instances kept in-process.
        """
        obs_id = request.observer_id

        if request.callback_url:
            self._remote_observer_urls[obs_id] = request.callback_url
            logger.info("Remote PublicObserver registered: %s", obs_id)
        else:
            existing_ids = {o.api_id for o in self._observers}
            if obs_id not in existing_ids:
                self._observers.append(PublicAPI(obs_id))
                logger.info("Local PublicAPI observer registered: %s", obs_id)

        return SuccessResponse(success=True, message=f"Observer '{obs_id}' registered.")

    def remove_observer(self, observer_id: str) -> SuccessResponse:
        self._observers = [o for o in self._observers if o.api_id != observer_id]
        self._remote_observer_urls.pop(observer_id, None)
        return SuccessResponse(success=True, message=f"Observer '{observer_id}' removed.")

    async def notify_observers(self) -> None:
        """
        Build the current public snapshot from the abstraction layer and
        push it to all registered PublicObservers.
        """
        alerts = self._abstraction.get_alerts()
        sensor_data = self._abstraction.get_data()

        if sensor_data is None:
            logger.debug("notify_observers called but no sensor data available yet.")
            return

        snapshot = PublicAPISnapshot(
            sensor_data=sensor_data,
            public_alerts=alerts,
        )

        # Local observers
        for observer in self._observers:
            observer.update(snapshot)

        # Remote observers — fire-and-forget HTTP POST
        if self._http_client:
            payload = snapshot.model_dump()
            for obs_id, url in self._remote_observer_urls.items():
                try:
                    await self._http_client.post(url, json=payload)
                    logger.info("Notified remote observer '%s' at %s", obs_id, url)
                except httpx.RequestError as exc:
                    logger.warning(
                        "Failed to notify remote observer '%s': %s", obs_id, exc
                    )

    # -----------------------------------------------------------------------
    # Abstraction layer access
    # -----------------------------------------------------------------------

    def get_abstraction_snapshot(self) -> Optional[PublicAbstractionSchema]:
        return self._abstraction.get_snapshot()

    def get_public_alerts(self, region: Optional[str] = None) -> List[PublicAlertSchema]:
        if region:
            return self._abstraction.get_alerts_for_region(region)
        return self._abstraction.get_alerts()

    # -----------------------------------------------------------------------
    # PublicAPI (presentation layer) helpers
    # -----------------------------------------------------------------------

    def get_api_snapshot(self, api_id: str) -> Optional[PublicAPISnapshot]:
        for obs in self._observers:
            if obs.api_id == api_id:
                return obs.get_snapshot()
        return None

    def list_observer_ids(self) -> List[str]:
        local = [o.api_id for o in self._observers]
        remote = list(self._remote_observer_urls.keys())
        return local + remote

    # -----------------------------------------------------------------------
    # Inbound: City agent → PublicController (sensor data)
    # -----------------------------------------------------------------------

    async def receive_sensor_data(
        self, notification: InboundSensorData
    ) -> SuccessResponse:
        """
        Entry point for approved public sensor data arriving from the
        City agent.  Updates the abstraction layer and notifies observers.
        """
        self._abstraction.update_data(notification.sensor_data)
        await self.notify_observers()
        logger.info(
            "Received public sensor data for region '%s'.",
            notification.sensor_data.region,
        )
        return SuccessResponse(
            success=True,
            message="Sensor data received and observers notified.",
        )

    # -----------------------------------------------------------------------
    # Inbound: City agent → PublicController (alerts)
    # -----------------------------------------------------------------------

    async def receive_alert(
        self, notification: InboundAlertNotification
    ) -> SuccessResponse:
        """
        Entry point for publicly visible alerts forwarded by the City agent.
        Adds or updates the alert in the abstraction layer, then notifies
        observers.  If the alert is resolved it is removed from the list.
        """
        if notification.status == AlertStatus.RESOLVED:
            removed = self._abstraction.remove_alert(notification.alert_id)
            logger.info(
                "Alert '%s' resolved and %s.",
                notification.alert_id,
                "removed" if removed else "was not present",
            )
        else:
            alert = PublicAlertSchema(
                alert_id=notification.alert_id,
                severity=notification.severity,
                status=notification.status,
                region=notification.region,
                environmental_type=notification.environmental_type,
                description=(
                    f"{notification.environmental_type.replace('_', ' ').title()} "
                    f"threshold of {notification.threshold} exceeded in "
                    f"{notification.region}."
                ),
                time=notification.time,
            )
            self._abstraction.add_alert(alert)
            logger.warning(
                "Public alert added: id=%s severity=%s region=%s",
                notification.alert_id,
                notification.severity,
                notification.region,
            )

        await self.notify_observers()
        return SuccessResponse(success=True, message="Alert received and processed.")

    # -----------------------------------------------------------------------
    # Location — requestUserLocation()
    # -----------------------------------------------------------------------

    async def request_user_location(
        self, region: Optional[str] = None
    ) -> LocationResponse:
        """
        Returns location data from the current abstraction snapshot.
        Falls back to querying the City service if no local data exists.
        """
        current_data = self._abstraction.get_data()

        if current_data:
            target = region or current_data.region
            if current_data.region == target:
                return LocationResponse(
                    region=current_data.region,
                    gps_location=current_data.gps_location,
                )

        # Fallback — ask the City service
        if self._http_client:
            try:
                response = await self._http_client.post(
                    f"{self._city_url}/api/v1/location",
                    json={"region": region},
                )
                response.raise_for_status()
                return LocationResponse(**response.json())
            except httpx.RequestError as exc:
                logger.error(
                    "Error fetching location from City service: %s", exc
                )
                raise

        raise RuntimeError("HTTP client not initialised.")
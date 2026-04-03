"""
Public Agent Service — PublicAbstraction
PAC Architecture: Abstraction layer of the Public Agent.

PublicAbstraction sits between the PublicController (control) and the
PublicAPI (presentation).  It holds the current approved sensor data
and the list of publicly visible alerts, and is the single source of
truth for what this agent exposes externally.

Keeping this as a separate module (rather than inlining it into the
controller) makes the PAC separation explicit and mirrors the UML design.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.models import (
    PublicAbstractionSchema,
    PublicAlertSchema,
    SensorDataSchema,
)


class PublicAbstraction:
    """
    Abstraction layer of the Public PAC Agent.

    Responsibilities:
    - Hold the most recently approved SensorData snapshot.
    - Maintain a list of currently active public alerts.
    - Provide a clean schema-validated view of both to the presentation layer.
    """

    def __init__(self):
        self._sensor_data: Optional[SensorDataSchema] = None
        self._public_alerts: List[PublicAlertSchema] = []
        self._last_updated: Optional[str] = None

    # -----------------------------------------------------------------------
    # Sensor data
    # -----------------------------------------------------------------------

    def update_data(self, sensor_data: SensorDataSchema) -> None:
        """
        Called by PublicController when the City agent pushes new
        approved sensor data.
        """
        self._sensor_data = sensor_data
        self._last_updated = datetime.now(timezone.utc).isoformat()

    def get_data(self) -> Optional[SensorDataSchema]:
        return self._sensor_data

    # -----------------------------------------------------------------------
    # Public alerts
    # -----------------------------------------------------------------------

    def add_alert(self, alert: PublicAlertSchema) -> None:
        """
        Add or update an alert in the public-facing alert list.
        If an alert with the same alert_id already exists it is replaced
        so the list never has duplicate IDs.
        """
        self._public_alerts = [
            a for a in self._public_alerts if a.alert_id != alert.alert_id
        ]
        self._public_alerts.append(alert)

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID (e.g. when it is resolved)."""
        before = len(self._public_alerts)
        self._public_alerts = [
            a for a in self._public_alerts if a.alert_id != alert_id
        ]
        return len(self._public_alerts) < before

    def get_alerts(self) -> List[PublicAlertSchema]:
        return list(self._public_alerts)

    def get_alerts_for_region(self, region: str) -> List[PublicAlertSchema]:
        return [a for a in self._public_alerts if a.region == region]

    # -----------------------------------------------------------------------
    # Full abstraction snapshot — what PublicController surfaces to routes
    # -----------------------------------------------------------------------

    def get_snapshot(self) -> Optional[PublicAbstractionSchema]:
        """
        Returns the full public-facing snapshot.
        Returns None if no sensor data has been received yet.
        """
        if self._sensor_data is None:
            return None

        return PublicAbstractionSchema(
            sensor_data=self._sensor_data,
            region=self._sensor_data.region,
            last_updated=self._last_updated or "",
        )

    def has_data(self) -> bool:
        return self._sensor_data is not None
"""
Alerts Agent Service — AlertsAbstraction
PAC Architecture: Abstraction layer of the Alerts Agent.

AlertsAbstraction sits between CityAlertManagement (control) and the
AlertPresentation interface (presentation). It holds:
  - The current configured alert rule list (mirrors alertRules in UML).
  - The pending approvals list (mirrors pendingApprovals in UML).
  - The current AlertPresentation state for the presentation layer.

Updated to match the real Supabase schema:
  - alertRules keyed by str(alert_id) (UUID) not alertID (string)
  - Uses ConfiguredAlertSchema not TriggeredAlertsSchema
  - set_presentation() accepts an optional triggered alert as a second arg
    to match the three-argument calls in controller.py
  - Convenience builders updated to use new field names (alert.alert_id,
    alert.geographic_area, alert.status)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from app.models import (
    AlertPresentationSchema,
    AlertVisibility,
    ConfiguredAlertSchema,
    ConfiguredAlertStatus,
    TriggeredAlertSchema,
    TriggeredAlertStatus,
)


class AlertsAbstraction:
    """
    Abstraction layer of the Alerts PAC Agent.

    Responsibilities:
    - Mirror the UML alertRules and pendingApprovals lists in memory.
    - Maintain the AlertPresentation state (current alert being displayed).
    - Provide helper methods that produce AlertPresentationSchema objects
      so the controller and routes never construct presentation state directly.
    """

    def __init__(self):
        # UML: alertRules: List<TriggeredAlerts>
        # Keyed by str(alert_id) (UUID) for O(1) lookup
        self._alert_rules: Dict[str, ConfiguredAlertSchema] = {}

        # UML: pendingApprovals: List<TriggeredAlerts>
        self._pending_approvals: Dict[str, ConfiguredAlertSchema] = {}

        # UML: alertPresentation: AlertPresentation
        self._presentation: Optional[AlertPresentationSchema] = None

    # -----------------------------------------------------------------------
    # Alert rules — mirrors UML alertRules: List<TriggeredAlerts>
    # Now uses ConfiguredAlertSchema; keyed by str(alert.alert_id)
    # -----------------------------------------------------------------------

    def add_alert_rule(self, alert: ConfiguredAlertSchema) -> None:
        self._alert_rules[str(alert.alert_id)] = alert

    def update_alert_rule(self, alert: ConfiguredAlertSchema) -> None:
        """Replace an existing rule entirely."""
        self._alert_rules[str(alert.alert_id)] = alert

    def remove_alert_rule(self, alert_id: str) -> bool:
        if alert_id in self._alert_rules:
            del self._alert_rules[alert_id]
            return True
        return False

    def get_alert_rule(self, alert_id: str) -> Optional[ConfiguredAlertSchema]:
        return self._alert_rules.get(alert_id)

    def get_all_alert_rules(self) -> List[ConfiguredAlertSchema]:
        return list(self._alert_rules.values())

    def get_active_rules(self) -> List[ConfiguredAlertSchema]:
        return [
            a for a in self._alert_rules.values()
            if a.status == ConfiguredAlertStatus.APPROVED and a.is_active
        ]

    def get_rules_by_area(self, geographic_area: str) -> List[ConfiguredAlertSchema]:
        return [
            a for a in self._alert_rules.values()
            if a.geographic_area == geographic_area
        ]

    # -----------------------------------------------------------------------
    # Pending approvals — mirrors UML pendingApprovals: List<TriggeredAlerts>
    # -----------------------------------------------------------------------

    def add_to_pending(self, alert: ConfiguredAlertSchema) -> None:
        self._pending_approvals[str(alert.alert_id)] = alert

    def remove_from_pending(self, alert_id: str) -> Optional[ConfiguredAlertSchema]:
        return self._pending_approvals.pop(alert_id, None)

    def get_pending_approvals(self) -> List[ConfiguredAlertSchema]:
        return list(self._pending_approvals.values())

    def is_pending(self, alert_id: str) -> bool:
        return alert_id in self._pending_approvals

    # -----------------------------------------------------------------------
    # Session / state clearing
    # -----------------------------------------------------------------------

    def clear_session(self) -> None:
        """Called on shutdown to clear in-memory state."""
        self._alert_rules.clear()
        self._pending_approvals.clear()
        self._presentation = None

    # -----------------------------------------------------------------------
    # AlertPresentation — UML: alertPresentation: AlertPresentation
    #
    # set_presentation() accepts three arguments to match the controller's
    # call sites which supply both a configured and a triggered alert:
    #   set_presentation(configured, triggered, message)
    # Both alert arguments are optional — pass None for either if not
    # relevant to the operation being described.
    # -----------------------------------------------------------------------

    def set_presentation(
        self,
        configured_alert: Optional[ConfiguredAlertSchema],
        triggered_alert: Optional[TriggeredAlertSchema],
        message: str,
    ) -> AlertPresentationSchema:
        """
        Build and store the current AlertPresentation state.
        Maps to AlertPresentation.update(AlertPresentation) in the UML.

        Args:
            configured_alert: The configured alert rule being acted on, or None.
            triggered_alert:  The triggered alert event being acted on, or None.
            message:          Human-readable description for the presentation layer.
        """
        self._presentation = AlertPresentationSchema(
            configured_alert=configured_alert,
            triggered_alert=triggered_alert,
            presentation_message=message,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        return self._presentation

    def get_presentation(self) -> Optional[AlertPresentationSchema]:
        return self._presentation

    # -----------------------------------------------------------------------
    # Convenience builders — produce AlertPresentationSchema for common
    # controller outcomes. Use the new ConfiguredAlertSchema field names.
    # -----------------------------------------------------------------------

    def presentation_for_created(
        self, alert: ConfiguredAlertSchema
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            alert,
            None,
            f"Alert rule '{alert.alert_name}' created. Status: pending.",
        )

    def presentation_for_approved(
        self, alert: ConfiguredAlertSchema
    ) -> AlertPresentationSchema:
        visibility = alert.alert_visibility.value if alert.alert_visibility else "Internal"
        return self.set_presentation(
            alert,
            None,
            f"Alert rule '{alert.alert_name}' approved and active in "
            f"'{alert.geographic_area}'. Visibility: {visibility}.",
        )

    def presentation_for_acknowledged(
        self,
        configured_alert: Optional[ConfiguredAlertSchema],
        triggered_alert: TriggeredAlertSchema,
        operator_id: uuid.UUID,
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            configured_alert,
            triggered_alert,
            f"Alert acknowledged by operator '{operator_id}'.",
        )

    def presentation_for_resolved(
        self, alert: ConfiguredAlertSchema
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            alert,
            None,
            f"Alert rule '{alert.alert_name}' resolved.",
        )

    def presentation_for_error(self, message: str) -> AlertPresentationSchema:
        return self.set_presentation(None, None, f"Error: {message}")
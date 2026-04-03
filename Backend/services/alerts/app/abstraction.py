"""
Alerts Agent Service — AlertsAbstraction
PAC Architecture: Abstraction layer of the Alerts Agent.

AlertsAbstraction sits between CityAlertManagement (control) and the
AlertPresentation interface (presentation). It holds:
  - The current active alert rule list (mirrors alertRules in UML).
  - The pending approvals list (mirrors pendingApprovals in UML).
  - The current AlertPresentation state for the presentation layer.
  - A focused view of the most recently triggered / updated alert.

This layer owns no persistence — ConfiguredAlertsDatabase in the
controller is the durable store. The abstraction provides fast in-memory
access to current state so routes and the presentation layer never touch
raw controller internals directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.models import (
    AlertPresentationSchema,
    AlertSeverity,
    AlertStatus,
    TriggeredAlertsResponse,
    TriggeredAlertsSchema,
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
        # Keyed by alertID for O(1) lookup
        self._alert_rules: Dict[str, TriggeredAlertsSchema] = {}

        # UML: pendingApprovals: List<TriggeredAlerts>
        self._pending_approvals: Dict[str, TriggeredAlertsSchema] = {}

        # UML: alertPresentation: AlertPresentation
        self._presentation: Optional[AlertPresentationSchema] = None

    # -----------------------------------------------------------------------
    # Alert rules — mirrors UML alertRules: List<TriggeredAlerts>
    # -----------------------------------------------------------------------

    def add_alert_rule(self, alert: TriggeredAlertsSchema) -> None:
        self._alert_rules[alert.alertID] = alert

    def update_alert_rule(self, alert: TriggeredAlertsSchema) -> None:
        """Replace an existing rule entirely."""
        self._alert_rules[alert.alertID] = alert

    def remove_alert_rule(self, alert_id: str) -> bool:
        if alert_id in self._alert_rules:
            del self._alert_rules[alert_id]
            return True
        return False

    def get_alert_rule(self, alert_id: str) -> Optional[TriggeredAlertsSchema]:
        return self._alert_rules.get(alert_id)

    def get_all_alert_rules(self) -> List[TriggeredAlertsSchema]:
        return list(self._alert_rules.values())

    def get_active_rules(self) -> List[TriggeredAlertsSchema]:
        return [
            a for a in self._alert_rules.values()
            if a.status == AlertStatus.ACTIVE
        ]

    def get_rules_by_region(self, region: str) -> List[TriggeredAlertsSchema]:
        return [
            a for a in self._alert_rules.values()
            if a.region == region
        ]

    # -----------------------------------------------------------------------
    # Pending approvals — mirrors UML pendingApprovals: List<TriggeredAlerts>
    # -----------------------------------------------------------------------

    def add_to_pending(self, alert: TriggeredAlertsSchema) -> None:
        self._pending_approvals[alert.alertID] = alert

    def remove_from_pending(self, alert_id: str) -> Optional[TriggeredAlertsSchema]:
        return self._pending_approvals.pop(alert_id, None)

    def get_pending_approvals(self) -> List[TriggeredAlertsSchema]:
        return list(self._pending_approvals.values())

    def is_pending(self, alert_id: str) -> bool:
        return alert_id in self._pending_approvals

    # -----------------------------------------------------------------------
    # AlertPresentation — UML: alertPresentation: AlertPresentation
    # UML update(AlertPresentation) is modelled here as set_presentation()
    # -----------------------------------------------------------------------

    def set_presentation(
        self,
        alert: Optional[TriggeredAlertsSchema],
        message: str,
    ) -> AlertPresentationSchema:
        """
        Build and store the current AlertPresentation state.
        Maps to AlertPresentation.update(AlertPresentation) in the UML.
        """
        response = (
            TriggeredAlertsResponse.from_schema(alert) if alert else None
        )
        self._presentation = AlertPresentationSchema(
            triggered_alert=response,
            presentation_message=message,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        return self._presentation

    def get_presentation(self) -> Optional[AlertPresentationSchema]:
        return self._presentation

    # -----------------------------------------------------------------------
    # Convenience: build AlertPresentationSchema for common outcomes
    # Used by the controller to return consistent presentation state
    # -----------------------------------------------------------------------

    def presentation_for_created(
        self, alert: TriggeredAlertsSchema
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            alert,
            f"Alert rule '{alert.alertID}' created. Status: PENDING_APPROVAL.",
        )

    def presentation_for_approved(
        self, alert: TriggeredAlertsSchema
    ) -> AlertPresentationSchema:
        severity_label = AlertSeverity(alert.severity).name
        return self.set_presentation(
            alert,
            f"{severity_label}: '{alert.alertID}' approved and active in "
            f"{alert.region}.",
        )

    def presentation_for_acknowledged(
        self, alert: TriggeredAlertsSchema, operator_id: str
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            alert,
            f"Alert '{alert.alertID}' acknowledged by operator '{operator_id}'.",
        )

    def presentation_for_resolved(
        self, alert: TriggeredAlertsSchema
    ) -> AlertPresentationSchema:
        return self.set_presentation(
            alert,
            f"Alert '{alert.alertID}' resolved.",
        )

    def presentation_for_error(self, message: str) -> AlertPresentationSchema:
        return self.set_presentation(None, f"Error: {message}")
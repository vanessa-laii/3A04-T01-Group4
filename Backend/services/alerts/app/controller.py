"""
Alerts Agent Service — AlertManagement (Abstract) + CityAlertManagement (Concrete)
PAC Architecture: Control layer of the Alerts Agent.

The UML defines AlertManagement as an <<Abstract Class>> with six methods.
CityAlertManagement is the concrete implementation used by this service.

Also contains:
  ConfiguredAlertsDatabase — UML persistence class for TriggeredAlerts
  AlertPresentation        — UML interface, modelled as a thin wrapper
                             around AlertsAbstraction.set_presentation()
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from app.abstraction import AlertsAbstraction
from app.models import (
    AcknowledgeAlertResponse,
    AlertDatabaseQueryParams,
    AlertDatabaseQueryResponse,
    AlertPresentationSchema,
    AlertSeverity,
    AlertStatus,
    ApproveAlertRuleResponse,
    ConfiguredAlertsDatabaseRecord,
    CreateAlertRuleRequest,
    CreateAlertRuleResponse,
    DeleteAlertRuleResponse,
    EditAlertRuleRequest,
    EditAlertRuleResponse,
    EnvironmentalType,
    RejectAlertRuleResponse,
    SendForApprovalResponse,
    TriggeredAlertsResponse,
    TriggeredAlertsSchema,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ConfiguredAlertsDatabase
# UML: + TriggeredAlerts: TriggeredAlerts
#      (persistence class owned by AlertManagement)
# ---------------------------------------------------------------------------

class ConfiguredAlertsDatabase:
    """
    Persistence layer for TriggeredAlerts / configured alert rules.
    All methods are async to support drop-in replacement with a real
    async DB driver (SQLAlchemy async, asyncpg, etc.).

    TODO: replace the in-memory dict with real DB calls.
    """

    def __init__(self):
        # record_id -> ConfiguredAlertsDatabaseRecord
        self._records: Dict[str, ConfiguredAlertsDatabaseRecord] = {}
        # alertID -> record_id (secondary index for fast alert lookups)
        self._alert_index: Dict[str, str] = {}

    async def save(self, alert: TriggeredAlertsSchema) -> ConfiguredAlertsDatabaseRecord:
        """Insert or update a TriggeredAlerts record."""
        # If this alertID already has a record, update it in place
        existing_record_id = self._alert_index.get(alert.alertID)
        record_id = existing_record_id or f"db-rec-{uuid.uuid4().hex[:8]}"

        record = ConfiguredAlertsDatabaseRecord(
            record_id=record_id,
            stored_at=datetime.now(timezone.utc).isoformat(),
            alert=alert,
        )
        self._records[record_id] = record
        self._alert_index[alert.alertID] = record_id

        logger.info(
            "ConfiguredAlertsDatabase: saved alert '%s' (record_id=%s status=%s).",
            alert.alertID,
            record_id,
            alert.status.name,
        )
        return record

    async def get_by_alert_id(
        self, alert_id: str
    ) -> Optional[ConfiguredAlertsDatabaseRecord]:
        record_id = self._alert_index.get(alert_id)
        if record_id is None:
            return None
        return self._records.get(record_id)

    async def delete(self, alert_id: str) -> bool:
        record_id = self._alert_index.pop(alert_id, None)
        if record_id is None:
            return False
        self._records.pop(record_id, None)
        logger.info("ConfiguredAlertsDatabase: deleted alert '%s'.", alert_id)
        return True

    async def query(
        self, params: AlertDatabaseQueryParams
    ) -> AlertDatabaseQueryResponse:
        """Filter records by the supplied query parameters."""
        results = [r.alert for r in self._records.values()]

        if params.region:
            results = [a for a in results if a.region == params.region]
        if params.environmental_type:
            results = [
                a for a in results
                if a.environmentalType == params.environmental_type
            ]
        if params.status is not None:
            results = [a for a in results if a.status == params.status]
        if params.severity is not None:
            results = [a for a in results if a.severity == params.severity]
        if params.publicly_visible is not None:
            results = [
                a for a in results
                if a.publiclyVisible == params.publicly_visible
            ]

        results = results[: params.limit]

        # Re-wrap in full records for the response
        records = []
        for alert in results:
            rec = await self.get_by_alert_id(alert.alertID)
            if rec:
                records.append(rec)

        return AlertDatabaseQueryResponse(records=records, total=len(records))


# ---------------------------------------------------------------------------
# AlertManagement — <<Abstract Class>> from UML
# ---------------------------------------------------------------------------

class AlertManagement(ABC):
    """
    UML <<Abstract Class>> AlertManagement.

    Defines the six alert lifecycle operations that any concrete
    implementation must provide. CityAlertManagement is the concrete
    subclass used by this microservice.

    UML attributes (owned by the concrete class):
      - alertRules: List<TriggeredAlerts>       → AlertsAbstraction
      - pendingApprovals: List<TriggeredAlerts>  → AlertsAbstraction
      - alertPresentation: AlertPresentation     → AlertsAbstraction
    """

    @abstractmethod
    async def create_alert_rule(
        self, request: CreateAlertRuleRequest
    ) -> CreateAlertRuleResponse:
        """UML: createAlertRule(alertID, environmentalType, Region,
        threshold, time, visibility): boolean"""
        pass

    @abstractmethod
    async def send_for_approval(self, alert_id: str) -> SendForApprovalResponse:
        """UML: sendForApproval(alertID): void"""
        pass

    @abstractmethod
    async def edit_alert_rule(
        self, alert_id: str, request: EditAlertRuleRequest
    ) -> EditAlertRuleResponse:
        """UML: editAlertRule(alertID, updates): boolean"""
        pass

    @abstractmethod
    async def delete_alert_rule(self, alert_id: str) -> DeleteAlertRuleResponse:
        """UML: deleteAlertRule(alertID): boolean"""
        pass

    @abstractmethod
    async def acknowledge_alert(
        self, alert_id: str, operator_id: str
    ) -> AcknowledgeAlertResponse:
        """UML: acknowledgeAlert(alertID, operatorID): void"""
        pass

    @abstractmethod
    async def approve_alert_rule(self, alert_id: str) -> ApproveAlertRuleResponse:
        """UML: approveAlertRule(alertID): boolean"""
        pass


# ---------------------------------------------------------------------------
# CityAlertManagement — concrete implementation of AlertManagement
# ---------------------------------------------------------------------------

class CityAlertManagement(AlertManagement):
    """
    Concrete control layer of the Alerts PAC Agent.

    Extends AlertManagement (abstract) with full implementations of all
    six UML lifecycle methods. Owns and wires together:
      - ConfiguredAlertsDatabase  (persistence)
      - AlertsAbstraction         (in-memory state + presentation layer)
      - httpx.AsyncClient         (for forwarding to the City agent)
    """

    def __init__(self, city_service_url: str):
        self._city_url = city_service_url
        self._database = ConfiguredAlertsDatabase()
        self._abstraction = AlertsAbstraction()
        self._http_client: Optional[httpx.AsyncClient] = None

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    async def initialise(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("CityAlertManagement initialised.")

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        logger.info("CityAlertManagement shut down.")

    # -----------------------------------------------------------------------
    # UML: createAlertRule(alertID, environmentalType, Region,
    #                      threshold, time, visibility): boolean
    # -----------------------------------------------------------------------

    async def create_alert_rule(
        self, request: CreateAlertRuleRequest
    ) -> CreateAlertRuleResponse:
        # Guard against duplicate alertIDs
        existing = await self._database.get_by_alert_id(request.alertID)
        if existing:
            presentation = self._abstraction.presentation_for_error(
                f"Alert rule '{request.alertID}' already exists."
            )
            return CreateAlertRuleResponse(
                success=False,
                message=f"Alert rule '{request.alertID}' already exists.",
                presentation=presentation,
            )

        alert = TriggeredAlertsSchema(
            alertID=request.alertID,
            threshold=request.threshold,
            environmentalType=request.environmentalType,
            region=request.region,
            severity=request.severity,
            publiclyVisible=request.publiclyVisible,
            time=request.time,
            status=AlertStatus.PENDING_APPROVAL,
        )

        await self._database.save(alert)
        self._abstraction.add_alert_rule(alert)
        presentation = self._abstraction.presentation_for_created(alert)

        logger.info(
            "Alert rule created: id=%s type=%s region=%s",
            alert.alertID,
            alert.environmentalType,
            alert.region,
        )
        return CreateAlertRuleResponse(
            success=True,
            alertID=alert.alertID,
            status=alert.status,
            message=f"Alert rule '{alert.alertID}' created. Awaiting approval.",
            presentation=presentation,
        )

    # -----------------------------------------------------------------------
    # UML: sendForApproval(alertID): void
    # -----------------------------------------------------------------------

    async def send_for_approval(self, alert_id: str) -> SendForApprovalResponse:
        alert = self._abstraction.get_alert_rule(alert_id)

        if alert is None:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' not found."
            )
            return SendForApprovalResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' not found.",
                presentation=presentation,
            )

        if alert.status != AlertStatus.PENDING_APPROVAL:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' is not in PENDING_APPROVAL status "
                f"(current: {alert.status.name})."
            )
            return SendForApprovalResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' cannot be sent for approval "
                        f"from status '{alert.status.name}'.",
                presentation=presentation,
            )

        # Move to the pending approvals list
        self._abstraction.add_to_pending(alert)
        presentation = self._abstraction.set_presentation(
            alert,
            f"Alert '{alert_id}' submitted for approval.",
        )

        logger.info("Alert '%s' sent for approval.", alert_id)
        return SendForApprovalResponse(
            success=True,
            alertID=alert_id,
            message=f"Alert '{alert_id}' submitted for approval.",
            presentation=presentation,
        )

    # -----------------------------------------------------------------------
    # UML: editAlertRule(alertID, updates): boolean
    # -----------------------------------------------------------------------

    async def edit_alert_rule(
        self, alert_id: str, request: EditAlertRuleRequest
    ) -> EditAlertRuleResponse:
        alert = self._abstraction.get_alert_rule(alert_id)

        if alert is None:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' not found."
            )
            return EditAlertRuleResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' not found.",
                presentation=presentation,
            )

        # Resolved / rejected alerts cannot be edited
        if alert.status in (AlertStatus.RESOLVED, AlertStatus.REJECTED):
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' cannot be edited in status "
                f"'{alert.status.name}'."
            )
            return EditAlertRuleResponse(
                success=False,
                alertID=alert_id,
                message=f"Cannot edit alert with status '{alert.status.name}'.",
                presentation=presentation,
            )

        # Apply partial updates — only supplied fields are changed
        updated_data = alert.model_dump()
        if request.threshold is not None:
            updated_data["threshold"] = request.threshold
        if request.severity is not None:
            updated_data["severity"] = request.severity
        if request.region is not None:
            updated_data["region"] = request.region
        if request.time is not None:
            updated_data["time"] = request.time
        if request.publiclyVisible is not None:
            updated_data["publiclyVisible"] = request.publiclyVisible

        updated_alert = TriggeredAlertsSchema(**updated_data)
        await self._database.save(updated_alert)
        self._abstraction.update_alert_rule(updated_alert)

        presentation = self._abstraction.set_presentation(
            updated_alert,
            f"Alert rule '{alert_id}' updated.",
        )

        logger.info("Alert rule '%s' edited.", alert_id)
        return EditAlertRuleResponse(
            success=True,
            alertID=alert_id,
            message=f"Alert rule '{alert_id}' updated successfully.",
            presentation=presentation,
        )

    # -----------------------------------------------------------------------
    # UML: deleteAlertRule(alertID): boolean
    # -----------------------------------------------------------------------

    async def delete_alert_rule(self, alert_id: str) -> DeleteAlertRuleResponse:
        db_deleted = await self._database.delete(alert_id)
        mem_deleted = self._abstraction.remove_alert_rule(alert_id)
        self._abstraction.remove_from_pending(alert_id)

        if not db_deleted and not mem_deleted:
            return DeleteAlertRuleResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' not found.",
            )

        logger.info("Alert rule '%s' deleted.", alert_id)
        return DeleteAlertRuleResponse(
            success=True,
            alertID=alert_id,
            message=f"Alert rule '{alert_id}' deleted.",
        )

    # -----------------------------------------------------------------------
    # UML: acknowledgeAlert(alertID, operatorID): void
    # -----------------------------------------------------------------------

    async def acknowledge_alert(
        self, alert_id: str, operator_id: str
    ) -> AcknowledgeAlertResponse:
        alert = self._abstraction.get_alert_rule(alert_id)

        if alert is None:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' not found."
            )
            return AcknowledgeAlertResponse(
                success=False,
                alertID=alert_id,
                operatorID=operator_id,
                message=f"Alert '{alert_id}' not found.",
                presentation=presentation,
            )

        if alert.status != AlertStatus.ACTIVE:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' must be ACTIVE to acknowledge "
                f"(current: {alert.status.name})."
            )
            return AcknowledgeAlertResponse(
                success=False,
                alertID=alert_id,
                operatorID=operator_id,
                message=f"Cannot acknowledge alert with status '{alert.status.name}'.",
                presentation=presentation,
            )

        updated_data = alert.model_dump()
        updated_data["status"] = AlertStatus.ACKNOWLEDGED
        updated_alert = TriggeredAlertsSchema(**updated_data)

        await self._database.save(updated_alert)
        self._abstraction.update_alert_rule(updated_alert)
        presentation = self._abstraction.presentation_for_acknowledged(
            updated_alert, operator_id
        )

        logger.info(
            "Alert '%s' acknowledged by operator '%s'.", alert_id, operator_id
        )
        return AcknowledgeAlertResponse(
            success=True,
            alertID=alert_id,
            operatorID=operator_id,
            message=f"Alert '{alert_id}' acknowledged.",
            presentation=presentation,
        )

    # -----------------------------------------------------------------------
    # UML: approveAlertRule(alertID): boolean
    # -----------------------------------------------------------------------

    async def approve_alert_rule(self, alert_id: str) -> ApproveAlertRuleResponse:
        # Must be in pending approvals list
        pending = self._abstraction.remove_from_pending(alert_id)
        alert = pending or self._abstraction.get_alert_rule(alert_id)

        if alert is None:
            presentation = self._abstraction.presentation_for_error(
                f"Alert '{alert_id}' not found in pending approvals."
            )
            return ApproveAlertRuleResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' not found.",
                presentation=presentation,
            )

        # Activate the alert
        updated_data = alert.model_dump()
        updated_data["status"] = AlertStatus.ACTIVE
        active_alert = TriggeredAlertsSchema(**updated_data)

        await self._database.save(active_alert)
        self._abstraction.update_alert_rule(active_alert)
        presentation = self._abstraction.presentation_for_approved(active_alert)

        logger.info(
            "Alert '%s' approved and active. publicly_visible=%s",
            alert_id,
            active_alert.publiclyVisible,
        )

        # Forward to City agent if publicly visible
        forwarded = False
        if active_alert.publiclyVisible:
            forwarded = await self._forward_to_city(active_alert)

        return ApproveAlertRuleResponse(
            success=True,
            alertID=alert_id,
            forwarded_to_city=forwarded,
            message=(
                f"Alert '{alert_id}' approved and active."
                + (" Forwarded to City agent." if forwarded else "")
            ),
            presentation=presentation,
        )

    # -----------------------------------------------------------------------
    # Reject (workflow complement to approve — not in UML but required)
    # -----------------------------------------------------------------------

    async def reject_alert_rule(self, alert_id: str) -> RejectAlertRuleResponse:
        pending = self._abstraction.remove_from_pending(alert_id)
        alert = pending or self._abstraction.get_alert_rule(alert_id)

        if alert is None:
            return RejectAlertRuleResponse(
                success=False,
                alertID=alert_id,
                message=f"Alert '{alert_id}' not found.",
            )

        updated_data = alert.model_dump()
        updated_data["status"] = AlertStatus.REJECTED
        rejected_alert = TriggeredAlertsSchema(**updated_data)

        await self._database.save(rejected_alert)
        self._abstraction.update_alert_rule(rejected_alert)

        logger.info("Alert '%s' rejected.", alert_id)
        return RejectAlertRuleResponse(
            success=True,
            alertID=alert_id,
            message=f"Alert '{alert_id}' rejected.",
        )

    # -----------------------------------------------------------------------
    # Abstraction layer accessors (used by routes)
    # -----------------------------------------------------------------------

    def get_alert_rule(
        self, alert_id: str
    ) -> Optional[TriggeredAlertsSchema]:
        return self._abstraction.get_alert_rule(alert_id)

    def get_all_alert_rules(self) -> List[TriggeredAlertsSchema]:
        return self._abstraction.get_all_alert_rules()

    def get_active_rules(self) -> List[TriggeredAlertsSchema]:
        return self._abstraction.get_active_rules()

    def get_pending_approvals(self) -> List[TriggeredAlertsSchema]:
        return self._abstraction.get_pending_approvals()

    def get_presentation(self) -> Optional[AlertPresentationSchema]:
        return self._abstraction.get_presentation()

    # -----------------------------------------------------------------------
    # ConfiguredAlertsDatabase query passthrough (used by routes)
    # -----------------------------------------------------------------------

    async def query_database(
        self, params: AlertDatabaseQueryParams
    ) -> AlertDatabaseQueryResponse:
        return await self._database.query(params)

    async def get_database_record(
        self, alert_id: str
    ) -> Optional[ConfiguredAlertsDatabaseRecord]:
        return await self._database.get_by_alert_id(alert_id)

    # -----------------------------------------------------------------------
    # City agent forwarding
    # -----------------------------------------------------------------------

    async def _forward_to_city(self, alert: TriggeredAlertsSchema) -> bool:
        """
        POST the approved, publicly visible alert to the City agent.
        The City agent will route it onward to the Public agent.
        Returns True on success, False on failure.
        """
        if not self._http_client:
            logger.error("HTTP client not initialised — cannot forward alert.")
            return False

        payload = {
            "alert_id": alert.alertID,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "region": alert.region,
            "environmental_type": alert.environmentalType.value,
            "threshold": alert.threshold,
            "time": alert.time,
            "publicly_visible": alert.publiclyVisible,
        }

        try:
            response = await self._http_client.post(
                f"{self._city_url}/api/v1/alerts/inbound",
                json=payload,
            )
            response.raise_for_status()
            logger.info(
                "Alert '%s' forwarded to City agent.", alert.alertID
            )
            return True
        except httpx.RequestError as exc:
            logger.error(
                "Failed to forward alert '%s' to City agent (network): %s",
                alert.alertID,
                exc,
            )
            return False
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Failed to forward alert '%s' to City agent (HTTP %s): %s",
                alert.alertID,
                exc.response.status_code,
                exc,
            )
            return False
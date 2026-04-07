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
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.abstraction import AlertsAbstraction
from app.orm_models import ConfiguredAlerts, TriggeredAlerts, TimeSeriesSensorData
from app.models import (
    AcknowledgeAlertRequest,
    AcknowledgeAlertResponse,
    AlertDatabaseQueryParams,
    AlertDatabaseQueryResponse,
    AlertPresentationSchema,
    AlertVisibility,
    ApproveAlertRuleResponse,
    ConfiguredAlertSchema,
    ConfiguredAlertsDatabaseRecord,
    ConfiguredAlertStatus,
    CreateAlertRuleRequest,
    CreateAlertRuleResponse,
    DeleteAlertRuleResponse,
    EditAlertRuleRequest,
    EditAlertRuleResponse,
    EnvironmentalMetric,
    RejectAlertRuleResponse,
    SendForApprovalResponse,
    TriggeredAlertSchema,
    TriggeredAlertSeverity,
    TriggeredAlertStatus,
)
 
logger = logging.getLogger(__name__)
 
 
# ---------------------------------------------------------------------------
# ConfiguredAlertsDatabase
# Wraps configured_alerts table — rule definitions
# ---------------------------------------------------------------------------
 
class ConfiguredAlertsDatabase:
    def __init__(self, session: AsyncSession):
        self._session = session
 
    async def save(self, alert: ConfiguredAlerts) -> ConfiguredAlerts:
        self._session.add(alert)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(alert)
        return alert
 
    async def get_by_id(self, alert_id: uuid.UUID) -> Optional[ConfiguredAlerts]:
        result = await self._session.execute(
            select(ConfiguredAlerts).where(ConfiguredAlerts.alert_id == alert_id)
        )
        return result.scalar_one_or_none()
 
    async def get_pending(self) -> List[ConfiguredAlerts]:
        result = await self._session.execute(
            select(ConfiguredAlerts).where(
                ConfiguredAlerts.status == ConfiguredAlertStatus.PENDING.value
            )
        )
        return list(result.scalars().all())
 
    async def get_approved_active(self) -> List[ConfiguredAlerts]:
        result = await self._session.execute(
            select(ConfiguredAlerts).where(
                and_(
                    ConfiguredAlerts.status == ConfiguredAlertStatus.APPROVED.value,
                    ConfiguredAlerts.is_active == True,
                )
            )
        )
        return list(result.scalars().all())
 
    async def query(
        self, params: AlertDatabaseQueryParams
    ) -> List[ConfiguredAlerts]:
        conditions = []
        if params.geographic_area:
            conditions.append(ConfiguredAlerts.geographic_area == params.geographic_area)
        if params.environmental_metric:
            conditions.append(ConfiguredAlerts.environmental_metric == params.environmental_metric.value)
        if params.configured_status:
            conditions.append(ConfiguredAlerts.status == params.configured_status.value)
 
        q = select(ConfiguredAlerts).limit(params.limit)
        if conditions:
            q = q.where(and_(*conditions))
        result = await self._session.execute(q)
        return list(result.scalars().all())
 
 
# ---------------------------------------------------------------------------
# TriggeredAlertsDatabase
# Wraps triggered_alerts table — fired alert events
# ---------------------------------------------------------------------------
 
class TriggeredAlertsDatabase:
    def __init__(self, session: AsyncSession):
        self._session = session
 
    async def create(
        self,
        alert_id: uuid.UUID,
        triggered_value: float,
        sensor_id: Optional[str],
        region: Optional[str],
        severity: Optional[str],
        is_public: bool,
    ) -> TriggeredAlerts:
        row = TriggeredAlerts(
            alert_id=alert_id,
            triggered_value=triggered_value,
            sensor_id=sensor_id,
            region=region,
            alert_severity=severity,
            is_public=is_public,
            status=TriggeredAlertStatus.ACTIVE.value,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(row)
        return row
 
    async def get_by_id(
        self, triggered_alert_id: uuid.UUID
    ) -> Optional[TriggeredAlerts]:
        result = await self._session.execute(
            select(TriggeredAlerts).where(
                TriggeredAlerts.triggered_alert_id == triggered_alert_id
            )
        )
        return result.scalar_one_or_none()
 
    async def get_by_configured_alert(
        self, alert_id: uuid.UUID
    ) -> List[TriggeredAlerts]:
        result = await self._session.execute(
            select(TriggeredAlerts).where(TriggeredAlerts.alert_id == alert_id)
        )
        return list(result.scalars().all())
 
    async def acknowledge(
        self,
        triggered_alert_id: uuid.UUID,
        operator_id: uuid.UUID,
    ) -> Optional[TriggeredAlerts]:
        row = await self.get_by_id(triggered_alert_id)
        if row is None or row.status != TriggeredAlertStatus.ACTIVE.value:
            return None
        row.status           = TriggeredAlertStatus.ACKNOWLEDGED.value
        row.acknowledged_by  = operator_id
        row.acknowledged_at  = datetime.now(timezone.utc)
        await self._session.commit()
        return row
 
    async def query(
        self, params: AlertDatabaseQueryParams
    ) -> List[TriggeredAlerts]:
        conditions = []
        if params.triggered_status:
            conditions.append(TriggeredAlerts.status == params.triggered_status.value)
        if params.severity:
            conditions.append(TriggeredAlerts.alert_severity == params.severity.value)
        if params.is_public is not None:
            conditions.append(TriggeredAlerts.is_public == params.is_public)
 
        q = select(TriggeredAlerts).limit(params.limit)
        if conditions:
            q = q.where(and_(*conditions))
        result = await self._session.execute(q)
        return list(result.scalars().all())
 
 
# ---------------------------------------------------------------------------
# AlertManagement — abstract base (UML <<Abstract Class>>)
# ---------------------------------------------------------------------------
 
class AlertManagement(ABC):
    @abstractmethod
    async def create_alert_rule(self, request: CreateAlertRuleRequest) -> CreateAlertRuleResponse:
        pass
 
    @abstractmethod
    async def send_for_approval(self, alert_id: uuid.UUID) -> SendForApprovalResponse:
        pass
 
    @abstractmethod
    async def edit_alert_rule(self, alert_id: uuid.UUID, request: EditAlertRuleRequest) -> EditAlertRuleResponse:
        pass
 
    @abstractmethod
    async def delete_alert_rule(self, alert_id: uuid.UUID) -> DeleteAlertRuleResponse:
        pass
 
    @abstractmethod
    async def acknowledge_alert(self, triggered_alert_id: uuid.UUID, operator_id: uuid.UUID) -> AcknowledgeAlertResponse:
        pass
 
    @abstractmethod
    async def approve_alert_rule(self, alert_id: uuid.UUID, approver_id: uuid.UUID) -> ApproveAlertRuleResponse:
        pass

    @abstractmethod
    async def initialise(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass
 
 
# ---------------------------------------------------------------------------
# CityAlertManagement — concrete implementation
# ---------------------------------------------------------------------------
 
class CityAlertManagement(AlertManagement):
 
    def __init__(
        self,
        session: AsyncSession,
        city_service_url: str,
        http_client: httpx.AsyncClient,
    ):
        self._session        = session
        self._configured_db  = ConfiguredAlertsDatabase(session)
        self._triggered_db   = TriggeredAlertsDatabase(session)
        self._abstraction    = AlertsAbstraction()
        self._city_url       = city_service_url
        self._http_client    = http_client
 
    # -----------------------------------------------------------------------
    # createAlertRule → INSERT configured_alerts (status='pending')
    # -----------------------------------------------------------------------
 
    async def create_alert_rule(
        self, request: CreateAlertRuleRequest
    ) -> CreateAlertRuleResponse:
        row = ConfiguredAlerts(
            operator_id=request.operator_id,
            environmental_metric=request.environmental_metric.value,
            geographic_area=request.geographic_area,
            threshold_value=request.threshold_value,
            timeframe_minutes=request.timeframe_minutes,
            alert_visibility=request.alert_visibility.value,
            alert_name=request.alert_name,
            threshold_value_max=request.threshold_value_max,
            condition=request.condition,
            description=request.description,
            status=ConfiguredAlertStatus.PENDING.value,
        )
        saved = await self._configured_db.save(row)
        schema = _configured_to_schema(saved)
        presentation = self._abstraction.presentation_for_created(schema)
 
        logger.info("Alert rule created: id=%s name=%s", saved.alert_id, saved.alert_name)
        return CreateAlertRuleResponse(
            success=True,
            alert_id=saved.alert_id,
            status=ConfiguredAlertStatus.PENDING,
            message=f"Alert rule '{saved.alert_name}' created. Awaiting approval.",
            presentation=presentation,
        )
 
    # -----------------------------------------------------------------------
    # sendForApproval → no DB change; marks as submitted in abstraction layer
    # -----------------------------------------------------------------------
 
    async def send_for_approval(
        self, alert_id: uuid.UUID
    ) -> SendForApprovalResponse:
        row = await self._configured_db.get_by_id(alert_id)
        if row is None:
            return SendForApprovalResponse(
                success=False, alert_id=alert_id,
                message=f"Alert rule '{alert_id}' not found.",
            )
        if row.status != ConfiguredAlertStatus.PENDING.value:
            return SendForApprovalResponse(
                success=False, alert_id=alert_id,
                message=f"Alert is in status '{row.status}', not 'pending'.",
            )
        schema = _configured_to_schema(row)
        self._abstraction.add_to_pending(schema)
        presentation = self._abstraction.set_presentation(
            schema, None, f"Alert '{row.alert_name}' submitted for approval."
        )
        return SendForApprovalResponse(
            success=True, alert_id=alert_id,
            message=f"Alert '{row.alert_name}' submitted for approval.",
            presentation=presentation,
        )
 
    # -----------------------------------------------------------------------
    # editAlertRule → UPDATE configured_alerts
    # -----------------------------------------------------------------------
 
    async def edit_alert_rule(
        self, alert_id: uuid.UUID, request: EditAlertRuleRequest
    ) -> EditAlertRuleResponse:
        row = await self._configured_db.get_by_id(alert_id)
        if row is None:
            return EditAlertRuleResponse(
                success=False, alert_id=alert_id,
                message=f"Alert rule '{alert_id}' not found.",
            )
        if request.threshold_value      is not None: row.threshold_value      = request.threshold_value
        if request.threshold_value_max  is not None: row.threshold_value_max  = request.threshold_value_max
        if request.timeframe_minutes    is not None: row.timeframe_minutes    = request.timeframe_minutes
        if request.geographic_area      is not None: row.geographic_area      = request.geographic_area
        if request.environmental_metric is not None: row.environmental_metric = request.environmental_metric.value
        if request.alert_visibility     is not None: row.alert_visibility     = request.alert_visibility.value
        if request.alert_name           is not None: row.alert_name           = request.alert_name
        if request.condition            is not None: row.condition            = request.condition
        if request.description          is not None: row.description          = request.description
        if request.is_active            is not None: row.is_active            = request.is_active

        # Any edit resets the rule to pending — must be re-submitted and re-approved
        row.status = ConfiguredAlertStatus.PENDING.value
 
        row.updated_at = datetime.now(timezone.utc)
        saved = await self._configured_db.save(row)
        schema = _configured_to_schema(saved)
        self._abstraction.update_alert_rule(schema)
        presentation = self._abstraction.set_presentation(
            schema, None, f"Alert rule '{saved.alert_name}' updated."
        )
        logger.info("Alert rule edited: id=%s", alert_id)
        return EditAlertRuleResponse(
            success=True, alert_id=alert_id,
            message=f"Alert rule '{saved.alert_name}' updated.",
            presentation=presentation,
        )
 
    # -----------------------------------------------------------------------
    # deleteAlertRule → soft delete (is_active=False)
    # -----------------------------------------------------------------------
 
    async def delete_alert_rule(
        self, alert_id: uuid.UUID
    ) -> DeleteAlertRuleResponse:
        row = await self._configured_db.get_by_id(alert_id)
        if row is None:
            return DeleteAlertRuleResponse(
                success=False, alert_id=alert_id,
                message=f"Alert rule '{alert_id}' not found.",
            )
        row.is_active  = False
        row.updated_at = datetime.now(timezone.utc)
        await self._configured_db.save(row)
        self._abstraction.remove_alert_rule(str(alert_id))
        self._abstraction.remove_from_pending(str(alert_id))
        logger.info("Alert rule soft-deleted: id=%s", alert_id)
        return DeleteAlertRuleResponse(
            success=True, alert_id=alert_id,
            message=f"Alert rule '{alert_id}' deactivated.",
        )
 
    # -----------------------------------------------------------------------
    # acknowledgeAlert → UPDATE triggered_alerts
    # -----------------------------------------------------------------------
 
    async def acknowledge_alert(
        self, triggered_alert_id: uuid.UUID, operator_id: uuid.UUID
    ) -> AcknowledgeAlertResponse:
        row = await self._triggered_db.acknowledge(triggered_alert_id, operator_id)
        if row is None:
            return AcknowledgeAlertResponse(
                success=False,
                triggered_alert_id=triggered_alert_id,
                operator_id=operator_id,
                message=f"Triggered alert '{triggered_alert_id}' not found or not active.",
            )
        schema = _triggered_to_schema(row)
        configured = await self._configured_db.get_by_id(row.alert_id)
        configured_schema = _configured_to_schema(configured) if configured else None
        presentation = self._abstraction.set_presentation(
            configured_schema, schema,
            f"Alert acknowledged by operator '{operator_id}'.",
        )
        logger.info("Alert acknowledged: triggered_id=%s operator=%s", triggered_alert_id, operator_id)
        return AcknowledgeAlertResponse(
            success=True,
            triggered_alert_id=triggered_alert_id,
            operator_id=operator_id,
            message="Alert acknowledged.",
            presentation=presentation,
        )
 
    # -----------------------------------------------------------------------
    # approveAlertRule → UPDATE configured_alerts SET status='approved'
    # -----------------------------------------------------------------------
 
    async def approve_alert_rule(
        self, alert_id: uuid.UUID, approver_id: uuid.UUID
    ) -> ApproveAlertRuleResponse:
        row = await self._configured_db.get_by_id(alert_id)
        if row is None:
            return ApproveAlertRuleResponse(
                success=False, alert_id=alert_id,
                message=f"Alert rule '{alert_id}' not found.",
            )
 
        row.status        = ConfiguredAlertStatus.APPROVED.value
        row.approved_by   = approver_id
        row.approval_date = datetime.now(timezone.utc)
        row.updated_at    = datetime.now(timezone.utc)
        saved = await self._configured_db.save(row)
        schema = _configured_to_schema(saved)
        self._abstraction.update_alert_rule(schema)
        self._abstraction.remove_from_pending(str(alert_id))
        presentation = self._abstraction.presentation_for_approved(schema)
 
        forwarded = False
        if saved.alert_visibility == AlertVisibility.PUBLIC_FACING.value:
            forwarded = await self._forward_to_city(schema)

        # Immediately evaluate against latest sensor data in case condition already violated
        await self._evaluate_on_approval(saved)

        logger.info("Alert rule approved: id=%s forwarded=%s", alert_id, forwarded)
        return ApproveAlertRuleResponse(
            success=True, alert_id=alert_id,
            forwarded_to_city=forwarded,
            message=f"Alert rule approved." + (" Forwarded to City agent." if forwarded else ""),
            presentation=presentation,
        )
 
    # -----------------------------------------------------------------------
    # reject (complements approve)
    # -----------------------------------------------------------------------
 
    async def reject_alert_rule(
        self, alert_id: uuid.UUID
    ) -> RejectAlertRuleResponse:
        row = await self._configured_db.get_by_id(alert_id)
        if row is None:
            return RejectAlertRuleResponse(
                success=False, alert_id=alert_id,
                message=f"Alert rule '{alert_id}' not found.",
            )
        row.status     = ConfiguredAlertStatus.REJECTED.value
        row.updated_at = datetime.now(timezone.utc)
        await self._configured_db.save(row)
        self._abstraction.remove_from_pending(str(alert_id))
        logger.info("Alert rule rejected: id=%s", alert_id)
        return RejectAlertRuleResponse(
            success=True, alert_id=alert_id,
            message=f"Alert rule '{alert_id}' rejected.",
        )
 
    # -----------------------------------------------------------------------
    # Accessors used by routes
    # -----------------------------------------------------------------------
 
    async def get_configured_alert(self, alert_id: uuid.UUID) -> Optional[ConfiguredAlertSchema]:
        row = await self._configured_db.get_by_id(alert_id)
        return _configured_to_schema(row) if row else None
 
    async def get_all_configured(self) -> List[ConfiguredAlertSchema]:
        rows = await self._configured_db.query(AlertDatabaseQueryParams(limit=1000))
        return [_configured_to_schema(r) for r in rows]
 
    async def get_pending_approvals(self) -> List[ConfiguredAlertSchema]:
        rows = await self._configured_db.get_pending()
        return [_configured_to_schema(r) for r in rows]
 
    async def get_active_rules(self) -> List[ConfiguredAlertSchema]:
        rows = await self._configured_db.get_approved_active()
        return [_configured_to_schema(r) for r in rows]
 
    async def get_triggered_alert(self, triggered_alert_id: uuid.UUID) -> Optional[TriggeredAlertSchema]:
        row = await self._triggered_db.get_by_id(triggered_alert_id)
        return _triggered_to_schema(row) if row else None
 
    async def query_database(
        self, params: AlertDatabaseQueryParams
    ) -> AlertDatabaseQueryResponse:
        configured_rows = await self._configured_db.query(params)
        records = []
        for c in configured_rows:
            triggered_rows = await self._triggered_db.get_by_configured_alert(c.alert_id)
            records.append(ConfiguredAlertsDatabaseRecord(
                alert=_configured_to_schema(c),
                triggered=[_triggered_to_schema(t) for t in triggered_rows],
            ))
        return AlertDatabaseQueryResponse(records=records, total=len(records))
 
    def get_presentation(self) -> Optional[AlertPresentationSchema]:
        return self._abstraction.get_presentation()
 
    # -----------------------------------------------------------------------
    # City agent forwarding
    # -----------------------------------------------------------------------
 
    async def _forward_to_city(self, alert: ConfiguredAlertSchema) -> bool:
        payload = {
            "alert_id":           str(alert.alert_id),
            "severity":           "MEDIUM",
            "status":             alert.status.value,
            "region":             alert.geographic_area,
            "environmental_type": alert.environmental_metric.value,
            "threshold":          alert.threshold_value,
            "time":               datetime.now(timezone.utc).isoformat(),
            "publicly_visible":   alert.alert_visibility == AlertVisibility.PUBLIC_FACING,
        }
        try:
            resp = await self._http_client.post(
                f"{self._city_url}/api/v1/alerts/inbound", json=payload
            )
            resp.raise_for_status()
            return True
        except httpx.RequestError as exc:
            logger.error("Failed to forward alert to City agent: %s", exc)
            return False

    async def _evaluate_on_approval(self, rule: ConfiguredAlerts) -> None:
        """
        After a rule is approved, check whether the most recent sensor reading
        for that zone+metric already violates the threshold. If so, create an
        immediate triggered_alert so operators see it right away.
        """
        try:
            result = await self._session.execute(
                select(TimeSeriesSensorData)
                .where(
                    and_(
                        TimeSeriesSensorData.geographic_zone == rule.geographic_area,
                        TimeSeriesSensorData.metric_type     == rule.environmental_metric,
                    )
                )
                .order_by(TimeSeriesSensorData.recorded_at.desc())
                .limit(1)
            )
            reading = result.scalar_one_or_none()
            if reading is None:
                return

            condition     = rule.condition or 'ABOVE'
            threshold_max = rule.threshold_value_max

            if threshold_max is not None:
                breached = reading.metric_value < rule.threshold_value or reading.metric_value > threshold_max
            elif condition == 'BELOW':
                breached = reading.metric_value < rule.threshold_value
            else:
                breached = reading.metric_value > rule.threshold_value

            if not breached:
                return

            # Calculate severity
            if threshold_max is not None:
                range_size = threshold_max - rule.threshold_value
                if range_size <= 0:
                    severity = "Medium"
                else:
                    excess = (reading.metric_value - threshold_max) if reading.metric_value > threshold_max else (rule.threshold_value - reading.metric_value)
                    pct = (excess / range_size) * 100
                    severity = "Low" if pct < 10 else "Medium" if pct < 25 else "High" if pct < 50 else "Critical"
            elif rule.threshold_value == 0:
                severity = "High"
            else:
                if condition == 'BELOW':
                    pct = ((rule.threshold_value - reading.metric_value) / abs(rule.threshold_value)) * 100
                else:
                    pct = ((reading.metric_value - rule.threshold_value) / abs(rule.threshold_value)) * 100
                severity = "Low" if pct < 10 else "Medium" if pct < 25 else "High" if pct < 50 else "Critical"

            await self._triggered_db.create(
                alert_id=rule.alert_id,
                triggered_value=reading.metric_value,
                sensor_id=reading.sensor_id,
                region=reading.geographic_zone,
                severity=severity,
                is_public=rule.alert_visibility == AlertVisibility.PUBLIC_FACING.value,
            )
            logger.info(
                "Immediate trigger on approval: rule=%s metric=%s value=%.2f threshold=%.2f condition=%s severity=%s",
                rule.alert_id, rule.environmental_metric, reading.metric_value,
                rule.threshold_value, condition, severity,
            )
        except Exception as exc:
            logger.error("_evaluate_on_approval failed: %s", exc)

    async def initialise(self) -> None:
        """
        Prepare the controller for operation.
        This is called during the FastAPI lifespan startup.
        """
        # If AccountDatabase or AuditLogDataClass need to 
        # warm up a connection pool or check DB health, do it here.
        # Example: await self._account_db.verify_connection()
        pass

    async def shutdown(self) -> None:
        """
        Gracefully shut down sub-components.
        This is called during the FastAPI lifespan shutdown.
        """
        # Clear the in-memory abstraction cache on shutdown
        self._abstraction.clear_session()
        
        # If you added an HTTP client or a specific worker to 
        # any sub-component, close it here.
        # Example: await self._audit_log.close_session()
        pass
 
 
# ---------------------------------------------------------------------------
# Helpers — ORM row → Pydantic schema
# ---------------------------------------------------------------------------
 
def _configured_to_schema(row: ConfiguredAlerts) -> ConfiguredAlertSchema:
    return ConfiguredAlertSchema(
        alert_id=row.alert_id,
        operator_id=row.operator_id,
        environmental_metric=EnvironmentalMetric(row.environmental_metric),
        geographic_area=row.geographic_area,
        threshold_value=row.threshold_value,
        timeframe_minutes=row.timeframe_minutes,
        alert_visibility=AlertVisibility(row.alert_visibility),
        alert_name=row.alert_name,
        threshold_value_max=row.threshold_value_max,
        condition=row.condition or 'ABOVE',
        description=row.description,
        is_active=row.is_active if row.is_active is not None else True,
        created_at=row.created_at,
        updated_at=row.updated_at,
        approved_by=row.approved_by,
        approval_date=row.approval_date,
        status=ConfiguredAlertStatus(row.status or "pending"),
    )
 
 
def _triggered_to_schema(row: TriggeredAlerts) -> TriggeredAlertSchema:
    return TriggeredAlertSchema(
        triggered_alert_id=row.triggered_alert_id,
        alert_id=row.alert_id,
        triggered_value=row.triggered_value,
        sensor_id=row.sensor_id,
        region=row.region,
        triggered_at=row.triggered_at,
        acknowledged_at=row.acknowledged_at,
        acknowledged_by=row.acknowledged_by,
        is_false_alarm=row.is_false_alarm or False,
        alert_severity=TriggeredAlertSeverity(row.alert_severity) if row.alert_severity else None,
        is_public=row.is_public or False,
        status=TriggeredAlertStatus(row.status or "active"),
    )
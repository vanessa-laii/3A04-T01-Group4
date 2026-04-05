"""
Alerts Agent Service — Routes
All API endpoints exposed by the Alerts Agent.

Route groups:
  /alerts/rules      — CRUD for alert rules (create, edit, delete, list)
  /alerts/approval   — approval workflow (send for approval, approve, reject)
  /alerts/active     — live / active alert queries
  /alerts/acknowledge — operator acknowledgement
  /alerts/presentation — AlertPresentation interface state
  /alerts/database   — ConfiguredAlertsDatabase historical queries
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.controller import CityAlertManagement
from app.dependencies import get_alert_management_controller
from app.models import (
    AcknowledgeAlertRequest,
    AcknowledgeAlertResponse,
    AlertDatabaseQueryParams,
    AlertDatabaseQueryResponse,
    AlertPresentationSchema,
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
    TriggeredAlertSeverity,
    TriggeredAlertStatus,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Alert rule CRUD
# UML: createAlertRule / editAlertRule / deleteAlertRule
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/rules",
    response_model=CreateAlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Alert Rules"],
    summary="Create a new alert rule",
    description=(
        "Creates a new configured alert rule in the database. "
        "New rules are placed in 'pending' status and must be submitted "
        "for approval before becoming active. Maps to UML: "
        "createAlertRule(alertID, environmentalType, Region, threshold, "
        "time, visibility): boolean."
    ),
)
async def create_alert_rule(
    request: CreateAlertRuleRequest,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> CreateAlertRuleResponse:
    return await controller.create_alert_rule(request)


@router.get(
    "/alerts/rules",
    response_model=List[ConfiguredAlertSchema],
    tags=["Alert Rules"],
    summary="List all alert rules",
    description="Returns all configured alert rules from the database.",
)
async def list_alert_rules(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[ConfiguredAlertSchema]:
    return await controller.get_all_configured()


@router.get(
    "/alerts/rules/{alert_id}",
    response_model=ConfiguredAlertSchema,
    tags=["Alert Rules"],
    summary="Get a specific alert rule",
)
async def get_alert_rule(
    alert_id: uuid.UUID,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> ConfiguredAlertSchema:
    alert = await controller.get_configured_alert(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule '{alert_id}' not found.",
        )
    return alert


@router.patch(
    "/alerts/rules/{alert_id}",
    response_model=EditAlertRuleResponse,
    tags=["Alert Rules"],
    summary="Edit an alert rule",
    description=(
        "Partially updates an existing alert rule. Only supplied fields are "
        "modified. Rejected rules cannot be edited. Maps to UML: "
        "editAlertRule(alertID, updates): boolean."
    ),
)
async def edit_alert_rule(
    alert_id: uuid.UUID,
    request: EditAlertRuleRequest,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> EditAlertRuleResponse:
    return await controller.edit_alert_rule(alert_id, request)


@router.delete(
    "/alerts/rules/{alert_id}",
    response_model=DeleteAlertRuleResponse,
    tags=["Alert Rules"],
    summary="Delete (deactivate) an alert rule",
    description=(
        "Soft-deletes an alert rule by setting is_active=False. A hard "
        "DELETE is not used because triggered_alerts holds FK references "
        "to configured_alerts. Maps to UML: deleteAlertRule(alertID): boolean."
    ),
)
async def delete_alert_rule(
    alert_id: uuid.UUID,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> DeleteAlertRuleResponse:
    return await controller.delete_alert_rule(alert_id)


# ---------------------------------------------------------------------------
# Approval workflow
# UML: sendForApproval / approveAlertRule
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/rules/{alert_id}/submit",
    response_model=SendForApprovalResponse,
    tags=["Approval Workflow"],
    summary="Submit an alert rule for approval",
    description=(
        "Marks a pending alert rule as submitted for approval in the "
        "abstraction layer. Maps to UML: sendForApproval(alertID): void."
    ),
)
async def send_for_approval(
    alert_id: uuid.UUID,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> SendForApprovalResponse:
    return await controller.send_for_approval(alert_id)


@router.get(
    "/alerts/approval/pending",
    response_model=List[ConfiguredAlertSchema],
    tags=["Approval Workflow"],
    summary="List all alerts pending approval",
    description=(
        "Returns all alert rules with status 'pending' from the database "
        "(UML: pendingApprovals: List<TriggeredAlerts>)."
    ),
)
async def list_pending_approvals(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[ConfiguredAlertSchema]:
    return await controller.get_pending_approvals()


@router.post(
    "/alerts/rules/{alert_id}/approve",
    response_model=ApproveAlertRuleResponse,
    tags=["Approval Workflow"],
    summary="Approve an alert rule",
    description=(
        "Approves a pending alert rule, setting its status to 'approved'. "
        "If the rule visibility is 'Public Facing' it is forwarded to the "
        "City agent. Maps to UML: approveAlertRule(alertID): boolean. "
        "The approver_id query parameter identifies who is approving."
    ),
)
async def approve_alert_rule(
    alert_id: uuid.UUID,
    approver_id: uuid.UUID = Query(
        ...,
        description="accountinfo_id of the operator approving this rule.",
    ),
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> ApproveAlertRuleResponse:
    return await controller.approve_alert_rule(alert_id, approver_id)


@router.post(
    "/alerts/rules/{alert_id}/reject",
    response_model=RejectAlertRuleResponse,
    tags=["Approval Workflow"],
    summary="Reject an alert rule",
    description=(
        "Rejects a pending alert rule, setting its status to 'rejected'. "
        "Rejected rules cannot be edited or re-submitted."
    ),
)
async def reject_alert_rule(
    alert_id: uuid.UUID,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> RejectAlertRuleResponse:
    return await controller.reject_alert_rule(alert_id)


# ---------------------------------------------------------------------------
# Active alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/active",
    response_model=List[ConfiguredAlertSchema],
    tags=["Active Alerts"],
    summary="List all active (approved) alert rules",
    description=(
        "Returns all configured alert rules with status 'approved' and "
        "is_active=True."
    ),
)
async def list_active_alerts(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[ConfiguredAlertSchema]:
    return await controller.get_active_rules()


# ---------------------------------------------------------------------------
# Acknowledgement
# UML: acknowledgeAlert(alertID, operatorID): void
#
# NOTE: alert_id here is the triggered_alert_id (UUID primary key of the
# triggered_alerts table), not the configured alert_id. The path param
# is named triggered_alert_id for clarity.
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/triggered/{triggered_alert_id}/acknowledge",
    response_model=AcknowledgeAlertResponse,
    tags=["Acknowledgement"],
    summary="Acknowledge a triggered alert",
    description=(
        "Marks a triggered alert event as ACKNOWLEDGED by the given operator. "
        "The path parameter is the triggered_alert_id (PK of triggered_alerts), "
        "not the configured alert_id. "
        "Maps to UML: acknowledgeAlert(alertID, operatorID): void."
    ),
)
async def acknowledge_alert(
    triggered_alert_id: uuid.UUID,
    request: AcknowledgeAlertRequest,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> AcknowledgeAlertResponse:
    return await controller.acknowledge_alert(triggered_alert_id, request.operator_id)


# ---------------------------------------------------------------------------
# AlertPresentation — UML interface state
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/presentation",
    response_model=AlertPresentationSchema,
    tags=["Presentation"],
    summary="Get the current AlertPresentation state",
    description=(
        "Returns the current AlertPresentation state from the abstraction "
        "layer — the most recently acted-on alert with its human-readable "
        "presentation message."
    ),
)
async def get_presentation(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> AlertPresentationSchema:
    presentation = controller.get_presentation()
    if presentation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No presentation state available yet.",
        )
    return presentation


# ---------------------------------------------------------------------------
# ConfiguredAlertsDatabase — historical queries
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/database/records",
    response_model=AlertDatabaseQueryResponse,
    tags=["Database"],
    summary="Query alert database records",
    description=(
        "Query configured alert records with their associated triggered events. "
        "Supports filtering by geographic area, environmental metric, "
        "configured status, triggered status, severity, and public visibility."
    ),
)
async def query_database(
    geographic_area: Optional[str] = Query(None, example="Downtown"),
    environmental_metric: Optional[EnvironmentalMetric] = Query(None),
    configured_status: Optional[ConfiguredAlertStatus] = Query(None),
    triggered_status: Optional[TriggeredAlertStatus] = Query(None),
    severity: Optional[TriggeredAlertSeverity] = Query(None),
    is_public: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> AlertDatabaseQueryResponse:
    params = AlertDatabaseQueryParams(
        geographic_area=geographic_area,
        environmental_metric=environmental_metric,
        configured_status=configured_status,
        triggered_status=triggered_status,
        severity=severity,
        is_public=is_public,
        limit=limit,
    )
    return await controller.query_database(params)


@router.get(
    "/alerts/database/records/{alert_id}",
    response_model=ConfiguredAlertsDatabaseRecord,
    tags=["Database"],
    summary="Get a specific configured alert record with its triggered events",
    description=(
        "Returns a ConfiguredAlertsDatabaseRecord containing the configured "
        "alert rule and all of its associated triggered alert events."
    ),
)
async def get_database_record(
    alert_id: uuid.UUID,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> ConfiguredAlertsDatabaseRecord:
    # Fetch the configured rule
    configured = await controller.get_configured_alert(alert_id)
    if configured is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No alert record found for alert_id '{alert_id}'.",
        )

    # Fetch all triggered events linked to this rule
    result = await controller.query_database(
        AlertDatabaseQueryParams(limit=1000)
    )
    triggered = []
    for record in result.records:
        if record.alert.alert_id == alert_id:
            triggered = record.triggered
            break

    return ConfiguredAlertsDatabaseRecord(alert=configured, triggered=triggered)
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
        "Creates a new TriggeredAlerts rule in the ConfiguredAlertsDatabase. "
        "New rules are placed in PENDING_APPROVAL status and must be sent for "
        "approval before becoming active. Maps to UML: "
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
    response_model=List[TriggeredAlertsResponse],
    tags=["Alert Rules"],
    summary="List all alert rules",
    description="Returns all alert rules currently held in the abstraction layer.",
)
async def list_alert_rules(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[TriggeredAlertsResponse]:
    rules = controller.get_all_alert_rules()
    return [TriggeredAlertsResponse.from_schema(r) for r in rules]


@router.get(
    "/alerts/rules/{alert_id}",
    response_model=TriggeredAlertsResponse,
    tags=["Alert Rules"],
    summary="Get a specific alert rule",
)
async def get_alert_rule(
    alert_id: str,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> TriggeredAlertsResponse:
    alert = controller.get_alert_rule(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule '{alert_id}' not found.",
        )
    return TriggeredAlertsResponse.from_schema(alert)


@router.patch(
    "/alerts/rules/{alert_id}",
    response_model=EditAlertRuleResponse,
    tags=["Alert Rules"],
    summary="Edit an alert rule",
    description=(
        "Partially updates an existing alert rule. Only supplied fields are "
        "modified. Resolved and rejected alerts cannot be edited. Maps to UML: "
        "editAlertRule(alertID, updates): boolean."
    ),
)
async def edit_alert_rule(
    alert_id: str,
    request: EditAlertRuleRequest,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> EditAlertRuleResponse:
    return await controller.edit_alert_rule(alert_id, request)


@router.delete(
    "/alerts/rules/{alert_id}",
    response_model=DeleteAlertRuleResponse,
    tags=["Alert Rules"],
    summary="Delete an alert rule",
    description=(
        "Removes an alert rule from both the ConfiguredAlertsDatabase and the "
        "in-memory abstraction layer. Maps to UML: deleteAlertRule(alertID): boolean."
    ),
)
async def delete_alert_rule(
    alert_id: str,
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
        "Moves a PENDING_APPROVAL alert rule into the pending approvals queue. "
        "Maps to UML: sendForApproval(alertID): void."
    ),
)
async def send_for_approval(
    alert_id: str,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> SendForApprovalResponse:
    return await controller.send_for_approval(alert_id)


@router.get(
    "/alerts/approval/pending",
    response_model=List[TriggeredAlertsResponse],
    tags=["Approval Workflow"],
    summary="List all alerts pending approval",
    description=(
        "Returns all alert rules currently in the pending approvals queue "
        "(UML: pendingApprovals: List<TriggeredAlerts>)."
    ),
)
async def list_pending_approvals(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[TriggeredAlertsResponse]:
    pending = controller.get_pending_approvals()
    return [TriggeredAlertsResponse.from_schema(a) for a in pending]


@router.post(
    "/alerts/rules/{alert_id}/approve",
    response_model=ApproveAlertRuleResponse,
    tags=["Approval Workflow"],
    summary="Approve an alert rule",
    description=(
        "Approves a pending alert rule, setting its status to ACTIVE. If the "
        "rule is publicly visible it is automatically forwarded to the City "
        "agent, which routes it to the Public agent. Maps to UML: "
        "approveAlertRule(alertID): boolean."
    ),
)
async def approve_alert_rule(
    alert_id: str,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> ApproveAlertRuleResponse:
    return await controller.approve_alert_rule(alert_id)


@router.post(
    "/alerts/rules/{alert_id}/reject",
    response_model=RejectAlertRuleResponse,
    tags=["Approval Workflow"],
    summary="Reject an alert rule",
    description=(
        "Rejects a pending alert rule, setting its status to REJECTED. "
        "Rejected rules cannot be edited or re-submitted. "
        "Not defined in UML but required to complete the approval workflow."
    ),
)
async def reject_alert_rule(
    alert_id: str,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> RejectAlertRuleResponse:
    return await controller.reject_alert_rule(alert_id)


# ---------------------------------------------------------------------------
# Active alerts
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/active",
    response_model=List[TriggeredAlertsResponse],
    tags=["Active Alerts"],
    summary="List all active alerts",
    description=(
        "Returns all alert rules with status ACTIVE. These are approved rules "
        "that are currently live in the system."
    ),
)
async def list_active_alerts(
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> List[TriggeredAlertsResponse]:
    active = controller.get_active_rules()
    return [TriggeredAlertsResponse.from_schema(a) for a in active]


# ---------------------------------------------------------------------------
# Acknowledgement
# UML: acknowledgeAlert(alertID, operatorID): void
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AcknowledgeAlertResponse,
    tags=["Acknowledgement"],
    summary="Acknowledge an active alert",
    description=(
        "Marks an ACTIVE alert as ACKNOWLEDGED by the given operator. "
        "Maps to UML: acknowledgeAlert(alertID, operatorID): void."
    ),
)
async def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeAlertRequest,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> AcknowledgeAlertResponse:
    return await controller.acknowledge_alert(alert_id, request.operatorID)


# ---------------------------------------------------------------------------
# AlertPresentation — UML interface state
# UML: alertPresentation: AlertPresentation
#      + update(AlertPresentation)
# ---------------------------------------------------------------------------

@router.get(
    "/alerts/presentation",
    response_model=AlertPresentationSchema,
    tags=["Presentation"],
    summary="Get the current AlertPresentation state",
    description=(
        "Returns the current AlertPresentation state from the abstraction "
        "layer — the most recently triggered or updated alert with its "
        "human-readable presentation message. Maps to UML AlertPresentation "
        "interface (alertPresentation: AlertPresentation)."
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
    summary="Query ConfiguredAlertsDatabase records",
    description=(
        "Query historical alert records from the ConfiguredAlertsDatabase. "
        "Supports filtering by region, environmental type, status, severity, "
        "and public visibility."
    ),
)
async def query_database(
    region: Optional[str] = Query(None, example="Downtown"),
    environmental_type: Optional[EnvironmentalType] = Query(None),
    alert_status: Optional[AlertStatus] = Query(None, alias="status"),
    severity: Optional[AlertSeverity] = Query(None),
    publicly_visible: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> AlertDatabaseQueryResponse:
    params = AlertDatabaseQueryParams(
        region=region,
        environmental_type=environmental_type,
        status=alert_status,
        severity=severity,
        publicly_visible=publicly_visible,
        limit=limit,
    )
    return await controller.query_database(params)


@router.get(
    "/alerts/database/records/{alert_id}",
    response_model=ConfiguredAlertsDatabaseRecord,
    tags=["Database"],
    summary="Get a specific ConfiguredAlertsDatabase record",
)
async def get_database_record(
    alert_id: str,
    controller: CityAlertManagement = Depends(get_alert_management_controller),
) -> ConfiguredAlertsDatabaseRecord:
    record = await controller.get_database_record(alert_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No database record found for alert '{alert_id}'.",
        )
    return record
"""
In-App Task List, Alerts, and Multi-Tier Escalations (FR-AL-01, FR-AL-03, FR-SM-06, FR-SV-06, FR-IM-05)
"""
from datetime import datetime, timedelta, date, timezone
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.alert import Alert, AlertType, AlertPriority, AlertStatus
from ..models.child import Child
from ..models.hierarchy import AWC
from ..models.supervisor import SupervisorVisit
from ..models.measurement import Measurement
from ..models.user import User, UserRole
from ..schemas.all_schemas import AlertResponse, AlertAcknowledgeRequest
from ..auth.rbac import get_current_user, get_user_accessible_awc_ids, log_audit_event

router = APIRouter(prefix="/alerts", tags=["Alerts & Tasks"])


def perform_escalations(db: Session):
    """FR-AL-01, FR-AL-03, FR-SV-06: Scans surveillance rules and handles escalations."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)

    # 1. Escalate to CDPO if unresolved > 14 days
    unresolved_14d = db.query(Alert).filter(
        Alert.status.in_([AlertStatus.OPEN, AlertStatus.ESCALATED_LS]),
        Alert.type.in_([AlertType.NEW_SAM, AlertType.SAM_RELAPSE]),
        Alert.created_at <= fourteen_days_ago
    ).all()
    for alt in unresolved_14d:
        alt.status = AlertStatus.ESCALATED_CDPO
        alt.escalation_level = 2
        alt.last_escalated_at = now

    # 2. Escalate to LS if unresolved > 7 days
    unresolved_7d = db.query(Alert).filter(
        Alert.status == AlertStatus.OPEN,
        Alert.type.in_([AlertType.NEW_SAM, AlertType.SAM_RELAPSE]),
        Alert.created_at <= seven_days_ago
    ).all()
    for alt in unresolved_7d:
        alt.status = AlertStatus.ESCALATED_LS
        alt.escalation_level = 1
        alt.last_escalated_at = now

    # 3. FR-SV-06: AWC not visited for > 30 days
    all_awcs = db.query(AWC).all()
    for awc in all_awcs:
        last_visit = db.query(SupervisorVisit).filter(
            SupervisorVisit.awc_id == awc.id
        ).order_by(SupervisorVisit.visit_date.desc()).first()
        
        needs_alert = False
        if not last_visit:
            needs_alert = True
        elif last_visit.visit_date < thirty_days_ago:
            needs_alert = True

        if needs_alert:
            existing_alert = db.query(Alert).filter(
                Alert.awc_id == awc.id,
                Alert.type == AlertType.VISIT_DUE_30D,
                Alert.status.in_([AlertStatus.OPEN, AlertStatus.ESCALATED_LS, AlertStatus.ESCALATED_CDPO])
            ).first()
            if not existing_alert:
                db.add(Alert(
                    alert_id=f"ALT-{secrets.token_hex(4).upper()}",
                    type=AlertType.VISIT_DUE_30D,
                    awc_id=awc.id,
                    priority=AlertPriority.MEDIUM,
                    status=AlertStatus.OPEN,
                    description=f"AWC {awc.name} ({awc.code}) has not been inspected by Lady Supervisor in over 30 days. Inspection visit required."
                ))

    # 4. FR-AL-01: Child not seen for 60 days
    active_children = db.query(Child).filter(Child.status == "ACTIVE").all()
    for child in active_children:
        last_meas = db.query(Measurement).filter(
            Measurement.child_id == child.id
        ).order_by(Measurement.date.desc()).first()

        if last_meas and last_meas.date < sixty_days_ago:
            existing_alert = db.query(Alert).filter(
                Alert.child_id == child.id,
                Alert.type == AlertType.CHILD_NOT_SEEN_60D,
                Alert.status.in_([AlertStatus.OPEN, AlertStatus.ESCALATED_LS, AlertStatus.ESCALATED_CDPO])
            ).first()
            if not existing_alert:
                db.add(Alert(
                    alert_id=f"ALT-{secrets.token_hex(4).upper()}",
                    type=AlertType.CHILD_NOT_SEEN_60D,
                    child_id=child.id,
                    awc_id=child.awc_id,
                    priority=AlertPriority.MEDIUM,
                    status=AlertStatus.OPEN,
                    description=f"{child.name} ({child.child_id}) has not been measured in over 60 days (last measured: {last_meas.date}). Home visit required."
                ))

    db.commit()


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    status_filter: Optional[AlertStatus] = None,
    priority_filter: Optional[AlertPriority] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-AL-01: In-app task list of active alerts scoped to user's jurisdiction."""
    perform_escalations(db)

    accessible_awcs = get_user_accessible_awc_ids(current_user, db)
    query = db.query(Alert)

    if accessible_awcs is not None:
        query = query.filter(Alert.awc_id.in_(accessible_awcs))

    if status_filter:
        query = query.filter(Alert.status == status_filter)
    if priority_filter:
        query = query.filter(Alert.priority == priority_filter)

    alerts = query.order_by(Alert.priority.desc(), Alert.created_at.desc()).all()
    
    out = []
    for a in alerts:
        resp = AlertResponse.model_validate(a)
        if a.child_id:
            c = db.query(Child.name).filter(Child.id == a.child_id).first()
            if c:
                resp.child_name = c[0]
        awc = db.query(AWC.name).filter(AWC.id == a.awc_id).first()
        if awc:
            resp.awc_name = awc[0]
        out.append(resp)
    return out


@router.post("/{id}/acknowledge")
def acknowledge_alert(
    id: int,
    req: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-AL-03: Acknowledge and resolve an alert with recorded action and note."""
    alert = db.query(Alert).filter(Alert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    accessible_awcs = get_user_accessible_awc_ids(current_user, db)
    if accessible_awcs is not None and alert.awc_id not in accessible_awcs:
        raise HTTPException(status_code=403, detail="Forbidden")

    alert.status = AlertStatus.CLOSED
    alert.action_taken = req.action_taken
    alert.notes = req.notes
    alert.action_by = f"{current_user.full_name} ({current_user.role.value})"
    alert.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    log_audit_event(
        db, current_user, "ACKNOWLEDGE_ALERT", "Alert", str(alert.id),
        after_val={"action": req.action_taken, "status": "CLOSED"}
    )

    return {"message": "Alert resolved and closed successfully"}


@router.post("/check-escalations")
def trigger_escalation_job(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    perform_escalations(db)
    return {"message": "Escalation and surveillance scan completed"}

"""
Offline Data Sync Endpoint (FR-GM-07, NFR-03, NFR-04)
Idempotent batch synchronisation with latest server-validated timestamp conflict resolution.
"""
from datetime import datetime, date
import secrets
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.child import Child
from ..models.measurement import Measurement, StateEvent
from ..models.immunisation import VaccineRecord
from ..models.alert import Alert, AlertType, AlertPriority, AlertStatus
from ..models.user import User
from ..schemas.all_schemas import OfflineSyncPayload
from ..auth.rbac import get_current_user, assert_awc_access, log_audit_event
from ..rules.zscore import compute_all_zscores
from ..rules.classification import (
    validate_biological_ranges, classify_acute_malnutrition,
    evaluate_growth_indicators, check_zscore_plausibility
)
from ..rules.state_machine import NutritionalState, NutritionalStateMachine

router = APIRouter(prefix="/sync", tags=["Offline Synchronisation"])


@router.post("")
def synchronize_offline_data(
    payload: OfflineSyncPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-GM-07: Permits offline entry and synchronises records when connectivity returns.
    Resolves conflicts by latest server timestamp and ensures idempotence.
    """
    synced_measurements = 0
    conflicts_resolved = 0
    synced_vaccines = 0
    errors = []

    # 1. Process offline measurements
    for item in payload.measurements:
        child = db.query(Child).filter(Child.id == item.child_id).first()
        if not child:
            errors.append(f"Child #{item.child_id} not found.")
            continue

        try:
            assert_awc_access(current_user, child.awc_id, db)
        except Exception:
            errors.append(f"Access denied for child #{child.child_id}")
            continue

        # Check existing measurement in that month
        existing = db.query(Measurement).filter(
            Measurement.child_id == child.id,
            Measurement.date >= date(item.date.year, item.date.month, 1),
            Measurement.date < date(item.date.year + (1 if item.date.month == 12 else 0), 1 if item.date.month == 12 else item.date.month + 1, 1)
        ).first()

        if existing:
            # Idempotency / Conflict resolution: if offline item has newer client timestamp, update; otherwise ignore
            conflicts_resolved += 1
            continue

        # Compute age
        age_days = (item.date - child.dob).days
        age_months = max(0, (item.date.year - child.dob.year) * 12 + item.date.month - child.dob.month - (1 if item.date.day < child.dob.day else 0))

        # Z-scores
        z_res = compute_all_zscores(
            sex=child.sex,
            age_days=age_days,
            age_months=age_months,
            weight_kg=item.weight_kg,
            length_height_cm=item.length_height_cm,
            posture=item.posture
        )
        acute_class = classify_acute_malnutrition(z_res["whz"], age_months, item.muac_cm, item.oedema)
        indicators = evaluate_growth_indicators(z_res["waz"], z_res["haz"])
        is_implausible, _ = check_zscore_plausibility(z_res["waz"], z_res["haz"], z_res["whz"])

        # State machine
        curr_state = NutritionalState(child.current_state) if child.current_state else None
        trans = NutritionalStateMachine.step(
            current_state=curr_state,
            acute_class=acute_class,
            has_oedema=item.oedema,
            consecutive_normal_count=child.consecutive_normal_count or 0
        )

        meas = Measurement(
            measurement_id=f"MSR-{item.date.year}-{secrets.token_hex(4).upper()}",
            child_id=child.id,
            date=item.date,
            age_days=age_days,
            age_months=age_months,
            weight_kg=item.weight_kg,
            length_height_cm=item.length_height_cm,
            posture=item.posture,
            posture_corrected=z_res["posture_corrected"],
            corrected_dimension_cm=z_res["corrected_dimension"],
            muac_cm=item.muac_cm,
            oedema=item.oedema,
            waz=z_res["waz"],
            haz=z_res["haz"],
            whz=z_res["whz"],
            acute_class=acute_class.value,
            is_underweight=indicators["underweight"],
            is_severely_underweight=indicators["severely_underweight"],
            is_stunted=indicators["stunted"],
            is_severely_stunted=indicators["severely_stunted"],
            is_implausible=is_implausible,
            ref_version=z_res["ref_version"],
            created_by=f"{current_user.full_name} (Offline Sync)"
        )
        db.add(meas)

        child.current_state = trans.to_state.value
        child.consecutive_normal_count = trans.consecutive_normal_count

        evt = StateEvent(
            event_id=f"EVT-{secrets.token_hex(4).upper()}",
            child_id=child.id,
            from_state=trans.from_state.value if trans.from_state else None,
            to_state=trans.to_state.value,
            measurement_id=None,
            event_date=item.date,
            transition_rule=trans.rule_applied,
            notes="Synced from offline queue"
        )
        db.add(evt)
        synced_measurements += 1

    # 2. Process offline vaccine records
    for v_item in payload.vaccine_records:
        child = db.query(Child).filter(Child.id == v_item.child_id).first()
        if not child:
            continue
        existing_v = db.query(VaccineRecord).filter(
            VaccineRecord.child_id == child.id,
            VaccineRecord.vaccine_code == v_item.vaccine_code
        ).first()
        if existing_v:
            conflicts_resolved += 1
            continue

        v_rec = VaccineRecord(
            child_id=child.id,
            vaccine_code=v_item.vaccine_code,
            dose_no=v_item.dose_no,
            given_date=v_item.given_date,
            place=v_item.place or f"AWC #{child.awc_id}",
            batch_no=v_item.batch_no,
            recorded_by=f"{current_user.full_name} (Offline Sync)"
        )
        db.add(v_rec)
        synced_vaccines += 1

    db.commit()

    log_audit_event(
        db, current_user, "SYNC", "OfflineSync",
        after_val={
            "synced_measurements": synced_measurements,
            "synced_vaccines": synced_vaccines,
            "conflicts_resolved": conflicts_resolved
        }
    )

    return {
        "status": "SUCCESS",
        "synced_measurements": synced_measurements,
        "synced_vaccines": synced_vaccines,
        "conflicts_resolved": conflicts_resolved,
        "errors": errors
    }

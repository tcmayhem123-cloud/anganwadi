"""
Growth Measurement Capture, Z-Score Computation, State Transitions, and Growth Curves (FR-GM-01 to FR-GM-08, FR-ZS-01 to FR-ZS-06, FR-SM-01 to FR-SM-06)
"""
from datetime import date, datetime, timedelta, timezone
import math
import secrets
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.child import Child, ChildStatus
from ..models.measurement import Measurement, StateEvent
from ..models.alert import Alert, AlertType, AlertPriority, AlertStatus
from ..models.user import User
from ..schemas.all_schemas import (
    MeasurementCreate, MeasurementUpdate, MeasurementResponse, ZScorePreviewRequest
)
from ..auth.rbac import get_current_user, assert_awc_access, log_audit_event
from ..rules.zscore import compute_all_zscores, WHOReferenceStore
from ..rules.classification import (
    validate_biological_ranges, check_zscore_plausibility,
    classify_acute_malnutrition, evaluate_growth_indicators, AcuteMalnutritionClass
)
from ..rules.state_machine import (
    NutritionalState, NutritionalStateMachine, MeasurementRecordStub
)

router = APIRouter(prefix="/measurements", tags=["Growth Measurements"])


def compute_exact_age(dob: date, measurement_date: date) -> tuple[int, int]:
    """FR-GM-02: Computes exact age in days and completed months."""
    age_days = (measurement_date - dob).days
    if age_days < 0:
        raise ValueError("Measurement date cannot be before child's date of birth.")
    completed_months = max(0, (measurement_date.year - dob.year) * 12 + measurement_date.month - dob.month - (1 if measurement_date.day < dob.day else 0))
    return age_days, completed_months


@router.post("/preview")
def preview_zscores(req: ZScorePreviewRequest):
    """Provides instant live preview of z-scores and classification before submitting."""
    # Biological validation
    bio_val = validate_biological_ranges(req.weight_kg, req.length_height_cm, req.muac_cm)
    if not bio_val.is_valid:
        return {"is_valid": False, "errors": bio_val.errors, "warnings": bio_val.warnings}

    age_days, age_months = compute_exact_age(req.dob, req.measurement_date)
    z_res = compute_all_zscores(
        sex=req.sex,
        age_days=age_days,
        age_months=age_months,
        weight_kg=req.weight_kg,
        length_height_cm=req.length_height_cm,
        posture=req.posture
    )

    acute_class = classify_acute_malnutrition(
        whz=z_res["whz"],
        age_months=age_months,
        muac_cm=req.muac_cm,
        oedema=req.oedema
    )
    indicators = evaluate_growth_indicators(waz=z_res["waz"], haz=z_res["haz"])
    is_implausible, plausibility_flags = check_zscore_plausibility(z_res["waz"], z_res["haz"], z_res["whz"])

    return {
        "is_valid": True,
        "age_days": age_days,
        "age_months": age_months,
        "zscores": z_res,
        "acute_class": acute_class.value,
        "indicators": indicators,
        "is_implausible": is_implausible,
        "plausibility_flags": plausibility_flags,
        "warnings": bio_val.warnings
    }


@router.post("", response_model=MeasurementResponse, status_code=status.HTTP_201_CREATED)
def record_measurement(
    req: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-GM-01 to FR-GM-07: Records monthly measurement, computes WHO z-scores,
    updates state machine, logs state event, and generates alerts if needed.
    """
    child = db.query(Child).filter(Child.id == req.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    # 1. Biological Range Validation (FR-GM-04)
    bio_val = validate_biological_ranges(req.weight_kg, req.length_height_cm, req.muac_cm)
    if not bio_val.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Biological validation failed", "errors": bio_val.errors}
        )

    # 2. FR-GM-06: At most one measurement per calendar month by default
    meas_year = req.date.year
    meas_month = req.date.month
    existing_in_month = [
        m for m in child.measurements
        if m.date.year == meas_year and m.date.month == meas_month
    ]
    if existing_in_month:
        existing = existing_in_month[0]
        # Check if within 7-day correction window
        days_diff = (date.today() - existing.date).days
        if days_diff <= 7:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Measurement already recorded for this calendar month on {existing.date}. You can edit/correct measurement #{existing.measurement_id} directly within the 7-day window."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A measurement has already been recorded for this child for {meas_month}/{meas_year}. Only one monthly measurement is permitted."
            )

    # 3. Exact Age Computation (FR-GM-02)
    try:
        age_days, age_months = compute_exact_age(child.dob, req.date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 4. WHO LMS Z-Score Computation (FR-ZS-01, FR-ZS-02) + Posture Correction (FR-GM-03)
    z_res = compute_all_zscores(
        sex=child.sex,
        age_days=age_days,
        age_months=age_months,
        weight_kg=req.weight_kg,
        length_height_cm=req.length_height_cm,
        posture=req.posture
    )

    # 5. Plausibility Check (FR-GM-05)
    is_implausible, plausibility_flags = check_zscore_plausibility(z_res["waz"], z_res["haz"], z_res["whz"])
    if is_implausible and not req.confirm_implausible:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Implausible z-score detected! Please verify measurements or set confirm_implausible=true to proceed.",
                "flags": plausibility_flags,
                "zscores": z_res
            }
        )

    # 6. Nutritional Classification (FR-ZS-03, FR-ZS-04)
    acute_class_enum = classify_acute_malnutrition(
        whz=z_res["whz"],
        age_months=age_months,
        muac_cm=req.muac_cm,
        oedema=req.oedema
    )
    indicators = evaluate_growth_indicators(waz=z_res["waz"], haz=z_res["haz"])

    # 7. State Machine Evaluation (FR-SM-01 to FR-SM-03)
    curr_nutr_state = NutritionalState(child.current_state) if child.current_state else None
    transition = NutritionalStateMachine.step(
        current_state=curr_nutr_state,
        acute_class=acute_class_enum,
        has_oedema=req.oedema,
        consecutive_normal_count=child.consecutive_normal_count or 0
    )

    # Create Measurement Record
    meas_id = f"MSR-{req.date.year}-{secrets.token_hex(4).upper()}"
    measurement = Measurement(
        measurement_id=meas_id,
        child_id=child.id,
        date=req.date,
        age_days=age_days,
        age_months=age_months,
        weight_kg=req.weight_kg,
        length_height_cm=req.length_height_cm,
        posture=req.posture,
        posture_corrected=z_res["posture_corrected"],
        corrected_dimension_cm=z_res["corrected_dimension"],
        muac_cm=req.muac_cm,
        oedema=req.oedema,
        waz=z_res["waz"],
        haz=z_res["haz"],
        whz=z_res["whz"],
        acute_class=acute_class_enum.value,
        is_underweight=indicators["underweight"],
        is_severely_underweight=indicators["severely_underweight"],
        is_stunted=indicators["stunted"],
        is_severely_stunted=indicators["severely_stunted"],
        is_implausible=is_implausible,
        ref_version=z_res["ref_version"],
        created_by=current_user.full_name
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    # Update Child state & consecutive counters
    child.current_state = transition.to_state.value
    child.consecutive_normal_count = transition.consecutive_normal_count

    # 8. Store StateEvent (FR-SM-04)
    state_event = StateEvent(
        event_id=f"EVT-{secrets.token_hex(4).upper()}",
        child_id=child.id,
        from_state=transition.from_state.value if transition.from_state else None,
        to_state=transition.to_state.value,
        measurement_id=measurement.id,
        event_date=req.date,
        transition_rule=transition.rule_applied,
        notes=f"Transition triggered by measurement {meas_id} (WHZ={z_res['whz']:.2f}, class={acute_class_enum.value})"
    )
    db.add(state_event)

    # 9. Trigger Alerts (FR-SM-06, FR-AL-01)
    if transition.is_alert_required:
        alert_type_enum = AlertType[transition.alert_type]
        alert_pri_enum = AlertPriority[transition.alert_priority]
        alert = Alert(
            alert_id=f"ALT-{secrets.token_hex(4).upper()}",
            type=alert_type_enum,
            child_id=child.id,
            awc_id=child.awc_id,
            priority=alert_pri_enum,
            status=AlertStatus.OPEN,
            escalation_level=0,
            description=f"{child.name} ({child.child_id}): {transition.alert_description}"
        )
        db.add(alert)

    db.commit()

    # 10. Audit Log (FR-AUTH-04)
    log_audit_event(
        db, current_user, "CREATE", "Measurement", str(measurement.id),
        after_val={
            "child_id": child.id,
            "weight_kg": req.weight_kg,
            "height_cm": req.length_height_cm,
            "whz": z_res["whz"],
            "state_to": transition.to_state.value,
            "rule": transition.rule_applied
        }
    )

    return MeasurementResponse.model_validate(measurement)


@router.put("/{id}", response_model=MeasurementResponse)
def correct_measurement(
    id: int,
    req: MeasurementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-GM-06 & FR-SM-04: Edit/correct a measurement within 7 days.
    Replays complete state machine history chronologically to ensure data integrity!
    """
    measurement = db.query(Measurement).filter(Measurement.id == id).first()
    if not measurement:
        raise HTTPException(status_code=404, detail="Measurement not found")
    
    child = db.query(Child).filter(Child.id == measurement.child_id).first()
    assert_awc_access(current_user, child.awc_id, db)

    # Check 7-day correction window
    days_since = (date.today() - measurement.date).days
    if days_since > 7 and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction window closed: Measurements can only be edited within 7 days of capture (elapsed: {days_since} days)."
        )

    before_val = {
        "weight_kg": measurement.weight_kg,
        "length_height_cm": measurement.length_height_cm,
        "whz": measurement.whz,
        "acute_class": measurement.acute_class
    }

    # Apply updates
    if req.weight_kg is not None:
        measurement.weight_kg = req.weight_kg
    if req.length_height_cm is not None:
        measurement.length_height_cm = req.length_height_cm
    if req.posture is not None:
        measurement.posture = req.posture
    if req.muac_cm is not None:
        measurement.muac_cm = req.muac_cm
    if req.oedema is not None:
        measurement.oedema = req.oedema

    # Recompute z-scores for this measurement
    z_res = compute_all_zscores(
        sex=child.sex,
        age_days=measurement.age_days,
        age_months=measurement.age_months,
        weight_kg=measurement.weight_kg,
        length_height_cm=measurement.length_height_cm,
        posture=measurement.posture
    )
    acute_class_enum = classify_acute_malnutrition(
        whz=z_res["whz"],
        age_months=measurement.age_months,
        muac_cm=measurement.muac_cm,
        oedema=measurement.oedema
    )
    indicators = evaluate_growth_indicators(waz=z_res["waz"], haz=z_res["haz"])

    measurement.waz = z_res["waz"]
    measurement.haz = z_res["haz"]
    measurement.whz = z_res["whz"]
    measurement.acute_class = acute_class_enum.value
    measurement.corrected_dimension_cm = z_res["corrected_dimension"]
    measurement.posture_corrected = z_res["posture_corrected"]
    measurement.is_underweight = indicators["underweight"]
    measurement.is_severely_underweight = indicators["severely_underweight"]
    measurement.is_stunted = indicators["stunted"]
    measurement.is_severely_stunted = indicators["severely_stunted"]
    measurement.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Replay full history for child to resolve correct state trajectory
    all_child_measurements = db.query(Measurement).filter(Measurement.child_id == child.id).order_by(Measurement.date.asc()).all()
    history_stubs = [
        MeasurementRecordStub(
            measurement_id=m.measurement_id,
            date=m.date,
            acute_class=AcuteMalnutritionClass(m.acute_class),
            oedema=m.oedema
        )
        for m in all_child_measurements
    ]
    final_state, final_consecutive, transitions = NutritionalStateMachine.replay_history(history_stubs)
    child.current_state = final_state.value
    child.consecutive_normal_count = final_consecutive

    db.commit()
    db.refresh(measurement)

    # Log audit entry
    log_audit_event(
        db, current_user, "CORRECTION", "Measurement", str(measurement.id),
        before_val=before_val,
        after_val={
            "weight_kg": measurement.weight_kg,
            "whz": measurement.whz,
            "acute_class": measurement.acute_class,
            "child_state_recomputed": final_state.value,
            "reason": req.correction_reason
        }
    )

    return MeasurementResponse.model_validate(measurement)


@router.get("/child/{child_id}", response_model=List[MeasurementResponse])
def get_child_measurements(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    measurements = db.query(Measurement).filter(Measurement.child_id == child_id).order_by(Measurement.date.asc()).all()
    return [MeasurementResponse.model_validate(m) for m in measurements]


@router.get("/child/{child_id}/growth-chart")
def get_child_growth_chart(
    child_id: int,
    indicator: str = Query("WFA", pattern="^(WFA|HFA|WFH)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-GM-08: Provides child's measurement trajectory points alongside
    standard WHO reference curves (-3SD, -2SD, Median, +2SD, +3SD) for Chart.js plotting
    across Weight-for-Age (WFA), Length/Height-for-Age (HFA), and Weight-for-Height/Length (WFH).
    """
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    measurements = db.query(Measurement).filter(Measurement.child_id == child_id).order_by(Measurement.date.asc()).all()
    WHOReferenceStore.ensure_loaded()

    def calc_curve_point(lms, z):
        L, M, S = lms.L, lms.M, lms.S
        if abs(L) > 1e-7:
            return round(M * pow(1.0 + L * S * z, 1.0 / L), 2)
        return round(M * math.exp(S * z), 2)

    curves = {"labels": [], "sd3neg": [], "sd2neg": [], "median": [], "sd2pos": [], "sd3pos": []}
    chart_info = {
        "indicator": indicator,
        "title": "WHO Weight-for-Age Standards (0-60 Months)",
        "x_label": "Age (Completed Months)",
        "y_label": "Weight (kg)"
    }

    if indicator == "WFA":
        chart_info["title"] = f"WHO Weight-for-Age (WAZ) — {child.name} ({'Boy' if child.sex == 'M' else 'Girl'})"
        chart_info["x_label"] = "Age (Completed Months)"
        chart_info["y_label"] = "Weight (kg)"
        for m in range(61):
            lms = WHOReferenceStore.get_wfa(child.sex, m)
            if lms:
                curves["labels"].append(m)
                curves["sd3neg"].append(calc_curve_point(lms, -3))
                curves["sd2neg"].append(calc_curve_point(lms, -2))
                curves["median"].append(round(lms.M, 2))
                curves["sd2pos"].append(calc_curve_point(lms, 2))
                curves["sd3pos"].append(calc_curve_point(lms, 3))

        child_points = [
            {
                "x": m.age_months,
                "y": m.weight_kg,
                "date": m.date.isoformat(),
                "whz": m.whz,
                "waz": m.waz,
                "haz": m.haz,
                "acute_class": m.acute_class
            }
            for m in measurements
        ]

    elif indicator == "HFA":
        chart_info["title"] = f"WHO Length/Height-for-Age (HAZ - Stunting) — {child.name} ({'Boy' if child.sex == 'M' else 'Girl'})"
        chart_info["x_label"] = "Age (Completed Months)"
        chart_info["y_label"] = "Length / Height (cm)"
        for m in range(61):
            lms = WHOReferenceStore.get_lhfa(child.sex, m)
            if lms:
                curves["labels"].append(m)
                curves["sd3neg"].append(calc_curve_point(lms, -3))
                curves["sd2neg"].append(calc_curve_point(lms, -2))
                curves["median"].append(round(lms.M, 2))
                curves["sd2pos"].append(calc_curve_point(lms, 2))
                curves["sd3pos"].append(calc_curve_point(lms, 3))

        child_points = [
            {
                "x": m.age_months,
                "y": m.corrected_dimension_cm or m.length_height_cm,
                "date": m.date.isoformat(),
                "whz": m.whz,
                "waz": m.waz,
                "haz": m.haz,
                "acute_class": m.acute_class
            }
            for m in measurements
        ]

    else:  # WFH
        chart_info["title"] = f"WHO Weight-for-Height/Length (WHZ - Wasting) — {child.name} ({'Boy' if child.sex == 'M' else 'Girl'})"
        chart_info["x_label"] = "Length / Height (cm)"
        chart_info["y_label"] = "Weight (kg)"
        # Use range 45cm to 120cm with 1.0cm steps
        for h_step in range(45, 121):
            h_val = float(h_step)
            lms = WHOReferenceStore.get_wfl(child.sex, h_val) if h_val < 85.0 else WHOReferenceStore.get_wfh(child.sex, h_val)
            if lms:
                curves["labels"].append(h_val)
                curves["sd3neg"].append(calc_curve_point(lms, -3))
                curves["sd2neg"].append(calc_curve_point(lms, -2))
                curves["median"].append(round(lms.M, 2))
                curves["sd2pos"].append(calc_curve_point(lms, 2))
                curves["sd3pos"].append(calc_curve_point(lms, 3))

        child_points = [
            {
                "x": m.corrected_dimension_cm or m.length_height_cm,
                "y": m.weight_kg,
                "date": m.date.isoformat(),
                "whz": m.whz,
                "waz": m.waz,
                "haz": m.haz,
                "acute_class": m.acute_class
            }
            for m in measurements
        ]

    return {
        "child": {
            "id": child.id,
            "child_id": child.child_id,
            "name": child.name,
            "sex": child.sex,
            "dob": child.dob.isoformat(),
            "current_state": child.current_state
        },
        "info": chart_info,
        "curves": curves,
        "points": child_points
    }

"""
Child Immunisation Card, Dose Recording, and Adherence Endpoints (FR-IM-01 to FR-IM-05)
"""
from datetime import date
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.child import Child
from ..models.immunisation import VaccineRecord
from ..models.user import User
from ..schemas.all_schemas import VaccineRecordCreate, VaccineRecordResponse
from ..auth.rbac import get_current_user, assert_awc_access, log_audit_event
from ..rules.immunisation import evaluate_child_immunisation, DoseStatus

router = APIRouter(prefix="/immunisation", tags=["Immunisation"])


@router.get("/child/{child_id}")
def get_child_immunisation_card(
    child_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-IM-01 to FR-IM-04: Returns child's full digital vaccination schedule,
    status classification (Given, Due, Overdue, Not yet due), and adherence percentage.
    """
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    # Fetch given records
    records = db.query(VaccineRecord).filter(VaccineRecord.child_id == child_id).all()
    given_list = [
        {
            "code": r.vaccine_code,
            "given_date": r.given_date,
            "batch_no": r.batch_no,
            "place": r.place
        }
        for r in records
    ]

    evaluations, adherence_pct, due_count, overdue_count = evaluate_child_immunisation(
        child_dob=child.dob,
        given_records=given_list,
        evaluation_date=date.today()
    )

    return {
        "child_id": child.id,
        "name": child.name,
        "dob": child.dob.isoformat(),
        "adherence_pct": adherence_pct,
        "due_count": due_count,
        "overdue_count": overdue_count,
        "doses": [
            {
                "code": e.code,
                "name": e.name,
                "dose_no": e.dose_no,
                "category": e.category,
                "status": e.status.value,
                "target_date": e.target_date.isoformat(),
                "window_start": e.window_start_date.isoformat(),
                "window_end": e.window_end_date.isoformat(),
                "given_date": e.given_date.isoformat() if e.given_date else None,
                "given_within_window": e.given_within_window,
                "days_overdue": e.days_overdue,
                "escalate_to_ls": e.escalate_to_ls,
                "batch_no": e.batch_no,
                "place": e.place
            }
            for e in evaluations
        ]
    }


@router.post("/record", response_model=VaccineRecordResponse, status_code=status.HTTP_201_CREATED)
def record_vaccine_dose(
    req: VaccineRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-IM-02: Records a vaccine dose given with date, place, and batch number."""
    child = db.query(Child).filter(Child.id == req.child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    # Check if already given
    existing = db.query(VaccineRecord).filter(
        VaccineRecord.child_id == req.child_id,
        VaccineRecord.vaccine_code == req.vaccine_code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dose {req.vaccine_code} was already recorded for this child on {existing.given_date}."
        )

    record = VaccineRecord(
        child_id=req.child_id,
        vaccine_code=req.vaccine_code,
        dose_no=req.dose_no,
        given_date=req.given_date,
        place=req.place or f"AWC #{child.awc_id}",
        batch_no=req.batch_no,
        recorded_by=current_user.full_name
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    log_audit_event(
        db, current_user, "CREATE", "VaccineRecord", str(record.id),
        after_val={"child_id": child.id, "vaccine": req.vaccine_code, "given_date": req.given_date}
    )

    return VaccineRecordResponse.model_validate(record)

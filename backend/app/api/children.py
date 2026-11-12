"""
Child Registration, Transfer, Status Management, and Duplicate Detection (FR-REG-01 to FR-REG-06)
"""
from datetime import date, datetime
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.child import Child, ChildStatus, ChildTransferHistory
from ..models.hierarchy import AWC
from ..models.user import User
from ..schemas.all_schemas import (
    ChildCreate, ChildUpdate, ChildResponse, ChildTransferRequest, ChildStatusUpdateRequest
)
from ..auth.rbac import (
    get_current_user, assert_awc_access, get_user_accessible_awc_ids, log_audit_event
)

router = APIRouter(prefix="/children", tags=["Children"])


def calculate_age_months(dob: date, ref_date: Optional[date] = None) -> int:
    ref = ref_date or date.today()
    return max(0, (ref.year - dob.year) * 12 + ref.month - dob.month - (1 if ref.day < dob.day else 0))


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
def register_child(
    req: ChildCreate,
    force_duplicate: bool = Query(False, description="Bypass duplicate warning"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-REG-01: Registers a new child with guardian consent, birth weight, and age validation."""
    # 1. RBAC check: AWW can only register children in their assigned AWC
    assert_awc_access(current_user, req.awc_id, db)

    reg_date = req.registration_date or date.today()

    # 2. FR-REG-02: Reject registration of children whose age on reg date is 72 months or more
    age_months_at_reg = calculate_age_months(req.dob, reg_date)
    if age_months_at_reg >= 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration rejected: Child is {age_months_at_reg} months old. ACGMS covers children under 6 years (0-71 months)."
        )

    # 3. FR-REG-03: Duplicate detection (same name, DOB, guardian, AWC)
    existing = db.query(Child).filter(
        Child.name.ilike(req.name.strip()),
        Child.dob == req.dob,
        Child.guardian_name.ilike(req.guardian_name.strip()),
        Child.awc_id == req.awc_id
    ).first()

    if existing and not force_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Possible duplicate detected: Child '{existing.name}' (ID: {existing.child_id}) already exists with same DOB and Guardian at this AWC. Set force_duplicate=true to override."
        )

    # Generate unique child ID: CHD-YYYY-XXXX
    child_id = f"CHD-{reg_date.year}-{secrets.token_hex(3).upper()}"

    # Determine low birth weight (< 2.5 kg per WHO/MoHFW guidelines)
    is_lbw = req.is_low_birth_weight
    if req.birth_weight_kg is not None and req.birth_weight_kg < 2.5:
        is_lbw = True

    child = Child(
        child_id=child_id,
        name=req.name.strip(),
        sex=req.sex.upper(),
        dob=req.dob,
        guardian_name=req.guardian_name.strip(),
        guardian_relationship=req.guardian_relationship,
        mobile=req.mobile,
        guardian_consent_sms=req.guardian_consent_sms,
        address_village=req.address_village.strip(),
        awc_id=req.awc_id,
        registration_date=reg_date,
        birth_weight_kg=req.birth_weight_kg,
        is_low_birth_weight=is_lbw,
        status=ChildStatus.ACTIVE,
        current_state="Normal",
        consecutive_normal_count=0
    )
    db.add(child)
    db.commit()
    db.refresh(child)

    log_audit_event(
        db, current_user, "CREATE", "Child", str(child.id),
        after_val={"child_id": child.child_id, "name": child.name, "awc_id": child.awc_id}
    )

    resp = ChildResponse.model_validate(child)
    resp.age_months = calculate_age_months(child.dob)
    return resp


@router.get("", response_model=List[ChildResponse])
def list_children(
    awc_id: Optional[int] = None,
    status_filter: Optional[ChildStatus] = None,
    nutritional_state: Optional[str] = None,
    age_group: Optional[str] = None,  # "0-6", "6-24", "24-36", "36-72"
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists children with RBAC jurisdiction filtering, search, and demographics filters."""
    accessible_ids = get_user_accessible_awc_ids(current_user, db)
    query = db.query(Child)

    if accessible_ids is not None:
        query = query.filter(Child.awc_id.in_(accessible_ids))

    if awc_id:
        assert_awc_access(current_user, awc_id, db)
        query = query.filter(Child.awc_id == awc_id)

    if status_filter:
        query = query.filter(Child.status == status_filter)

    if nutritional_state:
        query = query.filter(Child.current_state == nutritional_state)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Child.name.ilike(s)) |
            (Child.child_id.ilike(s)) |
            (Child.guardian_name.ilike(s)) |
            (Child.address_village.ilike(s))
        )

    children = query.order_by(Child.name.asc()).all()
    results = []

    today = date.today()
    for c in children:
        age_m = calculate_age_months(c.dob, today)
        
        # FR-REG-02: Auto-graduation check when turning 6 (72 months)
        if age_m >= 72 and c.status == ChildStatus.ACTIVE:
            c.status = ChildStatus.GRADUATED
            c.status_reason = "Automatically graduated upon reaching 6 years (72 months)"
            c.status_date = today
            db.commit()

        # Age group filtering if specified
        if age_group:
            if age_group == "0-6" and not (0 <= age_m < 6):
                continue
            elif age_group == "6-24" and not (6 <= age_m < 24):
                continue
            elif age_group == "24-36" and not (24 <= age_m < 36):
                continue
            elif age_group == "36-72" and not (36 <= age_m < 72):
                continue

        resp = ChildResponse.model_validate(c)
        resp.age_months = age_m
        results.append(resp)

    return results


@router.get("/{id}", response_model=ChildResponse)
def get_child(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    child = db.query(Child).filter(Child.id == id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)
    resp = ChildResponse.model_validate(child)
    resp.age_months = calculate_age_months(child.dob)
    return resp


@router.put("/{id}", response_model=ChildResponse)
def update_child(
    id: int,
    req: ChildUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    child = db.query(Child).filter(Child.id == id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    before_val = {"name": child.name, "guardian_name": child.guardian_name, "mobile": child.mobile}

    if req.name is not None:
        child.name = req.name.strip()
    if req.guardian_name is not None:
        child.guardian_name = req.guardian_name.strip()
    if req.guardian_relationship is not None:
        child.guardian_relationship = req.guardian_relationship
    if req.mobile is not None:
        child.mobile = req.mobile
    if req.address_village is not None:
        child.address_village = req.address_village.strip()

    db.commit()
    db.refresh(child)

    log_audit_event(
        db, current_user, "UPDATE", "Child", str(child.id),
        before_val=before_val, after_val={"name": child.name, "guardian_name": child.guardian_name, "mobile": child.mobile}
    )

    resp = ChildResponse.model_validate(child)
    resp.age_months = calculate_age_months(child.dob)
    return resp


@router.post("/{id}/transfer")
def transfer_child(
    id: int,
    req: ChildTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-REG-04: Transfers child to another AWC with transfer history audit."""
    child = db.query(Child).filter(Child.id == id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    target_awc = db.query(AWC).filter(AWC.id == req.target_awc_id).first()
    if not target_awc:
        raise HTTPException(status_code=404, detail="Target AWC not found")

    old_awc_id = child.awc_id
    child.awc_id = req.target_awc_id

    transfer_record = ChildTransferHistory(
        child_id=child.id,
        from_awc_id=old_awc_id,
        to_awc_id=req.target_awc_id,
        transfer_date=date.today(),
        reason=req.reason,
        transferred_by=current_user.full_name
    )
    db.add(transfer_record)
    db.commit()

    log_audit_event(
        db, current_user, "TRANSFER", "Child", str(child.id),
        before_val={"awc_id": old_awc_id}, after_val={"awc_id": req.target_awc_id, "reason": req.reason}
    )

    return {"message": f"Child transferred successfully from AWC #{old_awc_id} to AWC #{req.target_awc_id}"}


@router.post("/{id}/status")
def update_child_status(
    id: int,
    req: ChildStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """FR-REG-05: Mark child as migrated, deceased, or inactive with reason and date."""
    child = db.query(Child).filter(Child.id == id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    assert_awc_access(current_user, child.awc_id, db)

    before_val = {"status": child.status.value, "reason": child.status_reason}
    child.status = req.status
    child.status_reason = req.reason
    child.status_date = req.status_date or date.today()
    db.commit()

    log_audit_event(
        db, current_user, "STATUS_CHANGE", "Child", str(child.id),
        before_val=before_val, after_val={"status": req.status.value, "reason": req.reason}
    )

    return {"message": f"Child status updated to {req.status.value}"}

"""
Master Data Hierarchy and Reference Schedule Endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.hierarchy import District, Block, Sector, AWC
from ..models.user import User, UserRole
from ..models.audit import SystemConfig
from ..auth.rbac import get_current_user, require_roles, get_user_accessible_awc_ids, log_audit_event
from ..rules.immunisation import ImmunisationScheduleStore

router = APIRouter(prefix="/master", tags=["Master Data"])

@router.get("/hierarchy")
def get_hierarchy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns complete District -> Block -> Sector -> AWC hierarchy tree."""
    districts = db.query(District).all()
    out = []
    for d in districts:
        d_dict = {"id": d.id, "name": d.name, "code": d.code, "blocks": []}
        for b in d.blocks:
            b_dict = {"id": b.id, "name": b.name, "code": b.code, "sectors": []}
            for s in b.sectors:
                s_dict = {
                    "id": s.id,
                    "name": s.name,
                    "code": s.code,
                    "supervisor_id": s.supervisor_id,
                    "awcs": [{"id": a.id, "code": a.code, "name": a.name, "village": a.village} for a in s.awcs]
                }
                b_dict["sectors"].append(s_dict)
            d_dict["blocks"].append(b_dict)
        out.append(d_dict)
    return out

@router.get("/awcs")
def get_awcs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns accessible AWCs according to user's RBAC scope."""
    accessible_ids = get_user_accessible_awc_ids(current_user, db)
    query = db.query(AWC)
    if accessible_ids is not None:
        query = query.filter(AWC.id.in_(accessible_ids))
    awcs = query.all()
    return [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "village": a.village,
            "sector_id": a.sector_id,
            "sector_name": a.sector.name if a.sector else "",
            "block_name": a.sector.block.name if a.sector and a.sector.block else "",
            "district_name": a.sector.block.district.name if a.sector and a.sector.block and a.sector.block.district else ""
        }
        for a in awcs
    ]

@router.get("/uip-schedule")
def get_uip_schedule():
    """Returns Universal Immunisation Programme schedule definitions."""
    schedule = ImmunisationScheduleStore.get_schedule()
    return [
        {
            "code": s.code,
            "name": s.name,
            "dose_no": s.dose_no,
            "target_days": s.target_days,
            "window_start": s.window_start,
            "window_end": s.window_end,
            "category": s.category,
            "mandatory": s.mandatory
        }
        for s in schedule
    ]

@router.get("/configs")
def get_configs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    configs = db.query(SystemConfig).all()
    return {c.config_key: c.config_value for c in configs}

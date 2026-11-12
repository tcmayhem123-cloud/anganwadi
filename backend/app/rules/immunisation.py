"""
Universal Immunisation Programme (UIP) rules engine.
Complies with MoHFW guidelines and ACGMS SRS Section 3.7 & 6.5.
Pure, stateless schedule generation, status calculation, and adherence computation.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Set

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class DoseStatus(str, Enum):
    GIVEN = "GIVEN"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    NOT_YET_DUE = "NOT_YET_DUE"


@dataclass(frozen=True)
class VaccineDoseDef:
    code: str
    name: str
    dose_no: int
    target_days: int
    window_start: int
    window_end: int
    category: str
    mandatory: bool = True


@dataclass
class ChildDoseEvaluation:
    code: str
    name: str
    dose_no: int
    category: str
    status: DoseStatus
    target_date: date
    window_start_date: date
    window_end_date: date
    given_date: Optional[date]
    given_within_window: bool
    days_overdue: int
    escalate_to_ls: bool
    batch_no: Optional[str] = None
    place: Optional[str] = None


class ImmunisationScheduleStore:
    _schedule: List[VaccineDoseDef] = []
    _loaded: bool = False

    @classmethod
    def load(cls, data_dir: Optional[str] = None):
        target_dir = data_dir or DATA_DIR
        path = os.path.join(target_dir, "uip_schedule.json")
        if not os.path.exists(path):
            cls._schedule = []
            return
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
            cls._schedule = [
                VaccineDoseDef(
                    code=d["code"],
                    name=d["name"],
                    dose_no=d["dose_no"],
                    target_days=d["target_days"],
                    window_start=d["window_start"],
                    window_end=d["window_end"],
                    category=d.get("category", "General"),
                    mandatory=d.get("mandatory", True)
                )
                for d in content["schedule"]
            ]
        cls._loaded = True

    @classmethod
    def get_schedule(cls) -> List[VaccineDoseDef]:
        if not cls._loaded:
            cls.load()
        return cls._schedule


def evaluate_child_immunisation(
    child_dob: date,
    given_records: List[Dict],  # list of dicts with {"code": str, "given_date": date, "batch_no": ..., "place": ...}
    evaluation_date: Optional[date] = None
) -> Tuple[List[ChildDoseEvaluation], float, int, int]:
    """FR-IM-01, FR-IM-03, FR-IM-04, FR-IM-05:
    Evaluates status of each scheduled vaccine dose and computes adherence percentage.
    Returns:
    - List of ChildDoseEvaluation
    - adherence_pct (float 0.0 - 100.0)
    - total_due_count
    - total_overdue_count
    """
    ref_date = evaluation_date or date.today()
    child_age_days = (ref_date - child_dob).days

    schedule = ImmunisationScheduleStore.get_schedule()
    given_map: Dict[str, Dict] = {rec["code"]: rec for rec in given_records}

    evaluations: List[ChildDoseEvaluation] = []
    doses_given_in_window = 0
    doses_closed_or_given = 0
    due_count = 0
    overdue_count = 0

    for dose in schedule:
        from datetime import timedelta
        target_date = child_dob + timedelta(days=dose.target_days)
        window_start_date = child_dob + timedelta(days=dose.window_start)
        window_end_date = child_dob + timedelta(days=dose.window_end)

        is_given = dose.code in given_map
        given_rec = given_map.get(dose.code)
        given_date = given_rec["given_date"] if given_rec else None

        if is_given and given_date:
            # Check if given within permitted window
            days_from_dob = (given_date - child_dob).days
            in_window = (dose.window_start <= days_from_dob <= dose.window_end)
            if in_window:
                doses_given_in_window += 1
            doses_closed_or_given += 1

            evaluations.append(ChildDoseEvaluation(
                code=dose.code,
                name=dose.name,
                dose_no=dose.dose_no,
                category=dose.category,
                status=DoseStatus.GIVEN,
                target_date=target_date,
                window_start_date=window_start_date,
                window_end_date=window_end_date,
                given_date=given_date,
                given_within_window=in_window,
                days_overdue=0,
                escalate_to_ls=False,
                batch_no=given_rec.get("batch_no"),
                place=given_rec.get("place")
            ))
        else:
            # Not given
            if child_age_days < dose.window_start:
                # Not yet due
                evaluations.append(ChildDoseEvaluation(
                    code=dose.code,
                    name=dose.name,
                    dose_no=dose.dose_no,
                    category=dose.category,
                    status=DoseStatus.NOT_YET_DUE,
                    target_date=target_date,
                    window_start_date=window_start_date,
                    window_end_date=window_end_date,
                    given_date=None,
                    given_within_window=False,
                    days_overdue=0,
                    escalate_to_ls=False
                ))
            elif child_age_days <= dose.window_end:
                # Due
                due_count += 1
                evaluations.append(ChildDoseEvaluation(
                    code=dose.code,
                    name=dose.name,
                    dose_no=dose.dose_no,
                    category=dose.category,
                    status=DoseStatus.DUE,
                    target_date=target_date,
                    window_start_date=window_start_date,
                    window_end_date=window_end_date,
                    given_date=None,
                    given_within_window=False,
                    days_overdue=0,
                    escalate_to_ls=False
                ))
            else:
                # Overdue
                overdue_count += 1
                doses_closed_or_given += 1
                days_overdue = child_age_days - dose.window_end
                escalate = (days_overdue > 30)  # FR-IM-05: escalate to LS if > 30 days overdue

                evaluations.append(ChildDoseEvaluation(
                    code=dose.code,
                    name=dose.name,
                    dose_no=dose.dose_no,
                    category=dose.category,
                    status=DoseStatus.OVERDUE,
                    target_date=target_date,
                    window_start_date=window_start_date,
                    window_end_date=window_end_date,
                    given_date=None,
                    given_within_window=False,
                    days_overdue=days_overdue,
                    escalate_to_ls=escalate
                ))

    # Adherence % = (doses given within window) / (doses closed or given) * 100
    adherence_pct = 100.0
    if doses_closed_or_given > 0:
        adherence_pct = round((doses_given_in_window / doses_closed_or_given) * 100.0, 1)

    return evaluations, adherence_pct, due_count, overdue_count

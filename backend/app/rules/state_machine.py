"""
Nutritional Status State Machine Module.
Complies with ACGMS SRS Section 6.4 and Table 6.4.
Deterministic, pure function state transitions and event replay.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .classification import AcuteMalnutritionClass


class NutritionalState(str, Enum):
    NORMAL = "Normal"
    MAM = "MAM"
    SAM = "SAM"
    RECOVERING = "Recovering"


@dataclass
class TransitionResult:
    from_state: Optional[NutritionalState]
    to_state: NutritionalState
    rule_applied: str
    is_state_changed: bool
    consecutive_normal_count: int
    is_alert_required: bool
    alert_type: Optional[str]
    alert_priority: Optional[str]
    alert_description: Optional[str]


@dataclass
class MeasurementRecordStub:
    measurement_id: str
    date: date
    acute_class: AcuteMalnutritionClass
    oedema: bool = False


class NutritionalStateMachine:
    """Implements Table 6.4 transition matrix and invariant guards."""

    @staticmethod
    def step(
        current_state: Optional[NutritionalState],
        acute_class: AcuteMalnutritionClass,
        has_oedema: bool = False,
        consecutive_normal_count: int = 0,
        n_recovery_consecutive: int = 2,
        mam_to_normal_count: int = 1
    ) -> TransitionResult:
        """Evaluates single transition step according to Table 6.4."""
        
        # Initial measurement (Child has no prior state)
        if current_state is None:
            if acute_class == AcuteMalnutritionClass.NORMAL:
                return TransitionResult(
                    from_state=None,
                    to_state=NutritionalState.NORMAL,
                    rule_applied="T1",
                    is_state_changed=True,
                    consecutive_normal_count=1,
                    is_alert_required=False,
                    alert_type=None,
                    alert_priority=None,
                    alert_description=None
                )
            elif acute_class == AcuteMalnutritionClass.MAM:
                return TransitionResult(
                    from_state=None,
                    to_state=NutritionalState.MAM,
                    rule_applied="T2",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="NEW_MAM",
                    alert_priority="MEDIUM",
                    alert_description="Initial measurement classified child as MAM."
                )
            else:  # SAM
                return TransitionResult(
                    from_state=None,
                    to_state=NutritionalState.SAM,
                    rule_applied="T3",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="NEW_SAM",
                    alert_priority="HIGH",
                    alert_description="CRITICAL: Initial measurement classified child as SAM. Immediate facility/NRC follow-up needed."
                )

        # From NORMAL
        if current_state == NutritionalState.NORMAL:
            if acute_class == AcuteMalnutritionClass.NORMAL:
                return TransitionResult(
                    from_state=NutritionalState.NORMAL,
                    to_state=NutritionalState.NORMAL,
                    rule_applied="T6",
                    is_state_changed=False,
                    consecutive_normal_count=consecutive_normal_count + 1,
                    is_alert_required=False,
                    alert_type=None,
                    alert_priority=None,
                    alert_description=None
                )
            elif acute_class == AcuteMalnutritionClass.MAM:
                return TransitionResult(
                    from_state=NutritionalState.NORMAL,
                    to_state=NutritionalState.MAM,
                    rule_applied="T4",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="NEW_MAM",
                    alert_priority="MEDIUM",
                    alert_description="Child transitioned from Normal to MAM. Needs dietary supplement & counselling."
                )
            else:  # SAM
                return TransitionResult(
                    from_state=NutritionalState.NORMAL,
                    to_state=NutritionalState.SAM,
                    rule_applied="T5",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="NEW_SAM",
                    alert_priority="HIGH",
                    alert_description="CRITICAL: Child deteriorated directly from Normal to SAM. Immediate urgent intervention required."
                )

        # From MAM
        if current_state == NutritionalState.MAM:
            if acute_class == AcuteMalnutritionClass.SAM:
                return TransitionResult(
                    from_state=NutritionalState.MAM,
                    to_state=NutritionalState.SAM,
                    rule_applied="T7",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="NEW_SAM",
                    alert_priority="HIGH",
                    alert_description="CRITICAL: MAM child deteriorated to SAM. Immediate medical referral required."
                )
            elif acute_class == AcuteMalnutritionClass.NORMAL:
                new_count = consecutive_normal_count + 1
                if new_count >= mam_to_normal_count:
                    return TransitionResult(
                        from_state=NutritionalState.MAM,
                        to_state=NutritionalState.NORMAL,
                        rule_applied="T8",
                        is_state_changed=True,
                        consecutive_normal_count=new_count,
                        is_alert_required=False,
                        alert_type=None,
                        alert_priority=None,
                        alert_description=None
                    )
                else:
                    return TransitionResult(
                        from_state=NutritionalState.MAM,
                        to_state=NutritionalState.MAM,
                        rule_applied="T9",
                        is_state_changed=False,
                        consecutive_normal_count=new_count,
                        is_alert_required=False,
                        alert_type=None,
                        alert_priority=None,
                        alert_description=None
                    )
            else:  # MAM
                return TransitionResult(
                    from_state=NutritionalState.MAM,
                    to_state=NutritionalState.MAM,
                    rule_applied="T9",
                    is_state_changed=False,
                    consecutive_normal_count=0,
                    is_alert_required=False,
                    alert_type=None,
                    alert_priority=None,
                    alert_description=None
                )

        # From SAM
        if current_state == NutritionalState.SAM:
            if acute_class == AcuteMalnutritionClass.SAM:
                return TransitionResult(
                    from_state=NutritionalState.SAM,
                    to_state=NutritionalState.SAM,
                    rule_applied="T11",
                    is_state_changed=False,
                    consecutive_normal_count=0,
                    is_alert_required=False,
                    alert_type=None,
                    alert_priority=None,
                    alert_description=None
                )
            else:
                # Acute class improves to MAM or Normal and no oedema -> T10: moves to RECOVERING
                # Invariant: A SAM child NEVER moves directly to Normal!
                if has_oedema:
                    # Oedema forces SAM continuation
                    return TransitionResult(
                        from_state=NutritionalState.SAM,
                        to_state=NutritionalState.SAM,
                        rule_applied="T11",
                        is_state_changed=False,
                        consecutive_normal_count=0,
                        is_alert_required=False,
                        alert_type=None,
                        alert_priority=None,
                        alert_description=None
                    )
                
                new_norm_count = 1 if acute_class == AcuteMalnutritionClass.NORMAL else 0
                return TransitionResult(
                    from_state=NutritionalState.SAM,
                    to_state=NutritionalState.RECOVERING,
                    rule_applied="T10",
                    is_state_changed=True,
                    consecutive_normal_count=new_norm_count,
                    is_alert_required=False,
                    alert_type=None,
                    alert_priority=None,
                    alert_description=None
                )

        # From RECOVERING
        if current_state == NutritionalState.RECOVERING:
            if acute_class == AcuteMalnutritionClass.SAM:
                return TransitionResult(
                    from_state=NutritionalState.RECOVERING,
                    to_state=NutritionalState.SAM,
                    rule_applied="T12",
                    is_state_changed=True,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="SAM_RELAPSE",
                    alert_priority="HIGH",
                    alert_description="CRITICAL RELAPSE: Recovering child relapsed into SAM! Immediate escalation required."
                )
            elif acute_class == AcuteMalnutritionClass.MAM:
                return TransitionResult(
                    from_state=NutritionalState.RECOVERING,
                    to_state=NutritionalState.RECOVERING,
                    rule_applied="T14",
                    is_state_changed=False,
                    consecutive_normal_count=0,
                    is_alert_required=True,
                    alert_type="MAM_RELAPSE",
                    alert_priority="MEDIUM",
                    alert_description="Recovering child regressed to MAM range. Continues in Recovering with intensified monitoring."
                )
            else:  # Normal
                new_count = consecutive_normal_count + 1
                if new_count >= n_recovery_consecutive:
                    return TransitionResult(
                        from_state=NutritionalState.RECOVERING,
                        to_state=NutritionalState.NORMAL,
                        rule_applied="T13",
                        is_state_changed=True,
                        consecutive_normal_count=new_count,
                        is_alert_required=False,
                        alert_type=None,
                        alert_priority=None,
                        alert_description=None
                    )
                else:
                    return TransitionResult(
                        from_state=NutritionalState.RECOVERING,
                        to_state=NutritionalState.RECOVERING,
                        rule_applied="T15",
                        is_state_changed=False,
                        consecutive_normal_count=new_count,
                        is_alert_required=False,
                        alert_type=None,
                        alert_priority=None,
                        alert_description=None
                    )

        raise ValueError(f"Unrecognized state machine input: state={current_state}, acute_class={acute_class}")

    @classmethod
    def replay_history(
        cls,
        measurements: List[MeasurementRecordStub],
        n_recovery_consecutive: int = 2,
        mam_to_normal_count: int = 1
    ) -> Tuple[NutritionalState, int, List[TransitionResult]]:
        """Recomputes full nutritional state progression from ordered historical measurements.
        Enables clean correction replay (FR-SM-04).
        """
        sorted_records = sorted(measurements, key=lambda m: m.date)
        current_state: Optional[NutritionalState] = None
        consecutive_norm = 0
        results: List[TransitionResult] = []

        for m in sorted_records:
            res = cls.step(
                current_state=current_state,
                acute_class=m.acute_class,
                has_oedema=m.oedema,
                consecutive_normal_count=consecutive_norm,
                n_recovery_consecutive=n_recovery_consecutive,
                mam_to_normal_count=mam_to_normal_count
            )
            current_state = res.to_state
            consecutive_norm = res.consecutive_normal_count
            results.append(res)

        final_state = current_state or NutritionalState.NORMAL
        return final_state, consecutive_norm, results

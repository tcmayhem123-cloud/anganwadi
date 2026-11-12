"""
Comprehensive Unit Tests for Pure Business Rules Engine.
Tests WHO LMS Z-Score engine, Classification logic, State Machine transitions (T1-T15),
and UIP Immunisation adherence calculations.
"""
import pytest
from datetime import date, timedelta
from app.rules.zscore import (
    WHOReferenceStore,
    calculate_base_zscore,
    apply_who_extreme_tail_adjustment,
    correct_posture,
    compute_all_zscores,
    LMSParams
)
from app.rules.classification import (
    AcuteMalnutritionClass,
    validate_biological_ranges,
    check_zscore_plausibility,
    classify_acute_malnutrition,
    evaluate_growth_indicators
)
from app.rules.state_machine import (
    NutritionalState,
    NutritionalStateMachine,
    MeasurementRecordStub
)
from app.rules.immunisation import (
    DoseStatus,
    evaluate_child_immunisation,
    ImmunisationScheduleStore
)


# ==========================================
# 1. Z-SCORE & WHO LMS TESTS
# ==========================================

def test_who_reference_store_loading():
    WHOReferenceStore.load()
    # Check birth and 12-month parameters exist
    wfa_m0 = WHOReferenceStore.get_wfa("M", 0)
    assert wfa_m0 is not None
    assert 3.3 <= wfa_m0.M <= 3.4

    lhfa_f12 = WHOReferenceStore.get_lhfa("F", 12)
    assert lhfa_f12 is not None
    assert round(lhfa_f12.M, 1) == 74.0


def test_lms_formula_zero_lambda():
    # L = 0 formula: ln(X / M) / S
    lms_zero = LMSParams(L=0.0, M=10.0, S=0.1)
    # When X == M, z should be 0
    z_med = calculate_base_zscore(10.0, lms_zero)
    assert abs(z_med - 0.0) < 1e-4

    # When X = 11.0517 (approx e^0.1 * 10), z should be ~ 1.0
    z_pos = calculate_base_zscore(11.051709, lms_zero)
    assert abs(z_pos - 1.0) < 1e-3


def test_posture_correction():
    # Under 24 months, measured standing -> should add +0.7 cm
    corrected, was_corrected = correct_posture(18, 80.0, "STANDING")
    assert was_corrected is True
    assert corrected == 80.7

    # 24 months or older, measured recumbent/lying -> should subtract -0.7 cm
    corrected, was_corrected = correct_posture(36, 95.0, "RECUMBENT")
    assert was_corrected is True
    assert corrected == 94.3

    # Normal posture matches age -> no correction
    corrected, was_corrected = correct_posture(10, 72.0, "RECUMBENT")
    assert was_corrected is False
    assert corrected == 72.0


def test_who_extreme_tail_adjustment():
    lms = LMSParams(L=-0.2, M=10.0, S=0.1)
    # Base z within [-3, 3] should remain identical
    assert apply_who_extreme_tail_adjustment(10.0, lms, 0.0) == 0.0
    assert apply_who_extreme_tail_adjustment(12.0, lms, 1.8) == 1.8

    # Base z > 3 or < -3 should trigger tail extrapolation
    ext_z_neg = apply_who_extreme_tail_adjustment(5.0, lms, -3.8)
    assert ext_z_neg < -3.0
    ext_z_pos = apply_who_extreme_tail_adjustment(18.0, lms, 4.2)
    assert ext_z_pos > 3.0


def test_compute_all_zscores_bounds():
    # 6-month-old boy: 7.9 kg weight and 67.6 cm length (matches WHO median closely)
    res = compute_all_zscores(
        sex="M",
        age_days=180,
        age_months=6,
        weight_kg=7.9,
        length_height_cm=67.6,
        posture="RECUMBENT"
    )
    assert abs(res["waz"]) < 0.2
    assert abs(res["haz"]) < 0.2
    assert abs(res["whz"]) < 0.5


# ==========================================
# 2. CLASSIFICATION & VALIDATION TESTS
# ==========================================

def test_biological_range_validation():
    # Plausible
    res = validate_biological_ranges(weight_kg=9.5, length_height_cm=75.0, muac_cm=14.0)
    assert res.is_valid is True
    assert len(res.errors) == 0

    # Implausible weight (e.g. 0.4 kg or 45 kg)
    res_bad = validate_biological_ranges(weight_kg=0.5, length_height_cm=75.0, muac_cm=14.0)
    assert res_bad.is_valid is False
    assert any("Weight" in err for err in res_bad.errors)


def test_zscore_plausibility():
    # Plausible
    is_implausible, flags = check_zscore_plausibility(waz=-1.5, haz=-0.8, whz=-1.2)
    assert is_implausible is False
    assert len(flags) == 0

    # Implausible WHZ (< -5 or > +5)
    is_implausible, flags = check_zscore_plausibility(waz=-2.0, haz=-1.0, whz=-5.5)
    assert is_implausible is True
    assert len(flags) == 1


def test_acute_malnutrition_classification():
    # Normal: WHZ >= -2.0, MUAC >= 12.5, no oedema
    assert classify_acute_malnutrition(whz=-1.5, age_months=12, muac_cm=13.0, oedema=False) == AcuteMalnutritionClass.NORMAL

    # MAM by WHZ: -3.0 <= WHZ < -2.0
    assert classify_acute_malnutrition(whz=-2.4, age_months=12, muac_cm=13.0, oedema=False) == AcuteMalnutritionClass.MAM

    # MAM by MUAC: 11.5 <= MUAC < 12.5 cm
    assert classify_acute_malnutrition(whz=-1.5, age_months=12, muac_cm=12.0, oedema=False) == AcuteMalnutritionClass.MAM

    # SAM by WHZ: WHZ < -3.0
    assert classify_acute_malnutrition(whz=-3.2, age_months=12, muac_cm=13.0, oedema=False) == AcuteMalnutritionClass.SAM

    # SAM by MUAC: MUAC < 11.5 cm
    assert classify_acute_malnutrition(whz=-1.5, age_months=12, muac_cm=11.2, oedema=False) == AcuteMalnutritionClass.SAM

    # SAM by Bilateral Pitting Oedema: always SAM regardless of WHZ
    assert classify_acute_malnutrition(whz=0.5, age_months=12, muac_cm=14.0, oedema=True) == AcuteMalnutritionClass.SAM


def test_growth_indicator_flags():
    # Underweight & Stunted flags
    ind = evaluate_growth_indicators(waz=-2.5, haz=-3.2)
    assert ind["underweight"] is True
    assert ind["severely_underweight"] is False
    assert ind["stunted"] is True
    assert ind["severely_stunted"] is True


# ==========================================
# 3. STATE MACHINE TESTS (T1 TO T15)
# ==========================================

def test_state_machine_t1_t2_t3_initial():
    # T1: None -> Normal -> Normal
    r1 = NutritionalStateMachine.step(None, AcuteMalnutritionClass.NORMAL)
    assert r1.to_state == NutritionalState.NORMAL
    assert r1.rule_applied == "T1"

    # T2: None -> MAM -> MAM
    r2 = NutritionalStateMachine.step(None, AcuteMalnutritionClass.MAM)
    assert r2.to_state == NutritionalState.MAM
    assert r2.rule_applied == "T2"
    assert r2.is_alert_required is True

    # T3: None -> SAM -> SAM
    r3 = NutritionalStateMachine.step(None, AcuteMalnutritionClass.SAM)
    assert r3.to_state == NutritionalState.SAM
    assert r3.rule_applied == "T3"
    assert r3.alert_priority == "HIGH"


def test_state_machine_from_normal():
    # T6: Normal -> Normal -> Normal
    r6 = NutritionalStateMachine.step(NutritionalState.NORMAL, AcuteMalnutritionClass.NORMAL, consecutive_normal_count=2)
    assert r6.to_state == NutritionalState.NORMAL
    assert r6.rule_applied == "T6"
    assert r6.consecutive_normal_count == 3

    # T4: Normal -> MAM -> MAM
    r4 = NutritionalStateMachine.step(NutritionalState.NORMAL, AcuteMalnutritionClass.MAM)
    assert r4.to_state == NutritionalState.MAM
    assert r4.rule_applied == "T4"
    assert r4.is_alert_required is True

    # T5: Normal -> SAM -> SAM
    r5 = NutritionalStateMachine.step(NutritionalState.NORMAL, AcuteMalnutritionClass.SAM)
    assert r5.to_state == NutritionalState.SAM
    assert r5.rule_applied == "T5"
    assert r5.alert_priority == "HIGH"


def test_state_machine_from_mam():
    # T7: MAM -> SAM -> SAM
    r7 = NutritionalStateMachine.step(NutritionalState.MAM, AcuteMalnutritionClass.SAM)
    assert r7.to_state == NutritionalState.SAM
    assert r7.rule_applied == "T7"

    # T8: MAM -> Normal -> Normal (1 measurement by default)
    r8 = NutritionalStateMachine.step(NutritionalState.MAM, AcuteMalnutritionClass.NORMAL)
    assert r8.to_state == NutritionalState.NORMAL
    assert r8.rule_applied == "T8"

    # T9: MAM -> MAM -> MAM
    r9 = NutritionalStateMachine.step(NutritionalState.MAM, AcuteMalnutritionClass.MAM)
    assert r9.to_state == NutritionalState.MAM
    assert r9.rule_applied == "T9"


def test_state_machine_from_sam_guard_and_recovering():
    # T11: SAM -> SAM -> SAM
    r11 = NutritionalStateMachine.step(NutritionalState.SAM, AcuteMalnutritionClass.SAM)
    assert r11.to_state == NutritionalState.SAM
    assert r11.rule_applied == "T11"

    # CRITICAL INVARIANT: A SAM child NEVER moves directly to Normal!
    # T10: SAM -> Normal (or MAM) without oedema -> RECOVERING (NOT NORMAL!)
    r10 = NutritionalStateMachine.step(NutritionalState.SAM, AcuteMalnutritionClass.NORMAL, has_oedema=False)
    assert r10.to_state == NutritionalState.RECOVERING
    assert r10.rule_applied == "T10"

    # If SAM still has oedema, it stays SAM
    r_oedema = NutritionalStateMachine.step(NutritionalState.SAM, AcuteMalnutritionClass.NORMAL, has_oedema=True)
    assert r_oedema.to_state == NutritionalState.SAM


def test_state_machine_recovering_and_relapse():
    # T12: Recovering -> SAM (Relapse!)
    r12 = NutritionalStateMachine.step(NutritionalState.RECOVERING, AcuteMalnutritionClass.SAM)
    assert r12.to_state == NutritionalState.SAM
    assert r12.rule_applied == "T12"
    assert r12.alert_type == "SAM_RELAPSE"

    # T14: Recovering -> MAM -> Recovering (continues with monitoring)
    r14 = NutritionalStateMachine.step(NutritionalState.RECOVERING, AcuteMalnutritionClass.MAM)
    assert r14.to_state == NutritionalState.RECOVERING
    assert r14.rule_applied == "T14"

    # T15: Recovering -> Normal for 1 month (< N=2 months) -> Stays Recovering
    r15 = NutritionalStateMachine.step(NutritionalState.RECOVERING, AcuteMalnutritionClass.NORMAL, consecutive_normal_count=0, n_recovery_consecutive=2)
    assert r15.to_state == NutritionalState.RECOVERING
    assert r15.rule_applied == "T15"
    assert r15.consecutive_normal_count == 1

    # T13: Recovering -> Normal for 2nd month (>= N=2) -> Moves to NORMAL!
    r13 = NutritionalStateMachine.step(NutritionalState.RECOVERING, AcuteMalnutritionClass.NORMAL, consecutive_normal_count=1, n_recovery_consecutive=2)
    assert r13.to_state == NutritionalState.NORMAL
    assert r13.rule_applied == "T13"


def test_appendix_a_scenario():
    """Verifies the exact scenario described in Appendix A:
    A 14-month-old girl is registered and her first measurement gives WHZ = -3.4, so classed SAM (T3).
    Two months later WHZ = -2.4 (MAM-range, no oedema) -> moves to Recovering (T10).
    Following two monthly measurements WHZ = -1.8 and -1.6 (Normal).
    After the second consecutive Normal result she moves to Normal (T13).
    """
    history = [
        MeasurementRecordStub("M1", date(2026, 1, 10), AcuteMalnutritionClass.SAM),
        MeasurementRecordStub("M2", date(2026, 3, 10), AcuteMalnutritionClass.MAM),
        MeasurementRecordStub("M3", date(2026, 4, 10), AcuteMalnutritionClass.NORMAL),
        MeasurementRecordStub("M4", date(2026, 5, 10), AcuteMalnutritionClass.NORMAL),
    ]
    final_state, consecutive_norm, transitions = NutritionalStateMachine.replay_history(history, n_recovery_consecutive=2)
    
    assert transitions[0].rule_applied == "T3"
    assert transitions[0].to_state == NutritionalState.SAM

    assert transitions[1].rule_applied == "T10"
    assert transitions[1].to_state == NutritionalState.RECOVERING

    assert transitions[2].rule_applied == "T15"
    assert transitions[2].to_state == NutritionalState.RECOVERING

    assert transitions[3].rule_applied == "T13"
    assert transitions[3].to_state == NutritionalState.NORMAL
    assert final_state == NutritionalState.NORMAL


# ==========================================
# 4. IMMUNISATION ENGINE TESTS
# ==========================================

def test_immunisation_schedule_and_adherence():
    dob = date(2026, 1, 1)
    eval_date = date(2026, 5, 1)  # ~120 days old (approx 17 weeks)

    # Recorded vaccines: BCG, OPV_0, HEPB_0 given on time; OPV_1 given at 45 days
    records = [
        {"code": "BCG", "given_date": date(2026, 1, 2), "batch_no": "B123", "place": "AWC Rampur"},
        {"code": "OPV_0", "given_date": date(2026, 1, 2), "batch_no": "O123", "place": "AWC Rampur"},
        {"code": "HEPB_0", "given_date": date(2026, 1, 1), "batch_no": "H123", "place": "AWC Rampur"},
        {"code": "OPV_1", "given_date": date(2026, 2, 15), "batch_no": "O456", "place": "AWC Rampur"}
    ]

    evals, adherence, due_count, overdue_count = evaluate_child_immunisation(dob, records, eval_date)
    assert len(evals) > 10
    assert any(e.code == "BCG" and e.status == DoseStatus.GIVEN for e in evals)
    # At 120 days, doses scheduled for 9 months (270 days) like MR_1 should be NOT_YET_DUE
    mr1 = next(e for e in evals if e.code == "MR_1")
    assert mr1.status == DoseStatus.NOT_YET_DUE
    assert adherence > 0.0

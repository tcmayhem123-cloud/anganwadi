"""
Pure, stateless WHO LMS Z-score computation module.
Complies with WHO Child Growth Standards (0-60 months) and WHO Reference 2007 (61-72 months).
Includes WHO extreme tail adjustment (|z| > 3 for WAZ and WHZ) and posture correction.
"""
from __future__ import annotations
import json
import math
import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

@dataclass(frozen=True)
class LMSParams:
    L: float
    M: float
    S: float


class WHOReferenceStore:
    """Loads and caches versioned WHO LMS tables from JSON files."""
    _wfa_boys: Dict[str, LMSParams] = {}
    _wfa_girls: Dict[str, LMSParams] = {}
    _lhfa_boys: Dict[str, LMSParams] = {}
    _lhfa_girls: Dict[str, LMSParams] = {}
    _wfl_boys: Dict[str, LMSParams] = {}
    _wfl_girls: Dict[str, LMSParams] = {}
    _wfh_boys: Dict[str, LMSParams] = {}
    _wfh_girls: Dict[str, LMSParams] = {}
    _version: str = "WHO_2006_2007"
    _loaded: bool = False

    @classmethod
    def load(cls, data_dir: Optional[str] = None):
        target_dir = data_dir or DATA_DIR
        def _load_file(filename: str) -> Dict[str, LMSParams]:
            path = os.path.join(target_dir, filename)
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)
                return {
                    k: LMSParams(v["L"], v["M"], v["S"])
                    for k, v in content["data"].items()
                }

        cls._wfa_boys = _load_file("who_wfa_boys.json")
        cls._wfa_girls = _load_file("who_wfa_girls.json")
        cls._lhfa_boys = _load_file("who_lhfa_boys.json")
        cls._lhfa_girls = _load_file("who_lhfa_girls.json")
        cls._wfl_boys = _load_file("who_wfl_boys.json")
        cls._wfl_girls = _load_file("who_wfl_girls.json")
        cls._wfh_boys = _load_file("who_wfh_boys.json")
        cls._wfh_girls = _load_file("who_wfh_girls.json")
        cls._loaded = True

    @classmethod
    def ensure_loaded(cls):
        if not cls._loaded:
            cls.load()

    @classmethod
    def get_wfa(cls, sex: str, completed_months: int) -> Optional[LMSParams]:
        cls.ensure_loaded()
        table = cls._wfa_boys if sex.upper() in ("M", "MALE", "BOY") else cls._wfa_girls
        return table.get(str(completed_months))

    @classmethod
    def get_lhfa(cls, sex: str, completed_months: int) -> Optional[LMSParams]:
        cls.ensure_loaded()
        table = cls._lhfa_boys if sex.upper() in ("M", "MALE", "BOY") else cls._lhfa_girls
        return table.get(str(completed_months))

    @classmethod
    def get_wfl(cls, sex: str, length_cm: float) -> Optional[LMSParams]:
        """Interpolates between length rows (0.5cm steps) for exact length."""
        cls.ensure_loaded()
        table = cls._wfl_boys if sex.upper() in ("M", "MALE", "BOY") else cls._wfl_girls
        return cls._interpolate(table, length_cm, 45.0, 110.0)

    @classmethod
    def get_wfh(cls, sex: str, height_cm: float) -> Optional[LMSParams]:
        """Interpolates between height rows (0.5cm steps) for exact height."""
        cls.ensure_loaded()
        table = cls._wfh_boys if sex.upper() in ("M", "MALE", "BOY") else cls._wfh_girls
        return cls._interpolate(table, height_cm, 65.0, 120.0)

    @staticmethod
    def _interpolate(table: Dict[str, LMSParams], val: float, min_val: float, max_val: float) -> Optional[LMSParams]:
        val = max(min_val, min(max_val, val))
        step = 0.5
        lower_key = math.floor(val / step) * step
        upper_key = math.ceil(val / step) * step
        p1 = table.get(f"{lower_key:.1f}")
        p2 = table.get(f"{upper_key:.1f}")

        if not p1 or not p2:
            return p1 or p2

        if lower_key == upper_key:
            return p1

        frac = (val - lower_key) / (upper_key - lower_key)
        interp_L = p1.L + frac * (p2.L - p1.L)
        interp_M = p1.M + frac * (p2.M - p1.M)
        interp_S = p1.S + frac * (p2.S - p1.S)
        return LMSParams(interp_L, interp_M, interp_S)


def calculate_base_zscore(X: float, lms: LMSParams) -> float:
    """Computes base LMS z-score:
    If L != 0: z = ((X / M)^L - 1) / (L * S)
    If L == 0: z = ln(X / M) / S
    """
    if X <= 0 or lms.M <= 0 or lms.S <= 0:
        return 0.0
    if abs(lms.L) > 1e-7:
        return ((pow(X / lms.M, lms.L) - 1.0) / (lms.L * lms.S))
    else:
        return math.log(X / lms.M) / lms.S


def apply_who_extreme_tail_adjustment(X: float, lms: LMSParams, base_z: float) -> float:
    """Applies WHO tail adjustment for weight-based indicators when |z| > 3.
    Linear extrapolation using values at ±2 SD and ±3 SD.
    """
    if abs(base_z) <= 3.0:
        return base_z

    L, M, S = lms.L, lms.M, lms.S
    if abs(L) < 1e-7:
        return base_z

    if base_z > 3.0:
        sd3pos = M * pow(1.0 + L * S * 3.0, 1.0 / L)
        sd2pos = M * pow(1.0 + L * S * 2.0, 1.0 / L)
        sd_diff = sd3pos - sd2pos
        if sd_diff <= 0:
            return base_z
        return 3.0 + (X - sd3pos) / sd_diff
    else:  # base_z < -3.0
        sd3neg = M * pow(1.0 - L * S * 3.0, 1.0 / L)
        sd2neg = M * pow(1.0 - L * S * 2.0, 1.0 / L)
        sd_diff = sd2neg - sd3neg
        if sd_diff <= 0:
            return base_z
        return -3.0 + (X - sd3neg) / sd_diff


def correct_posture(age_months: int, length_height_cm: float, posture: str) -> Tuple[float, bool]:
    """FR-GM-03: Applies ±0.7 cm posture correction when measured with wrong posture.
    - Under 24 months: measured lying down (recumbent). If measured standing, length = height + 0.7 cm.
    - 24 months and above: measured standing. If measured lying down, height = length - 0.7 cm.
    Returns (corrected_dimension, was_corrected).
    """
    posture_upper = posture.strip().upper()
    if age_months < 24 and posture_upper in ("STANDING", "STAND", "H"):
        return round(length_height_cm + 0.7, 1), True
    elif age_months >= 24 and posture_upper in ("RECUMBENT", "LYING", "LIE", "L"):
        return round(length_height_cm - 0.7, 1), True
    return length_height_cm, False


def compute_all_zscores(
    sex: str,
    age_days: int,
    age_months: int,
    weight_kg: float,
    length_height_cm: float,
    posture: str = "RECUMBENT"
) -> Dict[str, float]:
    """Computes WAZ, HAZ, and WHZ for a child.
    Returns dictionary with rounded z-scores (to 2 decimal places) and flags.
    """
    corrected_dim, was_corrected = correct_posture(age_months, length_height_cm, posture)

    # 1. Weight-for-Age (WAZ)
    wfa_lms = WHOReferenceStore.get_wfa(sex, age_months)
    waz = 0.0
    if wfa_lms:
        base_waz = calculate_base_zscore(weight_kg, wfa_lms)
        waz = apply_who_extreme_tail_adjustment(weight_kg, wfa_lms, base_waz)

    # 2. Height/Length-for-Age (HAZ)
    lhfa_lms = WHOReferenceStore.get_lhfa(sex, age_months)
    haz = 0.0
    if lhfa_lms:
        # HAZ uses standard Box-Cox z-score without extreme tail adjustment per WHO specification
        haz = calculate_base_zscore(corrected_dim, lhfa_lms)

    # 3. Weight-for-Height/Length (WHZ)
    whz = 0.0
    if age_months < 24:
        whz_lms = WHOReferenceStore.get_wfl(sex, corrected_dim)
    else:
        whz_lms = WHOReferenceStore.get_wfh(sex, corrected_dim)

    if whz_lms:
        base_whz = calculate_base_zscore(weight_kg, whz_lms)
        whz = apply_who_extreme_tail_adjustment(weight_kg, whz_lms, base_whz)

    return {
        "waz": round(waz, 2),
        "haz": round(haz, 2),
        "whz": round(whz, 2),
        "corrected_dimension": corrected_dim,
        "posture_corrected": was_corrected,
        "ref_version": WHOReferenceStore._version
    }

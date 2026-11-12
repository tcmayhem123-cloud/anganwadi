"""
Pure, stateless nutritional classification and biological validation module.
Complies with WHO Child Growth Standards, MoHFW guidelines, and ACGMS SRS Section 6.3.
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AcuteMalnutritionClass(str, Enum):
    NORMAL = "Normal"
    MAM = "MAM"
    SAM = "SAM"


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str], warnings: List[str]):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


def validate_biological_ranges(
    weight_kg: float,
    length_height_cm: float,
    muac_cm: Optional[float] = None
) -> ValidationResult:
    """FR-GM-04: Validates inputs against plausible biological ranges.
    Weight: 1.0 - 30.0 kg
    Length/Height: 40.0 - 130.0 cm
    MUAC: 7.0 - 25.0 cm
    """
    errors = []
    warnings = []

    if weight_kg < 1.0 or weight_kg > 30.0:
        errors.append(f"Weight ({weight_kg:.1f} kg) is outside biological limits (1.0 to 30.0 kg).")
    elif weight_kg < 2.0 or weight_kg > 25.0:
        warnings.append(f"Weight ({weight_kg:.1f} kg) is unusual for child under 6 years. Please verify scale.")

    if length_height_cm < 40.0 or length_height_cm > 130.0:
        errors.append(f"Length/Height ({length_height_cm:.1f} cm) is outside biological limits (40.0 to 130.0 cm).")
    elif length_height_cm < 45.0 or length_height_cm > 120.0:
        warnings.append(f"Length/Height ({length_height_cm:.1f} cm) is unusual. Please verify measurement board.")

    if muac_cm is not None:
        if muac_cm < 7.0 or muac_cm > 25.0:
            errors.append(f"MUAC ({muac_cm:.1f} cm) is outside biological limits (7.0 to 25.0 cm).")
        elif muac_cm < 9.0 or muac_cm > 20.0:
            warnings.append(f"MUAC ({muac_cm:.1f} cm) is unusual. Please re-check tape placement.")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


def check_zscore_plausibility(waz: float, haz: float, whz: float) -> Tuple[bool, List[str]]:
    """FR-GM-05: Flags implausible z-scores as probable data-entry errors.
    Plausible intervals:
    WHZ: -5.0 to +5.0
    HAZ: -6.0 to +6.0
    WAZ: -6.0 to +5.0
    """
    flags = []
    if whz < -5.0 or whz > 5.0:
        flags.append(f"WHZ ({whz:.2f}) falls outside plausible interval [-5.0, +5.0].")
    if haz < -6.0 or haz > 6.0:
        flags.append(f"HAZ ({haz:.2f}) falls outside plausible interval [-6.0, +6.0].")
    if waz < -6.0 or waz > 5.0:
        flags.append(f"WAZ ({waz:.2f}) falls outside plausible interval [-6.0, +5.0].")

    return len(flags) > 0, flags


def classify_acute_malnutrition(
    whz: float,
    age_months: int,
    muac_cm: Optional[float] = None,
    oedema: bool = False
) -> AcuteMalnutritionClass:
    """FR-ZS-03 / Section 6.3:
    - SAM if: WHZ < -3.00, or MUAC < 11.5 cm (for age 6-59m), or bilateral pitting oedema present.
    - MAM if: -3.00 <= WHZ < -2.00, or 11.5 <= MUAC < 12.5 cm (for age 6-59m), and not SAM.
    - Normal: otherwise.
    Returns the most severe class produced by WHZ, MUAC, or oedema.
    """
    # 1. Bilateral pitting oedema is always SAM
    if oedema:
        return AcuteMalnutritionClass.SAM

    # 2. Check for SAM triggers
    if whz < -3.00:
        return AcuteMalnutritionClass.SAM
    if muac_cm is not None and 6 <= age_months <= 59:
        if muac_cm < 11.5:
            return AcuteMalnutritionClass.SAM

    # 3. Check for MAM triggers
    if -3.00 <= whz < -2.00:
        return AcuteMalnutritionClass.MAM
    if muac_cm is not None and 6 <= age_months <= 59:
        if 11.5 <= muac_cm < 12.5:
            return AcuteMalnutritionClass.MAM

    # 4. Otherwise Normal
    return AcuteMalnutritionClass.NORMAL


def evaluate_growth_indicators(waz: float, haz: float) -> Dict[str, bool]:
    """FR-ZS-04: Flags Underweight and Stunting as separate indicators.
    - Underweight: WAZ < -2.00 (Severe: WAZ < -3.00)
    - Stunted: HAZ < -2.00 (Severe: HAZ < -3.00)
    """
    return {
        "underweight": waz < -2.00,
        "severely_underweight": waz < -3.00,
        "stunted": haz < -2.00,
        "severely_stunted": haz < -3.00
    }

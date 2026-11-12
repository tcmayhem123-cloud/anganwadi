"""
Pydantic schemas for ACGMS requests and responses.
"""
from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from ..models.user import UserRole, JurisdictionType
from ..models.child import ChildStatus
from ..models.alert import AlertType, AlertPriority, AlertStatus


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str
    otp: Optional[str] = None  # FR-AUTH-01 optional OTP

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    mobile: Optional[str]
    jurisdiction_type: JurisdictionType
    jurisdiction_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Hierarchy
class AWCCreate(BaseModel):
    sector_id: int
    code: str
    name: str
    village: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None

class AWCResponse(BaseModel):
    id: int
    sector_id: int
    code: str
    name: str
    village: str
    latitude: Optional[str]
    longitude: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class SectorResponse(BaseModel):
    id: int
    block_id: int
    code: str
    name: str
    supervisor_id: Optional[int]
    awcs: List[AWCResponse] = []

    model_config = ConfigDict(from_attributes=True)

class BlockResponse(BaseModel):
    id: int
    district_id: int
    code: str
    name: str
    sectors: List[SectorResponse] = []

    model_config = ConfigDict(from_attributes=True)

class DistrictResponse(BaseModel):
    id: int
    code: str
    name: str
    blocks: List[BlockResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Child
class ChildCreate(BaseModel):
    name: str
    sex: str = Field(..., pattern="^(M|F)$")
    dob: date
    guardian_name: str
    guardian_relationship: str = "Mother"
    mobile: Optional[str] = None
    guardian_consent_sms: bool = True
    address_village: str
    awc_id: int
    registration_date: Optional[date] = None
    birth_weight_kg: Optional[float] = None
    is_low_birth_weight: bool = False

class ChildUpdate(BaseModel):
    name: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_relationship: Optional[str] = None
    mobile: Optional[str] = None
    address_village: Optional[str] = None

class ChildTransferRequest(BaseModel):
    target_awc_id: int
    reason: str

class ChildStatusUpdateRequest(BaseModel):
    status: ChildStatus
    reason: str
    status_date: Optional[date] = None

class ChildResponse(BaseModel):
    id: int
    child_id: str
    name: str
    sex: str
    dob: date
    guardian_name: str
    guardian_relationship: str
    mobile: Optional[str]
    address_village: str
    awc_id: int
    registration_date: date
    birth_weight_kg: Optional[float]
    is_low_birth_weight: bool
    status: ChildStatus
    status_reason: Optional[str]
    status_date: Optional[date]
    current_state: str
    consecutive_normal_count: int
    created_at: datetime
    age_months: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# Measurement
class MeasurementCreate(BaseModel):
    child_id: int
    date: date
    weight_kg: float
    length_height_cm: float
    posture: str = "RECUMBENT"
    muac_cm: Optional[float] = None
    oedema: bool = False
    confirm_implausible: bool = False  # Set to true if AWW confirms extreme z-score

class MeasurementUpdate(BaseModel):
    """Allows correcting measurement within 7 days (FR-GM-06)."""
    weight_kg: Optional[float] = None
    length_height_cm: Optional[float] = None
    posture: Optional[str] = None
    muac_cm: Optional[float] = None
    oedema: Optional[bool] = None
    correction_reason: str

class MeasurementResponse(BaseModel):
    id: int
    measurement_id: str
    child_id: int
    date: date
    age_days: int
    age_months: int
    weight_kg: float
    length_height_cm: float
    posture: str
    posture_corrected: bool
    corrected_dimension_cm: float
    muac_cm: Optional[float]
    oedema: bool
    waz: float
    haz: float
    whz: float
    acute_class: str
    is_underweight: bool
    is_severely_underweight: bool
    is_stunted: bool
    is_severely_stunted: bool
    is_implausible: bool
    ref_version: str
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ZScorePreviewRequest(BaseModel):
    sex: str
    dob: date
    measurement_date: date
    weight_kg: float
    length_height_cm: float
    posture: str = "RECUMBENT"
    muac_cm: Optional[float] = None
    oedema: bool = False


# Immunisation
class VaccineRecordCreate(BaseModel):
    child_id: int
    vaccine_code: str
    dose_no: int = 1
    given_date: date
    place: Optional[str] = None
    batch_no: Optional[str] = None

class VaccineRecordResponse(BaseModel):
    id: int
    child_id: int
    vaccine_code: str
    dose_no: int
    given_date: date
    place: Optional[str]
    batch_no: Optional[str]
    recorded_by: str

    model_config = ConfigDict(from_attributes=True)


# Alerts
class AlertResponse(BaseModel):
    id: int
    alert_id: str
    type: AlertType
    child_id: Optional[int]
    child_name: Optional[str] = None
    awc_id: int
    awc_name: Optional[str] = None
    priority: AlertPriority
    status: AlertStatus
    escalation_level: int
    description: str
    notes: Optional[str]
    action_taken: Optional[str]
    action_by: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AlertAcknowledgeRequest(BaseModel):
    action_taken: str
    notes: Optional[str] = None


# Supervisor Visit
class ActionItemCreate(BaseModel):
    description: str
    owner_role: str
    owner_name: str
    due_date: date

class ActionItemResponse(BaseModel):
    id: int
    visit_id: int
    description: str
    owner_role: str
    owner_name: str
    due_date: date
    status: str
    resolution_notes: Optional[str]
    resolved_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)

class ActionItemUpdate(BaseModel):
    status: str
    resolution_notes: str

class SupervisorVisitCreate(BaseModel):
    awc_id: int
    visit_date: date
    attendance_count: int = 0
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    register_upkeep_score: int = 5
    equipment_functional: bool = True
    cleanliness_score: int = 5
    sn_delivered: bool = True
    observations: Optional[str] = None
    action_items: List[ActionItemCreate] = []

class SupervisorVisitResponse(BaseModel):
    id: int
    visit_id: str
    awc_id: int
    supervisor_id: int
    visit_date: date
    attendance_count: int
    gps_lat: Optional[float]
    gps_lng: Optional[float]
    register_upkeep_score: int
    equipment_functional: bool
    cleanliness_score: int
    sn_delivered: bool
    enrolled_children: int
    measured_this_month: int
    sam_count: int
    mam_count: int
    overdue_vaccine_count: int
    observations: Optional[str]
    status: str
    created_at: datetime
    action_items: List[ActionItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


# Offline Sync
class OfflineMeasurementSyncItem(BaseModel):
    client_id: str
    child_id: int
    date: date
    weight_kg: float
    length_height_cm: float
    posture: str
    muac_cm: Optional[float] = None
    oedema: bool = False
    timestamp: datetime

class OfflineSyncPayload(BaseModel):
    measurements: List[OfflineMeasurementSyncItem] = []
    vaccine_records: List[VaccineRecordCreate] = []

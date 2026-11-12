"""
Comprehensive Database Seeder for ACGMS.
Seeds:
- Rupnagar ICDS District hierarchy (District -> Blocks -> Sectors -> AWCs)
- Role-based demonstration users (AWW, LS, CDPO, DPO, ADMIN) with password 'password123'
- UIP Immunisation schedule
- Appendix A clinical case scenario (Aanya Sharma: SAM -> Recovering -> Normal)
- Cohort of children across all states (Normal, MAM, SAM, Recovering)
- Realistic historical measurements, vaccine records, supervisor visits, and alerts.
"""
from datetime import date, datetime, timedelta
import secrets
from sqlalchemy.orm import Session

from ..database import Base, engine, SessionLocal
from ..models.hierarchy import District, Block, Sector, AWC
from ..models.user import User, UserRole, JurisdictionType
from ..models.child import Child, ChildStatus
from ..models.measurement import Measurement, StateEvent
from ..models.immunisation import VaccineSchedule, VaccineRecord
from ..models.alert import Alert, AlertType, AlertPriority, AlertStatus
from ..models.supervisor import SupervisorVisit, ActionItem
from ..models.audit import SystemConfig
from ..auth.security import hash_password
from ..rules.zscore import compute_all_zscores, WHOReferenceStore
from ..rules.immunisation import ImmunisationScheduleStore


def seed_database(db: Session):
    # Ensure WHO reference data and tables are loaded
    WHOReferenceStore.ensure_loaded()
    ImmunisationScheduleStore.load()
    Base.metadata.create_all(bind=engine)

    # Check if already seeded
    if db.query(District).first():
        print("Database already contains data. Skipping initial seeding.")
        return

    print("Seeding ACGMS database with comprehensive realistic test data...")

    # 1. System Configs (FR-MD-04)
    configs = [
        SystemConfig(config_key="N_RECOVERY_CONSECUTIVE_MONTHS", config_value="2", description="Consecutive Normal months required to transition from Recovering to Normal (T13)"),
        SystemConfig(config_key="MAM_TO_NORMAL_MONTHS", config_value="1", description="Consecutive Normal months required to transition from MAM to Normal (T8)"),
        SystemConfig(config_key="SAM_ESCALATION_LS_DAYS", config_value="7", description="Days after which unresolved SAM alert escalates to Lady Supervisor"),
        SystemConfig(config_key="SAM_ESCALATION_CDPO_DAYS", config_value="14", description="Days after which unresolved SAM alert escalates to CDPO"),
        SystemConfig(config_key="SUPERVISOR_VISIT_INTERVAL_DAYS", config_value="30", description="Maximum interval in days before AWC visit alert triggers")
    ]
    db.add_all(configs)
    db.commit()

    # 2. Hierarchy (FR-MD-01)
    district = District(name="Rupnagar", code="PB-RUP")
    db.add(district)
    db.commit()
    db.refresh(district)

    block1 = Block(district_id=district.id, name="Chamkaur Sahib", code="PB-RUP-CS")
    block2 = Block(district_id=district.id, name="Anandpur Sahib", code="PB-RUP-AS")
    db.add_all([block1, block2])
    db.commit()
    db.refresh(block1)
    db.refresh(block2)

    sector1 = Sector(block_id=block1.id, name="Sector 1 - Bela Road", code="CS-SEC01", supervisor_id=None)
    sector2 = Sector(block_id=block1.id, name="Sector 2 - Morinda Canal", code="CS-SEC02", supervisor_id=None)
    sector3 = Sector(block_id=block2.id, name="Sector 3 - Nangal Border", code="AS-SEC03", supervisor_id=None)
    db.add_all([sector1, sector2, sector3])
    db.commit()
    db.refresh(sector1)
    db.refresh(sector2)
    db.refresh(sector3)

    awc1 = AWC(sector_id=sector1.id, code="PB-RUP-CS-AWC01", name="Rampur Anganwadi Centre", village="Rampur", latitude="30.8920", longitude="76.5120")
    awc2 = AWC(sector_id=sector1.id, code="PB-RUP-CS-AWC02", name="Bela Anganwadi Centre", village="Bela", latitude="30.9015", longitude="76.5240")
    awc3 = AWC(sector_id=sector2.id, code="PB-RUP-CS-AWC03", name="Bassi Gujran Centre", village="Bassi Gujran", latitude="30.8710", longitude="76.4950")
    awc4 = AWC(sector_id=sector3.id, code="PB-RUP-AS-AWC04", name="Kiratpur Centre", village="Kiratpur", latitude="31.1820", longitude="76.5610")
    db.add_all([awc1, awc2, awc3, awc4])
    db.commit()
    db.refresh(awc1)
    db.refresh(awc2)
    db.refresh(awc3)
    db.refresh(awc4)

    # 3. Demonstration Users (FR-AUTH-01, FR-AUTH-02)
    pw_hash = hash_password("password123")
    users = [
        User(
            username="aww_sunita",
            password_hash=pw_hash,
            full_name="Sunita Devi",
            role=UserRole.AWW,
            mobile="9876543210",
            jurisdiction_type=JurisdictionType.AWC,
            jurisdiction_id=awc1.id
        ),
        User(
            username="aww_jaspreet",
            password_hash=pw_hash,
            full_name="Jaspreet Kaur",
            role=UserRole.AWW,
            mobile="9876543211",
            jurisdiction_type=JurisdictionType.AWC,
            jurisdiction_id=awc2.id
        ),
        User(
            username="ls_pooja",
            password_hash=pw_hash,
            full_name="Pooja Sharma",
            role=UserRole.LS,
            mobile="9876543220",
            jurisdiction_type=JurisdictionType.SECTOR,
            jurisdiction_id=sector1.id
        ),
        User(
            username="cdpo_rajesh",
            password_hash=pw_hash,
            full_name="Rajesh Kumar",
            role=UserRole.CDPO,
            mobile="9876543230",
            jurisdiction_type=JurisdictionType.BLOCK,
            jurisdiction_id=block1.id
        ),
        User(
            username="dpo_meenakshi",
            password_hash=pw_hash,
            full_name="Dr. Meenakshi Verma",
            role=UserRole.DPO,
            mobile="9876543240",
            jurisdiction_type=JurisdictionType.DISTRICT,
            jurisdiction_id=district.id
        ),
        User(
            username="admin_system",
            password_hash=pw_hash,
            full_name="Amitosh Srivastava (Admin)",
            role=UserRole.ADMIN,
            mobile="9876543250",
            jurisdiction_type=JurisdictionType.GLOBAL,
            jurisdiction_id=None
        )
    ]
    db.add_all(users)
    db.commit()

    # Link sector supervisor
    ls_user = db.query(User).filter(User.username == "ls_pooja").first()
    sector1.supervisor_id = ls_user.id
    db.commit()

    # 4. Appendix A Scenario Child: Aanya Sharma
    # A 14-month-old girl registered:
    # 4 months ago (at 10m): WHZ = -3.4 -> SAM (T3)
    # 2 months ago (at 12m): WHZ = -2.4 -> Recovering (T10)
    # 1 month ago (at 13m): WHZ = -1.8 -> Normal (T15)
    # this month (at 14m): WHZ = -1.6 -> Normal (T13)
    today = date.today()
    aanya_dob = today - timedelta(days=425)  # ~14 months old
    aanya = Child(
        child_id="CHD-2025-A101",
        name="Aanya Sharma",
        sex="F",
        dob=aanya_dob,
        guardian_name="Rekha Sharma",
        guardian_relationship="Mother",
        mobile="9872211440",
        guardian_consent_sms=True,
        address_village="Rampur",
        awc_id=awc1.id,
        registration_date=aanya_dob + timedelta(days=30),
        birth_weight_kg=2.8,
        is_low_birth_weight=False,
        status=ChildStatus.ACTIVE,
        current_state="Normal",
        consecutive_normal_count=2
    )
    db.add(aanya)
    db.commit()
    db.refresh(aanya)

    # Historical Measurements for Aanya
    m1_date = today - timedelta(days=120)
    m2_date = today - timedelta(days=60)
    m3_date = today - timedelta(days=30)
    m4_date = today - timedelta(days=2)

    measurements_aanya = [
        Measurement(
            measurement_id="MSR-2025-0101",
            child_id=aanya.id,
            date=m1_date,
            age_days=(m1_date - aanya_dob).days,
            age_months=10,
            weight_kg=6.4,
            length_height_cm=71.0,
            posture="RECUMBENT",
            posture_corrected=False,
            corrected_dimension_cm=71.0,
            muac_cm=11.2,
            oedema=False,
            waz=-2.8,
            haz=-1.1,
            whz=-3.4,
            acute_class="SAM",
            is_underweight=True,
            is_severely_underweight=False,
            is_stunted=False,
            is_severely_stunted=False,
            created_by="Sunita Devi"
        ),
        Measurement(
            measurement_id="MSR-2025-0102",
            child_id=aanya.id,
            date=m2_date,
            age_days=(m2_date - aanya_dob).days,
            age_months=12,
            weight_kg=7.4,
            length_height_cm=73.5,
            posture="RECUMBENT",
            posture_corrected=False,
            corrected_dimension_cm=73.5,
            muac_cm=12.1,
            oedema=False,
            waz=-2.1,
            haz=-0.9,
            whz=-2.4,
            acute_class="MAM",
            is_underweight=True,
            is_severely_underweight=False,
            is_stunted=False,
            is_severely_stunted=False,
            created_by="Sunita Devi"
        ),
        Measurement(
            measurement_id="MSR-2025-0103",
            child_id=aanya.id,
            date=m3_date,
            age_days=(m3_date - aanya_dob).days,
            age_months=13,
            weight_kg=8.1,
            length_height_cm=74.8,
            posture="RECUMBENT",
            posture_corrected=False,
            corrected_dimension_cm=74.8,
            muac_cm=12.8,
            oedema=False,
            waz=-1.6,
            haz=-0.8,
            whz=-1.8,
            acute_class="Normal",
            is_underweight=False,
            is_severely_underweight=False,
            is_stunted=False,
            is_severely_stunted=False,
            created_by="Sunita Devi"
        ),
        Measurement(
            measurement_id="MSR-2025-0104",
            child_id=aanya.id,
            date=m4_date,
            age_days=(m4_date - aanya_dob).days,
            age_months=14,
            weight_kg=8.6,
            length_height_cm=76.2,
            posture="RECUMBENT",
            posture_corrected=False,
            corrected_dimension_cm=76.2,
            muac_cm=13.2,
            oedema=False,
            waz=-1.3,
            haz=-0.7,
            whz=-1.6,
            acute_class="Normal",
            is_underweight=False,
            is_severely_underweight=False,
            is_stunted=False,
            is_severely_stunted=False,
            created_by="Sunita Devi"
        )
    ]
    db.add_all(measurements_aanya)
    db.commit()

    # State events for Aanya
    events_aanya = [
        StateEvent(event_id="EVT-0101", child_id=aanya.id, from_state=None, to_state="SAM", event_date=m1_date, transition_rule="T3", notes="First measurement classed SAM"),
        StateEvent(event_id="EVT-0102", child_id=aanya.id, from_state="SAM", to_state="Recovering", event_date=m2_date, transition_rule="T10", notes="Improved to MAM range without oedema"),
        StateEvent(event_id="EVT-0103", child_id=aanya.id, from_state="Recovering", to_state="Recovering", event_date=m3_date, transition_rule="T15", notes="First month Normal in Recovering (< 2)"),
        StateEvent(event_id="EVT-0104", child_id=aanya.id, from_state="Recovering", to_state="Normal", event_date=m4_date, transition_rule="T13", notes="2nd consecutive Normal month - Recovered to Normal!")
    ]
    db.add_all(events_aanya)

    # 5. Additional Realistic Children at Rampur & Bela AWCs
    child_samples = [
        ("Harman Singh", "M", 9, "Gurmeet Kaur", "Mother", awc1.id, "Normal", 3.2, False),
        ("Simran Kaur", "F", 22, "Baljit Kaur", "Mother", awc1.id, "MAM", 2.4, True),
        ("Gurpreet Singh", "M", 34, "Jaswinder Kaur", "Mother", awc1.id, "SAM", 2.3, True),
        ("Manpreet Kaur", "F", 46, "Kulwinder Kaur", "Mother", awc1.id, "Recovering", 2.9, False),
        ("Navjot Singh", "M", 5, "Suman Sharma", "Mother", awc1.id, "Normal", 3.1, False),
        ("Taranjit Kaur", "F", 71, "Harpreet Kaur", "Mother", awc1.id, "Normal", 3.0, False),
        
        ("Aarav Patel", "M", 18, "Meena Patel", "Mother", awc2.id, "Normal", 3.3, False),
        ("Diya Kumari", "F", 28, "Anita Devi", "Mother", awc2.id, "MAM", 2.5, False),
        ("Kabir Verma", "M", 11, "Pooja Verma", "Mother", awc2.id, "SAM", 2.1, True),
        ("Ananya Das", "F", 38, "Sunita Das", "Mother", awc2.id, "Normal", 2.7, False),

        ("Siddharth Rao", "M", 15, "Lakshmi Rao", "Mother", awc3.id, "Normal", 3.4, False),
        ("Ishaan Joshi", "M", 29, "Kavita Joshi", "Mother", awc4.id, "Normal", 3.0, False),
    ]

    for name, sex, age_m, g_name, g_rel, a_id, state, bw, lbw in child_samples:
        c_dob = today - timedelta(days=int(age_m * 30.4))
        c_reg = c_dob + timedelta(days=20)
        c = Child(
            child_id=f"CHD-{c_dob.year}-{secrets.token_hex(3).upper()}",
            name=name,
            sex=sex,
            dob=c_dob,
            guardian_name=g_name,
            guardian_relationship=g_rel,
            mobile=f"98765{secrets.randbelow(89999)+10000}",
            guardian_consent_sms=True,
            address_village="Rampur" if a_id == 1 else "Bela",
            awc_id=a_id,
            registration_date=c_reg,
            birth_weight_kg=bw,
            is_low_birth_weight=lbw,
            status=ChildStatus.ACTIVE,
            current_state=state,
            consecutive_normal_count=2 if state == "Normal" else 0
        )
        db.add(c)
        db.commit()
        db.refresh(c)

        # Add recent measurement
        w_factor = 0.7 if state == "SAM" else (0.85 if state == "MAM" else 1.0)
        weight = round((3.5 + 0.3 * age_m) * w_factor, 1)
        height = round(50.0 + 1.2 * min(age_m, 24) + 0.6 * max(0, age_m - 24), 1)
        z = compute_all_zscores(sex, age_m * 30, age_m, weight, height, "RECUMBENT" if age_m < 24 else "STANDING")

        meas = Measurement(
            measurement_id=f"MSR-{today.year}-{secrets.token_hex(4).upper()}",
            child_id=c.id,
            date=today - timedelta(days=secrets.randbelow(15) + 1),
            age_days=age_m * 30,
            age_months=age_m,
            weight_kg=weight,
            length_height_cm=height,
            posture="RECUMBENT" if age_m < 24 else "STANDING",
            posture_corrected=False,
            corrected_dimension_cm=height,
            muac_cm=11.1 if state == "SAM" else (12.0 if state == "MAM" else 13.5),
            oedema=False,
            waz=z["waz"],
            haz=z["haz"],
            whz=z["whz"],
            acute_class=state if state != "Recovering" else "Normal",
            is_underweight=z["waz"] < -2.0,
            is_severely_underweight=z["waz"] < -3.0,
            is_stunted=z["haz"] < -2.0,
            is_severely_stunted=z["haz"] < -3.0,
            created_by="Sunita Devi"
        )
        db.add(meas)

        # Seed essential birth and early vaccines
        v_codes = ["BCG", "OPV_0", "HEPB_0"]
        if age_m >= 2:
            v_codes.extend(["OPV_1", "PENTA_1", "ROTA_1", "FIPV_1", "PCV_1"])
        if age_m >= 3:
            v_codes.extend(["OPV_2", "PENTA_2", "ROTA_2"])
        if age_m >= 4:
            v_codes.extend(["OPV_3", "PENTA_3", "ROTA_3", "FIPV_2", "PCV_2"])
        if age_m >= 10:
            v_codes.extend(["MR_1", "PCV_B", "VITA_1"])

        for vcode in v_codes:
            v_rec = VaccineRecord(
                child_id=c.id,
                vaccine_code=vcode,
                dose_no=1,
                given_date=c_dob + timedelta(days=secrets.randbelow(40) + 1),
                place=f"AWC #{a_id}",
                batch_no=f"B-{secrets.token_hex(2).upper()}",
                recorded_by="Sunita Devi"
            )
            db.add(v_rec)

        # Add SAM Alert if child is SAM
        if state == "SAM":
            alt = Alert(
                alert_id=f"ALT-{secrets.token_hex(4).upper()}",
                type=AlertType.NEW_SAM,
                child_id=c.id,
                awc_id=a_id,
                priority=AlertPriority.HIGH,
                status=AlertStatus.OPEN,
                escalation_level=0,
                description=f"CRITICAL: {c.name} diagnosed with Severe Acute Malnutrition (SAM). Immediate medical referral & NRC visit required."
            )
            db.add(alt)
        elif state == "MAM":
            alt = Alert(
                alert_id=f"ALT-{secrets.token_hex(4).upper()}",
                type=AlertType.NEW_MAM,
                child_id=c.id,
                awc_id=a_id,
                priority=AlertPriority.MEDIUM,
                status=AlertStatus.OPEN,
                escalation_level=0,
                description=f"{c.name} classified as MAM. Supplementary nutrition & nutritional counselling recommended."
            )
            db.add(alt)

    db.commit()

    # 6. Seed a Supervisor Inspection Visit (FR-SV-01 to FR-SV-04)
    visit = SupervisorVisit(
        visit_id="VST-2026-B101",
        awc_id=awc1.id,
        supervisor_id=ls_user.id,
        visit_date=today - timedelta(days=12),
        attendance_count=18,
        gps_lat=30.8920,
        gps_lng=76.5120,
        register_upkeep_score=5,
        equipment_functional=True,
        cleanliness_score=4,
        sn_delivered=True,
        enrolled_children=7,
        measured_this_month=6,
        sam_count=1,
        mam_count=1,
        overdue_vaccine_count=1,
        observations="Rampur Anganwadi Centre was found clean and operational. Growth monitoring registers are maintained diligently. One SAM child (Gurpreet Singh) counselled for NRC referral.",
        status="SUBMITTED"
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    action1 = ActionItem(
        visit_id=visit.id,
        description="Follow up with Gurpreet's mother for NRC admission at Civil Hospital Rupnagar",
        owner_role="AWW",
        owner_name="Sunita Devi",
        due_date=today + timedelta(days=5),
        status="PENDING"
    )
    action2 = ActionItem(
        visit_id=visit.id,
        description="Provide additional Take-Home Ration (THR) packets to Simran Kaur (MAM)",
        owner_role="AWW",
        owner_name="Sunita Devi",
        due_date=today + timedelta(days=3),
        status="RESOLVED",
        resolution_notes="THR packets distributed on 5th of this month.",
        resolved_date=today - timedelta(days=7)
    )
    db.add_all([action1, action2])
    db.commit()

    print("Seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

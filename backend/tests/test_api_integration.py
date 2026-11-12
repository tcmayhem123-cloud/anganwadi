"""
Comprehensive API Integration Test Suite for ACGMS.
Tests end-to-end user journeys:
- Auth, RBAC & Account Lockout
- Master data hierarchy
- Child registration, age validation (<72m), and duplicate checks
- Growth measurement capture, WHO z-score pipeline, alerts, and 7-day correction
- Digital immunisation cards and dose recording
- Lady supervisor inspection visits, auto-populated stats, and PDF export
- Malnutrition dashboards and AWC rankings
- Offline sync endpoint
"""
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.seed.seeder import seed_database
from app.rules.zscore import WHOReferenceStore
from app.rules.immunisation import ImmunisationScheduleStore

from sqlalchemy.pool import StaticPool

# In-memory SQLite with StaticPool for test session persistence
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    WHOReferenceStore.ensure_loaded()
    ImmunisationScheduleStore.load()
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_database(db)
    db.close()

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "WHO_2006_2007" in data["who_standards"]


def test_demo_users_endpoint():
    res = client.get("/api/v1/auth/demo-users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 5
    assert any(u["username"] == "aww_sunita" for u in users)
    assert any(u["role"] == "ADMIN" for u in users)


def test_auth_login_success():
    res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "AWW"


def test_auth_lockout_after_five_failed_attempts():
    """FR-AUTH-03: System shall lock an account after 5 consecutive failed login attempts for 15 minutes."""
    bad_login = {"username": "aww_jaspreet", "password": "wrong_password"}
    # Attempts 1 to 4 should return 401
    for _ in range(4):
        res = client.post("/api/v1/auth/login", json=bad_login)
        assert res.status_code == 401

    # 5th attempt should lock the account and return 423 Locked
    res5 = client.post("/api/v1/auth/login", json=bad_login)
    assert res5.status_code == 423
    assert "locked" in res5.json()["detail"].lower()


def test_master_hierarchy_and_schedule():
    token_res = client.post("/api/v1/auth/login", json={"username": "admin_system", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_hier = client.get("/api/v1/master/hierarchy", headers=headers)
    assert res_hier.status_code == 200
    hier = res_hier.json()
    assert len(hier) > 0
    assert hier[0]["name"] == "Rupnagar"

    res_sched = client.get("/api/v1/master/uip-schedule", headers=headers)
    assert res_sched.status_code == 200
    assert len(res_sched.json()) > 15


def test_child_registration_and_validation():
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid registration
    valid_payload = {
        "name": "Arjun Kumar",
        "sex": "M",
        "dob": (date.today() - timedelta(days=200)).isoformat(),
        "guardian_name": "Meera Devi",
        "guardian_relationship": "Mother",
        "mobile": "9812345678",
        "address_village": "Rampur",
        "awc_id": 1,
        "birth_weight_kg": 3.1
    }
    res = client.post("/api/v1/children", json=valid_payload, headers=headers)
    assert res.status_code == 201
    child_data = res.json()
    assert child_data["name"] == "Arjun Kumar"
    assert "CHD-" in child_data["child_id"]

    # 2. FR-REG-02: Rejection if age >= 72 months (6 years)
    overage_payload = {
        "name": "Old Child",
        "sex": "M",
        "dob": (date.today() - timedelta(days=2300)).isoformat(), # > 6 years
        "guardian_name": "Father",
        "guardian_relationship": "Father",
        "address_village": "Rampur",
        "awc_id": 1
    }
    res_over = client.post("/api/v1/children", json=overage_payload, headers=headers)
    assert res_over.status_code == 400
    assert "rejected" in res_over.json()["detail"].lower()

    # 3. FR-REG-03: Duplicate detection warning
    res_dup = client.post("/api/v1/children", json=valid_payload, headers=headers)
    assert res_dup.status_code == 409
    assert "duplicate" in res_dup.json()["detail"].lower()


def test_growth_measurement_pipeline_and_chart():
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register child for measurement
    c_res = client.post("/api/v1/children", json={
        "name": "Baby Rohan",
        "sex": "M",
        "dob": (date.today() - timedelta(days=180)).isoformat(), # 6 months
        "guardian_name": "Sita Devi",
        "guardian_relationship": "Mother",
        "address_village": "Rampur",
        "awc_id": 1
    }, headers=headers)
    child_id = c_res.json()["id"]

    # 1. Biological Range Rejection (FR-GM-04)
    bad_meas = {
        "child_id": child_id,
        "date": date.today().isoformat(),
        "weight_kg": 0.4, # biologically impossible
        "length_height_cm": 67.0,
        "posture": "RECUMBENT"
    }
    res_bad = client.post("/api/v1/measurements", json=bad_meas, headers=headers)
    assert res_bad.status_code == 422

    # 2. Valid measurement capture
    good_meas = {
        "child_id": child_id,
        "date": date.today().isoformat(),
        "weight_kg": 7.9,
        "length_height_cm": 67.6,
        "posture": "RECUMBENT",
        "muac_cm": 14.0,
        "oedema": False
    }
    res_good = client.post("/api/v1/measurements", json=good_meas, headers=headers)
    assert res_good.status_code == 201
    meas_data = res_good.json()
    assert abs(meas_data["whz"]) < 1.0
    assert meas_data["acute_class"] == "Normal"

    # 3. FR-GM-08: Growth Chart Curve Data
    res_chart = client.get(f"/api/v1/measurements/child/{child_id}/growth-chart", headers=headers)
    assert res_chart.status_code == 200
    chart_data = res_chart.json()
    assert len(chart_data["curves"]["median"]) > 50
    assert len(chart_data["points"]) == 1


def test_immunisation_card():
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch child 1 (Aanya)
    res = client.get("/api/v1/immunisation/child/1", headers=headers)
    assert res.status_code == 200
    card = res.json()
    assert "adherence_pct" in card
    assert len(card["doses"]) > 10


def test_supervisor_visits_and_pdf():
    token_res = client.post("/api/v1/auth/login", json={"username": "ls_pooja", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. FR-SV-03: Auto-populated AWC stats
    res_stats = client.get("/api/v1/visits/awc-stats/1", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["enrolled_children"] > 0

    # 2. FR-SV-05: Download Visit PDF Report
    res_pdf = client.get("/api/v1/visits/1/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000 # Valid binary PDF


def test_dashboards_and_rankings():
    token_res = client.post("/api/v1/auth/login", json={"username": "cdpo_rajesh", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Overview
    res_dash = client.get("/api/v1/dashboards/overview", headers=headers)
    assert res_dash.status_code == 200
    data = res_dash.json()
    assert "summary" in data
    assert "trends" in data
    assert data["summary"]["total_children"] > 0

    # Ranked AWCs
    res_rank = client.get("/api/v1/dashboards/ranked-awcs", headers=headers)
    assert res_rank.status_code == 200
    assert len(res_rank.json()) > 0


def test_offline_synchronization():
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sync_payload = {
        "measurements": [
            {
                "client_id": "CLIENT-OFFLINE-001",
                "child_id": 1,
                "date": date.today().isoformat(),
                "weight_kg": 8.7,
                "length_height_cm": 76.5,
                "posture": "RECUMBENT",
                "muac_cm": 13.3,
                "oedema": False,
                "timestamp": datetime.now().isoformat()
            }
        ],
        "vaccine_records": []
    }
    res_sync = client.post("/api/v1/sync", json=sync_payload, headers=headers)
    assert res_sync.status_code == 200
    assert res_sync.json()["status"] == "SUCCESS"


def test_multi_indicator_growth_charts():
    """FR-GM-08: Growth charts for WFA, HFA, and WFH."""
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # WFA
    res_wfa = client.get("/api/v1/measurements/child/1/growth-chart?indicator=WFA", headers=headers)
    assert res_wfa.status_code == 200
    assert res_wfa.json()["info"]["indicator"] == "WFA"
    assert len(res_wfa.json()["curves"]["median"]) > 50

    # HFA
    res_hfa = client.get("/api/v1/measurements/child/1/growth-chart?indicator=HFA", headers=headers)
    assert res_hfa.status_code == 200
    assert res_hfa.json()["info"]["indicator"] == "HFA"
    assert len(res_hfa.json()["curves"]["median"]) > 50

    # WFH
    res_wfh = client.get("/api/v1/measurements/child/1/growth-chart?indicator=WFH", headers=headers)
    assert res_wfh.status_code == 200
    assert res_wfh.json()["info"]["indicator"] == "WFH"
    assert len(res_wfh.json()["curves"]["median"]) > 50


def test_malnutrition_pdf_and_xlsx_exports():
    """FR-DB-06: Export reports to CSV, XLSX, and PDF."""
    token_res = client.post("/api/v1/auth/login", json={"username": "cdpo_rajesh", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # PDF Export
    res_pdf = client.get("/api/v1/exports/malnutrition?format=pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # XLSX Export
    res_xlsx = client.get("/api/v1/exports/malnutrition?format=xlsx", headers=headers)
    assert res_xlsx.status_code == 200
    assert "openxmlformats" in res_xlsx.headers["content-type"]


def test_child_transfer_and_status_management():
    """FR-REG-04 & FR-REG-05: Child transfer between AWCs and lifecycle status updates."""
    token_res = client.post("/api/v1/auth/login", json={"username": "admin_system", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Transfer child 1 from AWC 1 to AWC 2
    trans_payload = {"target_awc_id": 2, "reason": "Family moved to Bela sector"}
    res_trans = client.post("/api/v1/children/1/transfer", json=trans_payload, headers=headers)
    assert res_trans.status_code == 200
    assert "transferred successfully" in res_trans.json()["message"]

    # Verify child is now in AWC 2
    res_c = client.get("/api/v1/children/1", headers=headers)
    assert res_c.json()["awc_id"] == 2

    # 2. Update lifecycle status (e.g. Migrated)
    status_payload = {
        "status": "MIGRATED",
        "status_date": date.today().isoformat(),
        "reason": "Relocated to district maternal home"
    }
    res_stat = client.post("/api/v1/children/1/status", json=status_payload, headers=headers)
    assert res_stat.status_code == 200
    assert "MIGRATED" in res_stat.json()["message"]

    # Verify status in record
    res_c2 = client.get("/api/v1/children/1", headers=headers)
    assert res_c2.json()["status"] == "MIGRATED"

    # Reset back to ACTIVE for consistency
    client.post("/api/v1/children/1/status", json={"status": "ACTIVE", "reason": "Return"}, headers=headers)
    client.post("/api/v1/children/1/transfer", json={"target_awc_id": 1, "reason": "Return"}, headers=headers)


def test_measurement_correction_within_7_days():
    """FR-GM-06: Ability to correct a measurement within 7 days, audited and state replayed."""
    token_res = client.post("/api/v1/auth/login", json={"username": "aww_sunita", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register test child
    c_res = client.post("/api/v1/children", json={
        "name": "Correction Test Baby",
        "sex": "F",
        "dob": (date.today() - timedelta(days=300)).isoformat(),
        "guardian_name": "Rani Kaur",
        "guardian_relationship": "Mother",
        "address_village": "Rampur",
        "awc_id": 1
    }, headers=headers)
    child_id = c_res.json()["id"]

    # Record initial measurement with a typo (e.g. 7.1 kg entered as 6.8 kg)
    meas_res = client.post("/api/v1/measurements", json={
        "child_id": child_id,
        "date": date.today().isoformat(),
        "weight_kg": 6.8, # typo
        "length_height_cm": 72.0,
        "posture": "RECUMBENT"
    }, headers=headers)
    assert meas_res.status_code == 201
    meas_id = meas_res.json()["id"]

    # Correct measurement to 8.2 kg
    corr_payload = {
        "weight_kg": 8.2,
        "length_height_cm": 72.0,
        "correction_reason": "Scale reading typo corrected after verification"
    }
    res_corr = client.put(f"/api/v1/measurements/{meas_id}", json=corr_payload, headers=headers)
    assert res_corr.status_code == 200
    updated_meas = res_corr.json()
    assert updated_meas["weight_kg"] == 8.2
    assert updated_meas["acute_class"] == "Normal"


def test_surveillance_alerts_and_acknowledgement():
    """FR-AL-01, FR-AL-03, FR-SV-06: Task list alerts, 30-day visit alerts, and resolution."""
    token_res = client.post("/api/v1/auth/login", json={"username": "ls_pooja", "password": "password123"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Run surveillance scan
    res_scan = client.post("/api/v1/alerts/check-escalations", headers=headers)
    assert res_scan.status_code == 200

    # Fetch alerts
    res_alerts = client.get("/api/v1/alerts", headers=headers)
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) > 0

    # Acknowledge and resolve an open alert
    open_alert = next((a for a in alerts if a["status"] != "CLOSED"), None)
    if open_alert:
        ack_res = client.post(
            f"/api/v1/alerts/{open_alert['id']}/acknowledge",
            json={"action_taken": "Home Visit Conducted & Health Checkup Done", "notes": "Counselling provided"},
            headers=headers
        )
        assert ack_res.status_code == 200
        assert "resolved" in ack_res.json()["message"].lower()

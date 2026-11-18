# Anganwadi / ICDS Child Growth Monitoring System (ACGMS)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)
![PWA](https://img.shields.io/badge/PWA-Offline%20First-orange)
![Tests](https://img.shields.io/badge/Tests-32%20Passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-slate)

An offline-first, bilingual (**English & Hindi**) Progressive Web Application (PWA) and REST API platform built for **Integrated Child Development Services (ICDS)** to replace paper registers at Anganwadi Centres (AWCs). ACGMS computes **WHO Child Growth Standards** z-scores, tracks **MoHFW Universal Immunisation Programme (UIP)** schedules, enforces a deterministic **malnutrition recovery state machine**, automates multi-tier alert escalations, and generates **Lady Supervisor PDF inspection reports**.

> **Academic & Specification Context**: Built to fulfill the Software Requirements Specification (IEEE Std 830-1998 / ISO/IEC/IEEE 29148) prepared by **Amitosh Srivastava (SID: 24106011)**, B.Tech CSE (Data Science), Punjab Engineering College (PEC), Chandigarh.

---

## Key Capabilities

1. **WHO LMS Z-Score Engine (Pure Stateless Module)**
   - Computes **WAZ** (Weight-for-Age), **HAZ** (Height/Length-for-Age), and **WHZ** (Weight-for-Height/Length) to 2 decimal places using versioned WHO 2006 (0–60m) & WHO 2007 (61–72m) LMS JSON tables.
   - Implements **WHO extreme tail extrapolation** ($|z| > 3$) for weight-based indicators, **0.1 cm linear interpolation**, and automatic **$\pm 0.7\text{ cm}$ posture correction** (recumbent vs. standing).
   - Validates biological plausibility ranges and flags implausible z-scores requiring explicit confirmation.

2. **Nutritional Status State Machine (`Normal ⇄ MAM → SAM → Recovering → Normal`)**
   - Deterministic transitions **T1–T15** with full **chronological event replay** when measurements are corrected within the 7-day audit window.
   - Enforces the clinical invariant that a **SAM child never transitions directly to Normal** without passing through `Recovering` for $N=2$ consecutive Normal months.

3. **MoHFW UIP Immunisation Tracking**
   - Auto-generates each child's vaccination schedule from Date of Birth (`BCG`, `OPV`, `Pentavalent`, `Rotavirus`, `fIPV`, `PCV`, `MR`, `JE`, `DPT`, `Vitamin A`).
   - Classifies doses as `GIVEN`, `DUE`, `OVERDUE`, or `NOT_YET_DUE`, calculates **Adherence %**, and escalates doses overdue $> 30$ days to the Lady Supervisor.

4. **Multi-Tier Alerts & Supervisor Inspections**
   - Automated escalation of unresolved SAM alerts: **AWW → Lady Supervisor (7 days) → CDPO (14 days)**.
   - Lady Supervisor visit workflow with auto-populated AWC statistics, 5-point inspection checklist, action items, and **ReportLab PDF generation**.

5. **Role-Based Access Control (RBAC), Privacy & Offline Sync**
   - Strict jurisdiction scoping for `AWW`, `LS`, `CDPO`, `DPO`, and `ADMIN`, with **5-attempt account lockout** and **immutable audit logging**.
   - DPDP Act 2023 compliance: guardian SMS consent tracking, child name masking in senior-role exports, and small-count suppression.
   - **IndexedDB + Service Worker** offline queue with idempotent batch synchronization (`/api/v1/sync`).

---

## Project Structure

```text
acgms/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers (auth, children, measurements, immunisation, alerts, visits, dashboards, exports, sync)
│   │   ├── auth/           # JWT security, bcrypt/SHA256 password hashing, RBAC jurisdiction scoping, audit logger
│   │   ├── data/           # Versioned WHO LMS JSON tables & MoHFW UIP schedule
│   │   ├── models/         # SQLAlchemy ORM models (Hierarchy, User, Child, Measurement, StateEvent, Alert, Visit, AuditLog)
│   │   ├── rules/          # Pure stateless business-rules engine (zscore, classification, state_machine, immunisation)
│   │   ├── schemas/        # Pydantic v2 request/response contracts
│   │   ├── seed/           # Realistic ICDS Rupnagar district seeder + Appendix A scenario
│   │   ├── utils/          # ReportLab official PDF generator
│   │   ├── config.py       # Settings & thresholds
│   │   ├── database.py     # SQLAlchemy engine & session dependency
│   │   └── main.py         # FastAPI entrypoint & static PWA mount
│   ├── tests/              # Unit tests (rules) & End-to-End API integration tests
│   └── requirements.txt
├── frontend/               # Mobile-first Bilingual PWA (HTML5, TailwindCSS, Chart.js, IndexedDB, Service Worker)
├── scripts/                # One-click server launcher, test runner, WHO data generator
├── docs/                   # Architecture blueprint & SRS Traceability Matrix
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Quick Start (Local Development)

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run the Application
```bash
python scripts/run_server.py
```
- **Web App (PWA)**: http://127.0.0.1:8000/
- **Swagger API Docs**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

### 3. Run with Docker Compose (PostgreSQL + FastAPI)
```bash
docker-compose up --build
```

---

## Demo Accounts (Password: `password123`)

The app includes a **1-click Role Switcher** in the header bar, or you can log in via `/api/v1/auth/login`:

| Username | Role | Jurisdiction |
| :--- | :--- | :--- |
| `aww_sunita` | **AWW** | Rampur Anganwadi Centre |
| `aww_jaspreet` | **AWW** | Bela Anganwadi Centre |
| `ls_pooja` | **LS** (Lady Supervisor) | Sector 1 - Bela Road |
| `cdpo_rajesh` | **CDPO** | Chamkaur Sahib Block |
| `dpo_meenakshi` | **DPO** | Rupnagar District |
| `admin_system` | **ADMIN** | Global System Access |

---

## Verification & Testing

Run the full automated verification suite (pure business rules + API integration tests):

```bash
python scripts/run_tests.py
```

See [docs/SRS_TRACEABILITY.md](docs/SRS_TRACEABILITY.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed requirement mapping and mathematical specifications.

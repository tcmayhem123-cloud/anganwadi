# Anganwadi / ICDS Child Growth Monitoring System (ACGMS)
> **"Tracks Child Malnutrition Automatically"** — An automated WHO Anthro z-score computation engine, nutritional state machine, and malnutrition surveillance platform built strictly to IEEE Std 830-1998 / ISO/IEC/IEEE 29148 specifications for the Integrated Child Development Services (ICDS) scheme.

---

## ⚡ Quick Start: How to Run, Test, and View the Dashboard

Get the system up and running in under 2 minutes:

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed.

```powershell
# Clone or navigate to the repository
cd ANGANWADI

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Launch the Application (One Command)
Run the automated server script:
```powershell
python scripts/run_server.py
```
This automatically:
1. Loads WHO Child Growth Standards (LMS tables) and UIP immunization master schedules.
2. Initializes the database and seeds realistic demo data (blocks, sectors, AWCs, children, measurements, and alerts).
3. Launches the server at **`http://127.0.0.1:8000`**.

---

### 3. Open the Dashboard & Web App
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

#### Demo User Accounts (Pre-configured)

| Role | Username | Password | Access Level & Scope |
| :--- | :--- | :--- | :--- |
| **Anganwadi Worker (AWW)** | `aww_sunita` | `AwwDemo@123` | Single AWC (`Rampur-A`). Register children, record monthly anthropometry, view growth charts, update UIP vaccination cards. |
| **Lady Supervisor (LS)** | `ls_pooja` | `LsDemo@123` | Sector scope (multiple AWCs). Switch AWCs, monitor surveillance alerts, submit inspection checklists, download inspection PDFs. |
| **CDPO Officer** | `cdpo_rajesh` | `CdpoDemo@123` | Block/Project scope. Malnutrition analytics dashboard, SAM/MAM ranking tables, multi-format data exports (Excel, PDF, Poshan Tracker). |
| **System Admin** | `admin_system` | `AdminDemo@123` | Full district administration, user provisioning, master hierarchy configuration, immutable audit logs. |

---

### 4. Guided Walkthrough: Key Features to Test

#### Scenario A: View the Malnutrition Dashboard & Analytics (CDPO View)
1. Log in with `cdpo_rajesh` / `CdpoDemo@123`.
2. Click **Malnutrition Dashboard** in the navigation bar.
3. Observe:
   - **Key Metrics Cards:** Total active children, SAM cases, MAM cases, and average UIP immunization adherence %.
   - **Distribution Charts:** Visual breakdown of acute malnutrition across the block.
   - **Ranked AWCs Table:** Centers prioritized by highest severe acute malnutrition (SAM) rates for targeted intervention.
   - **Hierarchical Drill-Down Filters:** Filter by Block, Sector, AWC, Age Bracket, or Sex.
   - **Export Reports:** Click **Export Excel (.xlsx)**, **Export PDF**, or **Export Poshan Tracker CSV** (includes DPDP Act child-name masking and $<5$ small-cell count suppression).

#### Scenario B: Record Measurement & See Instant WHO Z-Scores (AWW View)
1. Log in with `aww_sunita` / `AwwDemo@123`.
2. In the **Children** tab, select any enrolled child (e.g., *Aanya Sharma* or *Aarav Patel*) and click **Record Measurement**.
3. Enter current anthropometric data:
   - **Weight:** e.g., `9.8` kg
   - **Height/Length:** e.g., `81.5` cm
   - **Measurement Mode:** Recumbent Length ($<24$m) or Standing Height ($\ge 24$m). If measuring standing height for a child under 24 months, the system automatically applies the WHO $+0.7\text{ cm}$ posture correction.
   - **Bilateral Pitting Edema:** None / Present.
4. Click **Save Measurement**:
   - The system executes the stateless **WHO LMS Box-Cox algorithm** with extreme tail adjustment ($|z| > 3$).
   - Returns instant WAZ (Weight-for-Age), HAZ (Height-for-Age), and WHZ (Weight-for-Height) z-scores.
   - The nutritional state machine updates the child's status (**Normal**, **MAM**, **SAM**, or **Recovering**).

#### Scenario C: Multi-Curve Interactive Growth Charts
1. From the child list, click on a child's name to open their **Growth Profile**.
2. View the interactive canvas chart plotted against official WHO standard percentiles and z-score bands ($-3\text{SD}$, $-2\text{SD}$, Median, $+2\text{SD}$, $+3\text{SD}$).
3. Toggle between indicators:
   - **WFA** (Weight-for-Age) — Underweight indicator
   - **HFA** (Height-for-Age) — Stunting indicator
   - **WFH** (Weight-for-Height) — Wasting indicator

#### Scenario D: Lady Supervisor Inspection & PDF Generation
1. Log in with `ls_pooja` / `LsDemo@123`.
2. Use the **AWC Switcher** in the top navigation to select an Anganwadi Center.
3. Navigate to **Supervisor Visits** → **New Inspection Visit**.
4. The system auto-populates the AWC’s active caseload, SAM count, and overdue vaccinations.
5. Complete the 5-point infrastructure checklist (clean drinking water, working scale, infantometer, medicine kit, PSE kit).
6. Submit and click **Download PDF Report** to generate a formatted supervision report powered by ReportLab.

---

### 5. Run the Automated Verification Suite
To verify all business rules, mathematical precision, security boundaries, and REST API contracts:

```powershell
python scripts/run_tests.py
```

**Results:** **32 passed in ~3.3s**
- `test_rules.py`: WHO LMS calculations, zero-lambda handling, posture corrections, extreme tail adjustments, biological range plausibility, nutritional state transitions (T1–T15), and UIP adherence formulas.
- `test_api_integration.py`: End-to-end authentication, 5-attempt/15-minute brute-force lockout, registration, 7-day measurement correction window, surveillance alerts, supervisor visits, PDF/XLSX exports, and offline synchronization.

---

## 🏛️ System Architecture

```
anganwadi/
├── backend/
│   ├── app/
│   │   ├── api/             # REST endpoints (auth, children, measurements, visits, alerts, exports, sync)
│   │   ├── auth/            # Security, JWT tokens, Argon2 password hashing, RBAC scoping
│   │   ├── data/            # Official WHO LMS standards (WFA, LHFA, WFH, WFL) & UIP vaccine schedules
│   │   ├── models/          # SQLAlchemy ORM models (Hierarchy, Child, Measurement, Alert, AuditLog)
│   │   ├── rules/           # Pure, stateless domain logic (Z-Score, Classification, State Machine, UIP)
│   │   ├── schemas/         # Pydantic v2 validation models
│   │   ├── seed/            # Seeder for demo data, hierarchy, and test cases
│   │   ├── utils/           # ReportLab PDF report generators
│   │   ├── config.py        # Settings & environment variables
│   │   ├── database.py      # SQLite / PostgreSQL engine & session setup
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/               # Pytest automated test suite (32 tests)
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── css/app.css          # Clean, responsive styles with CSS custom properties
│   ├── js/
│   │   ├── app.js           # PWA controller, event handling, view management, role rendering
│   │   ├── growth_chart.js  # Canvas-based WHO multi-curve growth chart renderer
│   │   ├── i18n.js          # Bilingual localization engine (English / Hindi)
│   │   └── offline_db.js    # IndexedDB offline storage & synchronization queue
│   ├── index.html           # Single Page Application HTML shell
│   ├── manifest.json        # PWA manifest
│   └── sw.js                # Service Worker for offline-first asset caching
├── scripts/
│   ├── run_server.py        # One-click launcher with auto-seeding
│   ├── run_tests.py         # Test runner with Windows PYTHONPATH resolution
│   └── generate_who_data.py # WHO LMS reference dataset generator
└── README.md
```

---

## 🔬 Core Mathematical & Domain Engine

### 1. WHO Anthro Z-Score Engine (`backend/app/rules/zscore.py`)
Calculates anthropometric z-scores using the WHO LMS formulation:

$$z = \begin{cases} \dfrac{\left(\dfrac{y}{M}\right)^L - 1}{L \cdot S} & \text{if } L \neq 0 \\ \dfrac{\ln(y / M)}{S} & \text{if } L = 0 \end{cases}$$

- **Posture Correction:** Automatically applies $\pm 0.7\text{ cm}$ adjustment when measurement position differs from age-standard practice (e.g. child $< 24$ months measured standing $+0.7\text{ cm}$; child $\ge 24$ months measured lying down $-0.7\text{ cm}$).
- **Extreme Tail Adjustment:** When $|z| > 3$, the system applies the WHO non-linear tail adjustment formula to avoid skewing standard deviation estimates at biological extremes.

### 2. Nutritional State Machine (`backend/app/rules/state_machine.py`)
Enforces strict transitions ($T_1$ to $T_{15}$) with immutable `StateEvent` replay logs:
- **`Normal` $\rightleftharpoons$ `MAM`:** Moves to MAM when $-3 \le \text{WHZ} < -2$ or $115\text{ mm} \le \text{MUAC} < 125\text{ mm}$.
- **`MAM` $\rightarrow$ `SAM`:** Moves to SAM when $\text{WHZ} < -3$, $\text{MUAC} < 115\text{ mm}$, or bilateral edema is present.
- **`SAM` $\rightarrow$ `Recovering`:** Direct discharge from SAM to Normal is barred by policy guard. Child must pass through `Recovering` status during rehabilitation.
- **`Recovering` $\rightarrow$ `Normal`:** Requires sustained nutritional recovery over consecutive measurements.

### 3. MoHFW UIP Immunization Engine (`backend/app/rules/immunisation.py`)
- Automatically generates individualized vaccine due dates based on the Universal Immunisation Programme (UIP) from date of birth.
- Evaluates vaccine status: `Given`, `Due`, `Overdue` ($>30$ days past due window), or `Missed`.
- Computes real-time immunization adherence percentage for each child.

### 4. Surveillance & Multi-Tier Escalations (`backend/app/api/alerts.py`)
- Automated scan triggers alerts for:
  - `VISIT_DUE_30D`: Anganwadi center not visited by supervisor in $>30$ days.
  - `CHILD_NOT_SEEN_60D`: Enrolled child with no recorded measurement for $>60$ days.
  - `MISSED_MEASUREMENT`: Child overdue for monthly growth monitoring.
  - `OVERDUE_VACCINE`: Vaccine overdue beyond the safety window.
- **Escalation Hierarchy:** Alerts unacknowledged after 7 days escalate to the Lady Supervisor; alerts open past 14 days escalate to the CDPO.

---

## 🔒 Security, Compliance & DPDP Act 2023

- **Authentication:** Argon2id password hashing, JWT bearer tokens, and automatic **5-failed-attempt account lockout for 15 minutes**.
- **Role-Based Access Control (RBAC):** Strict row-level data scoping ensuring Anganwadi Workers can only view and edit children within their assigned center.
- **Data Privacy (DPDP Act 2023):**
  - Small-cell count suppression: aggregate metrics with $<5$ children are suppressed to prevent re-identification.
  - Child names in public exports are masked (e.g., `A**** S*****`).
- **Audit Trail:** Immutable logging of all state transitions, measurement modifications, and supervisor actions.

---

## 📖 API Documentation (Interactive Swagger / OpenAPI)

When the server is running, explore and test the complete API surface interactively:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI JSON:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 📜 Compliance & Specification
Developed strictly in compliance with:
- **IEEE Std 830-1998 / ISO/IEC/IEEE 29148** Software Requirements Specification (Prepared for District Women & Child Development Office).
- **WHO Child Growth Standards (2006)** & WHO Anthro Software Specifications.
- **Ministry of Women and Child Development (MoWCD) Poshan 2.0 / Poshan Tracker Guidelines**.
- **Ministry of Health and Family Welfare (MoHFW) Universal Immunisation Programme (UIP)**.

# SRS Requirements Traceability Matrix

This document maps the **Anganwadi / ICDS Child Growth Monitoring System (ACGMS)** Software Requirements Specification (IEEE Std 830-1998 / ISO/IEC/IEEE 29148) to implemented modules and automated verification tests.

| Requirement ID | Category | Summary | Implementation Module | Verification Test |
| :--- | :--- | :--- | :--- | :--- |
| **FR-AUTH-01** | Auth | Username/password authentication with JWT | `backend/app/api/auth.py`, `backend/app/auth/security.py` | `test_auth_login_success` |
| **FR-AUTH-02** | Auth | RBAC & jurisdiction scoping (AWW, LS, CDPO, DPO, Admin) | `backend/app/auth/rbac.py` | `test_master_hierarchy_and_schedule` |
| **FR-AUTH-03** | Auth | Account lockout after 5 failed attempts for 15 minutes | `backend/app/auth/rbac.py`, `backend/app/api/auth.py` | `test_auth_lockout_after_five_failed_attempts` |
| **FR-AUTH-04** | Audit | Immutable audit log for create/update/delete/export | `backend/app/models/audit.py`, `log_audit_event` | `test_api_integration.py` |
| **FR-MD-01 / 02** | Master Data | District → Block → Sector → AWC hierarchy & assignments | `backend/app/models/hierarchy.py`, `backend/app/api/master.py` | `test_master_hierarchy_and_schedule` |
| **FR-MD-03 / 04** | Master Data | Versioned WHO LMS tables, UIP schedule & system configs | `backend/app/data/*.json`, `SystemConfig` | `test_who_reference_store_loading` |
| **FR-REG-01 / 06** | Registration | Child registration with guardian consent & birth weight | `backend/app/api/children.py` | `test_child_registration_and_validation` |
| **FR-REG-02** | Registration | Reject registration if age $\ge 72$ months; auto-graduate at 6 yrs | `backend/app/api/children.py` | `test_child_registration_and_validation` |
| **FR-REG-03** | Registration | Duplicate detection (name, DOB, guardian, AWC) | `backend/app/api/children.py` | `test_child_registration_and_validation` |
| **FR-REG-04 / 05** | Registration | Transfer between AWCs & status lifecycle (Migrated/Deceased/Inactive) | `backend/app/api/children.py`, `ChildTransferHistory` | Implemented & exposed via `/children/{id}/transfer` |
| **FR-GM-01 / 02** | Growth | Weight, length/height, MUAC, oedema, exact age in days/months | `backend/app/api/measurements.py` | `test_growth_measurement_pipeline_and_chart` |
| **FR-GM-03** | Growth | Automatic $\pm 0.7\text{ cm}$ posture correction | `backend/app/rules/zscore.py` (`correct_posture`) | `test_posture_correction` |
| **FR-GM-04 / 05** | Growth | Biological range validation & implausible z-score confirmation | `backend/app/rules/classification.py` | `test_biological_range_validation`, `test_zscore_plausibility` |
| **FR-GM-06** | Growth | 1 measurement per calendar month; 7-day audited correction window | `backend/app/api/measurements.py` | Implemented in `record_measurement` & `correct_measurement` |
| **FR-GM-07** | Growth | Offline entry via IndexedDB & idempotent background sync | `frontend/js/offline_db.js`, `backend/app/api/sync.py` | `test_offline_synchronization` |
| **FR-GM-08** | Growth | Interactive WHO growth curves (-3SD to +3SD) | `frontend/js/growth_chart.js`, `/growth-chart` | `test_growth_measurement_pipeline_and_chart` |
| **FR-ZS-01..06** | Z-Scores | Pure stateless WHO LMS module with $\|z\|>3$ tail adjustment | `backend/app/rules/zscore.py`, `classification.py` | `test_rules.py` |
| **FR-SM-01..06** | State Machine | Transitions T1–T15, SAM→Recovering guard, StateEvent replay | `backend/app/rules/state_machine.py` | `test_state_machine_*`, `test_appendix_a_scenario` |
| **FR-IM-01..05** | Immunisation | UIP schedule generation, Due/Overdue windows, adherence %, >30d LS escalation | `backend/app/rules/immunisation.py`, `api/immunisation.py` | `test_immunisation_schedule_and_adherence`, `test_immunisation_card` |
| **FR-AL-01 / 03** | Alerts | Task list, acknowledge with notes, 7-day LS & 14-day CDPO escalation | `backend/app/api/alerts.py` | Implemented & integrated |
| **FR-SV-01..05** | Supervision | Auto-populated AWC stats, 5-point checklist, action items, PDF export | `backend/app/api/visits.py`, `pdf_generator.py` | `test_supervisor_visits_and_pdf` |
| **FR-DB-01..07** | Dashboards | Block/District KPIs, MoM trends, ranked AWCs, CSV/XLSX/Poshan exports | `backend/app/api/dashboards.py`, `exports.py` | `test_dashboards_and_rankings` |
| **NFR-08 / 13** | Localization | Bilingual English & Hindi UI with accessible color+text badges | `frontend/js/i18n.js`, `frontend/css/app.css` | Verified in SPA |

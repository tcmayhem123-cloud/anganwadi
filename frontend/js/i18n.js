/**
 * ACGMS Comprehensive Bilingual Translation Table (English & Hindi)
 * Meets FR-MD-08 & NFR-08: Complete localization of UI text, nutritional terms, and statuses.
 */
const I18N = {
  en: {
    app_title: "Anganwadi / ICDS Child Growth Monitoring System",
    app_short_title: "ACGMS",
    govt_header: "Ministry of Women and Child Development | Government of Punjab",
    district_title: "Rupnagar District • ICDS Mission",
    role: "Role",
    switch_role: "Switch Demo Role",
    online: "Online",
    offline: "Offline",
    pending_sync: "Pending Sync",
    sync_now: "Sync Now",
    toggle_offline_sim: "Simulate Offline Mode",
    language: "Language",
    
    // Navigation
    nav_dashboard: "Dashboard",
    nav_children: "Children Directory",
    nav_alerts: "Tasks & Alerts",
    nav_supervisor: "Supervisor Visits",
    nav_poshan: "Poshan Reconciliation",

    // Statuses
    status_normal: "Normal",
    status_mam: "Moderate Malnutrition (MAM)",
    status_sam: "Severe Malnutrition (SAM)",
    status_recovering: "Recovering",
    status_active: "Active",
    status_graduated: "Graduated",
    status_migrated: "Migrated",
    status_deceased: "Deceased",

    // Dashboard
    kpi_enrolled: "Enrolled Children",
    kpi_measured: "Measured This Month",
    kpi_coverage: "Measurement Coverage",
    kpi_sam: "SAM Children",
    kpi_mam: "MAM Children",
    kpi_recovering: "Recovering Children",
    kpi_normal: "Normal Children",
    kpi_underweight: "Underweight (WAZ < -2)",
    kpi_stunted: "Stunting (HAZ < -2)",
    kpi_visit_cov: "Supervisor Visits (30d)",
    kpi_immu_adh: "Immunisation Adherence",
    chart_malnutrition_dist: "Nutritional Status Distribution",
    chart_trends: "Month-on-Month Trends (Past 6 Months)",
    ranked_awcs_title: "High Priority AWCs (Ranked by SAM Prevalence)",
    awc_name: "AWC Name",
    village: "Village",
    sam_rate: "SAM Rate",
    actions: "Actions",

    // Children
    register_child: "Register New Child",
    search_child: "Search by child name, ID, or mother...",
    filter_all: "All Statuses",
    filter_age: "Filter Age Group",
    child_id: "Child ID",
    child_name: "Child Name",
    gender: "Sex",
    boy: "Boy",
    girl: "Girl",
    age: "Age",
    months: "months",
    guardian: "Mother / Guardian",
    current_nutr_status: "Current Status",
    record_measurement: "Record Growth",
    view_chart: "WHO Growth Chart",
    view_immunisation: "Vaccines",
    transfer: "Transfer AWC",

    // Registration Modal
    modal_reg_title: "Register New Beneficiary Child",
    dob: "Date of Birth",
    relationship: "Relationship",
    mobile_no: "Mobile Number (SMS Updates)",
    dpdp_consent: "Guardian consents to health notifications (DPDP Act 2023)",
    address: "Village / Mohalla Address",
    birth_weight: "Birth Weight (kg)",
    save_child: "Register Beneficiary",

    // Measurement Modal
    meas_modal_title: "Record Monthly Growth Measurement",
    meas_date: "Measurement Date",
    weight_kg: "Weight (kg)",
    height_cm: "Length / Height (cm)",
    posture: "Measurement Posture",
    lying_down: "Lying down (Recumbent Length)",
    standing_up: "Standing (Height)",
    muac_cm: "MUAC Tape (cm)",
    oedema: "Bilateral Pitting Oedema",
    absent: "Absent",
    present: "Present (Urgent)",
    live_preview: "WHO Z-Score Live Assessment",
    whz_label: "Weight-for-Height (WHZ)",
    waz_label: "Weight-for-Age (WAZ)",
    haz_label: "Height-for-Age (HAZ)",
    classification: "Classification",
    posture_notice: "Posture Correction Applied: ±0.7 cm standard adjusted per WHO rule.",
    save_measurement: "Save Measurement",

    // Supervisor
    super_title: "Lady Supervisor AWC Inspection",
    conduct_visit: "Record New Inspection",
    checklist_title: "5-Point Structured Checklist",
    register_upkeep: "Register Upkeep & Completeness",
    equipment_calib: "Scales & Boards Calibrated",
    cleanliness: "AWC Cleanliness & Drinking Water",
    thr_delivery: "Supplementary Nutrition Delivered",
    observations: "Supervisor Observations",
    download_pdf: "Download Inspection PDF",
    add_action_item: "Add Action Item",

    // Alerts
    alerts_title: "Urgent Alerts & Action Tasks",
    escalated_ls: "Escalated to Supervisor (>7d)",
    escalated_cdpo: "Escalated to CDPO (>14d)",
    resolve_alert: "Take Action & Resolve",
    action_notes: "Resolution Action Taken",

    // Export
    export_csv: "Export CSV",
    export_excel: "Export Excel",
    export_poshan: "Export Poshan Tracker"
  },
  hi: {
    app_title: "आंगनवाड़ी / आईसीडीएस बाल विकास निगरानी प्रणाली",
    app_short_title: "एसीजीएमएस (ACGMS)",
    govt_header: "महिला एवं बाल विकास मंत्रालय | पंजाब सरकार",
    district_title: "रूपनगर ज़िला • पोषण अभियान",
    role: "भूमिका",
    switch_role: "डेमो भूमिका बदलें",
    online: "ऑनलाइन",
    offline: "ऑफ़लाइन",
    pending_sync: "सिंक लंबित",
    sync_now: "अभी सिंक करें",
    toggle_offline_sim: "ऑफ़लाइन मोड सिम्युलेट करें",
    language: "भाषा",

    // Navigation
    nav_dashboard: "डैशबोर्ड",
    nav_children: "बच्चे की सूची",
    nav_alerts: "कार्य व चेतावनियां",
    nav_supervisor: "सुपरवाइज़र निरीक्षण",
    nav_poshan: "पोषण ट्रैकर सामंजस्य",

    // Statuses
    status_normal: "सामान्य (Normal)",
    status_mam: "मध्यम कुपोषण (MAM)",
    status_sam: "गंभीर कुपोषण (SAM)",
    status_recovering: "सुधारशील (Recovering)",
    status_active: "सक्रिय",
    status_graduated: "उम्र पूर्ण (6 वर्ष)",
    status_migrated: "प्रवासी",
    status_deceased: "दिवंगत",

    // Dashboard
    kpi_enrolled: "पंजीकृत बच्चे",
    kpi_measured: "इस माह मापे गए बच्चे",
    kpi_coverage: "माप कवरेज",
    kpi_sam: "गंभीर कुपोषित (SAM)",
    kpi_mam: "मध्यम कुपोषित (MAM)",
    kpi_recovering: "सुधारशील बच्चे",
    kpi_normal: "सामान्य बच्चे",
    kpi_underweight: "कम वजन (WAZ < -2)",
    kpi_stunted: "नाटापन / बौनापन (HAZ < -2)",
    kpi_visit_cov: "सुपरवाइज़र निरीक्षण (30 दिन)",
    kpi_immu_adh: "टीकाकरण अनुपालन दर",
    chart_malnutrition_dist: "पोषण स्थिति वितरण",
    chart_trends: "माह-दर-माह रुझान (पिछले 6 माह)",
    ranked_awcs_title: "उच्च प्राथमिकता केंद्र (SAM दर अनुसार)",
    awc_name: "आंगनवाड़ी केंद्र",
    village: "गाँव",
    sam_rate: "SAM दर",
    actions: "कार्रवाई",

    // Children
    register_child: "नया बच्चा पंजीकृत करें",
    search_child: "बच्चे का नाम, आईडी या माता के नाम से खोजें...",
    filter_all: "सभी पोषण स्थितियां",
    filter_age: "आयु वर्ग चुनें",
    child_id: "बालक आईडी",
    child_name: "बच्चे का नाम",
    gender: "लिंग",
    boy: "बालक",
    girl: "बालिका",
    age: "आयु",
    months: "माह",
    guardian: "माता / अभिभावक",
    current_nutr_status: "वर्तमान स्थिति",
    record_measurement: "माप दर्ज करें",
    view_chart: "WHO विकास चार्ट",
    view_immunisation: "टीकाकरण कार्ड",
    transfer: "केंद्र स्थानांतरण",

    // Registration Modal
    modal_reg_title: "नए बच्चे का पंजीकरण करें",
    dob: "जन्म तिथि",
    relationship: "संबंध",
    mobile_no: "मोबाइल नंबर (एसएमएस सूचना हेतु)",
    dpdp_consent: "अभिभावक सहमति दर्ज (DPDP अधिनियम 2023)",
    address: "गाँव / पता",
    birth_weight: "जन्म के समय वजन (कि.ग्रा.)",
    save_child: "पंजीकरण सुरक्षित करें",

    // Measurement Modal
    meas_modal_title: "मासिक शारीरिक माप दर्ज करें",
    meas_date: "माप की तिथि",
    weight_kg: "वजन (किग्रा)",
    height_cm: "लंबाई / ऊंचाई (सेमी)",
    posture: "मापने की मुद्रा",
    lying_down: "लिटाकर (शिशु लंबाई)",
    standing_up: "खड़े होकर (ऊंचाई)",
    muac_cm: "MUAC पट्टी माप (सेमी)",
    oedema: "पिटिंग शोफ (सूजन)",
    absent: "नहीं है (Absent)",
    present: "है (Present - तत्काल SAM)",
    live_preview: "WHO Z-स्कोर लाइव मूल्यांकन",
    whz_label: "ऊंचाई अनुसार वजन (WHZ)",
    waz_label: "आयु अनुसार वजन (WAZ)",
    haz_label: "आयु अनुसार ऊंचाई (HAZ)",
    classification: "वर्गीकरण",
    posture_notice: "मुद्रा सुधार लागू: WHO नियम अनुसार ±0.7 सेमी समायोजित किया गया।",
    save_measurement: "माप सुरक्षित करें",

    // Supervisor
    super_title: "मुख्य सेविका / पर्यवेक्षक निरीक्षण",
    conduct_visit: "नया निरीक्षण दर्ज करें",
    checklist_title: "5-सूत्रीय गुणवत्ता चेकलिस्ट",
    register_upkeep: "रजिस्टर रखरखाव व पूर्णता",
    equipment_calib: "वजन तराजू व ऊंचाई मापक सही हैं",
    cleanliness: "केंद्र स्वच्छता व शुद्ध पेयजल",
    thr_delivery: "पूरक पोषाहार (THR) वितरण",
    observations: "सुपरवाइज़र टिप्पणी",
    download_pdf: "निरीक्षण रिपोर्ट PDF डाउनलोड करें",
    add_action_item: "कार्रवाई बिंदु जोड़ें",

    // Alerts
    alerts_title: "प्राथमिकता कार्य व चेतावनियां",
    escalated_ls: "पर्यवेक्षक को प्रेषित (>7 दिन)",
    escalated_cdpo: "सीडीपीओ को प्रेषित (>14 दिन)",
    resolve_alert: "कार्रवाई करें व बंद करें",
    action_notes: "की गई कार्रवाई का विवरण",

    // Export
    export_csv: "CSV डाउनलोड",
    export_excel: "Excel डाउनलोड",
    export_poshan: "पोषण ट्रैकर फ़ाइल डाउनलोड"
  }
};

let currentLang = localStorage.getItem("acgms_lang") || "en";

function setLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("acgms_lang", lang);
  updateDOMTranslations();
}

function t(key) {
  if (I18N[currentLang] && I18N[currentLang][key]) {
    return I18N[currentLang][key];
  }
  return I18N["en"][key] || key;
}

function updateDOMTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (el.tagName === "INPUT" && el.getAttribute("placeholder")) {
      el.placeholder = t(key);
    } else {
      el.textContent = t(key);
    }
  });
}

/**
 * ACGMS Client Application Controller.
 * Comprehensive SPA supporting Role Switching, Live Z-Score Assessment,
 * Child Registration, WHO Growth Charts, Immunisation Tracking, Supervisor Visits,
 * Malnutrition Surveillance Dashboards, and Offline-First Sync.
 */

class ACGMSApp {
  constructor() {
    this.apiBase = "/api/v1";
    this.token = localStorage.getItem("acgms_token") || null;
    this.currentUser = null;
    this.demoUsers = [];
    this.currentView = "dashboard";
    this.children = [];
    this.alerts = [];
    this.dashboardData = null;
    this.rankedAwcs = [];
    this.selectedChild = null;
    this.isOfflineSimulated = false;
    this.chartRenderer = null;
    this.distChart = null;
    this.trendChart = null;
    this.currentChartIndicator = "WFA";
    this.selectedChartChildId = null;
    this.hierarchy = [];
    this.allAwcs = [];
    this.selectedSupervisorAwcId = 1;
    this.dashboardFilters = { block_id: '', sector_id: '', awc_id: '', age_group: '', sex: '' };
    this.childMeasurements = [];
  }

  async init() {
    // 1. Initialize offline IndexedDB
    try {
      await window.offlineDB.init();
      this.updateOfflineCounter();
    } catch (e) {
      console.warn("IndexedDB init error:", e);
    }

    // 2. Fetch demo users & master hierarchy
    await this.loadDemoUsers();
    await this.loadHierarchy();

    // 3. Authenticate initial user (default to aww_sunita if not logged in)
    if (!this.token) {
      await this.loginUser("aww_sunita", "password123");
    } else {
      await this.fetchCurrentUser();
    }

    // 4. Setup Growth Chart Renderer
    this.chartRenderer = new GrowthChartRenderer("whoGrowthChartCanvas");

    // 5. Initial View Load
    this.switchView("dashboard");
    updateDOMTranslations();

    // 6. Network status listeners
    window.addEventListener("online", () => this.handleNetworkChange(true));
    window.addEventListener("offline", () => this.handleNetworkChange(false));
  }

  async loadDemoUsers() {
    try {
      const res = await fetch(`${this.apiBase}/auth/demo-users`);
      if (res.ok) {
        this.demoUsers = await res.json();
        this.renderDemoUserSelector();
      }
    } catch (e) {
      console.error("Failed to load demo users:", e);
    }
  }

  renderDemoUserSelector() {
    const selector = document.getElementById("demoUserSelector");
    if (!selector) return;
    selector.innerHTML = this.demoUsers.map(u => `
      <option value="${u.username}" ${this.currentUser && this.currentUser.username === u.username ? "selected" : ""}>
        ${u.full_name} (${u.role} - ${u.jurisdiction})
      </option>
    `).join("");
  }

  async loadHierarchy() {
    try {
      const res = await this.authFetch(`${this.apiBase}/master/hierarchy`);
      if (res.ok) {
        this.hierarchy = await res.json();
        this.populateHierarchyFilters();
      }
      const resAwcs = await this.authFetch(`${this.apiBase}/master/awcs`);
      if (resAwcs.ok) {
        this.allAwcs = await resAwcs.json();
        this.populateAwcSelectors();
      }
    } catch (e) {
      console.warn("Hierarchy load error:", e);
    }
  }

  populateHierarchyFilters() {
    const blockSel = document.getElementById("dashBlockFilter");
    const sectorSel = document.getElementById("dashSectorFilter");
    if (!blockSel) return;

    let blocks = [];
    let sectors = [];
    this.hierarchy.forEach(d => {
      d.blocks.forEach(b => {
        blocks.push(b);
        b.sectors.forEach(s => sectors.push(s));
      });
    });

    blockSel.innerHTML = `<option value="">All Blocks</option>` + blocks.map(b => `<option value="${b.id}">${b.name}</option>`).join("");
    if (sectorSel) {
      sectorSel.innerHTML = `<option value="">All Sectors</option>` + sectors.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
    }
  }

  populateAwcSelectors() {
    const dashAwcSel = document.getElementById("dashAwcFilter");
    if (dashAwcSel) {
      dashAwcSel.innerHTML = `<option value="">All AWCs</option>` + this.allAwcs.map(a => `<option value="${a.id}">${a.name} (${a.code})</option>`).join("");
    }
    const supSel = document.getElementById("supervisorAwcSelector");
    if (supSel) {
      supSel.innerHTML = this.allAwcs.map(a => `<option value="${a.id}" ${a.id === this.selectedSupervisorAwcId ? "selected" : ""}>${a.name}</option>`).join("");
    }
    const transferSel = document.getElementById("transferTargetAwc");
    if (transferSel) {
      transferSel.innerHTML = this.allAwcs.map(a => `<option value="${a.id}">${a.name} (${a.code} - ${a.village})</option>`).join("");
    }
  }

  async loginUser(username, password = "password123") {
    try {
      const res = await fetch(`${this.apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      if (res.ok) {
        const data = await res.json();
        this.token = data.access_token;
        this.currentUser = data.user;
        localStorage.setItem("acgms_token", this.token);
        this.updateUserBadge();
        this.renderDemoUserSelector();
        this.refreshCurrentView();
        this.showToast(`Logged in as ${this.currentUser.full_name} (${this.currentUser.role})`, "success");
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Authentication failed", "error");
      }
    } catch (e) {
      console.error("Login error:", e);
      this.showToast("Network error during login", "error");
    }
  }

  async fetchCurrentUser() {
    try {
      const res = await this.authFetch(`${this.apiBase}/auth/me`);
      if (res.ok) {
        this.currentUser = await res.json();
        this.updateUserBadge();
        this.renderDemoUserSelector();
      } else {
        // Fallback to demo login
        await this.loginUser("aww_sunita", "password123");
      }
    } catch (e) {
      await this.loginUser("aww_sunita", "password123");
    }
  }

  updateUserBadge() {
    const badge = document.getElementById("currentUserBadge");
    if (badge && this.currentUser) {
      badge.innerHTML = `
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-900 border border-blue-200">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          ${this.currentUser.full_name} (${this.currentUser.role})
        </span>
      `;
    }
  }

  async authFetch(url, options = {}) {
    if (this.isOfflineSimulated && !url.includes("preview")) {
      throw new Error("SIMULATED_OFFLINE");
    }
    const headers = options.headers ? { ...options.headers } : {};
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return fetch(url, { ...options, headers });
  }

  switchView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll(".nav-link").forEach(el => {
      if (el.getAttribute("data-view") === viewName) {
        el.classList.add("bg-blue-800", "text-white");
        el.classList.remove("text-blue-100", "hover:bg-blue-800/50");
      } else {
        el.classList.remove("bg-blue-800", "text-white");
        el.classList.add("text-blue-100", "hover:bg-blue-800/50");
      }
    });

    document.querySelectorAll(".view-section").forEach(s => s.classList.add("hidden"));
    const activeSection = document.getElementById(`view-${viewName}`);
    if (activeSection) activeSection.classList.remove("hidden");

    this.refreshCurrentView();
  }

  async refreshCurrentView() {
    if (this.currentView === "dashboard") {
      await this.loadDashboard();
    } else if (this.currentView === "children") {
      await this.loadChildren();
    } else if (this.currentView === "alerts") {
      await this.loadAlerts();
    } else if (this.currentView === "supervisor") {
      await this.loadSupervisorView();
    }
    updateDOMTranslations();
  }

  // ==========================================
  // DASHBOARD VIEW
  // ==========================================
  async loadDashboard() {
    try {
      const q = new URLSearchParams();
      if (this.dashboardFilters.block_id) q.set("block_id", this.dashboardFilters.block_id);
      if (this.dashboardFilters.sector_id) q.set("sector_id", this.dashboardFilters.sector_id);
      if (this.dashboardFilters.awc_id) q.set("awc_id", this.dashboardFilters.awc_id);
      if (this.dashboardFilters.age_group) q.set("age_group", this.dashboardFilters.age_group);
      if (this.dashboardFilters.sex) q.set("sex", this.dashboardFilters.sex);

      const qs = q.toString() ? `?${q.toString()}` : "";
      const res = await this.authFetch(`${this.apiBase}/dashboards/overview${qs}`);
      if (res.ok) {
        const data = await res.json();
        this.dashboardData = data;
        this.renderDashboardKPIs(data.summary);
        this.renderCharts(data.summary, data.trends);
      }

      const resRanked = await this.authFetch(`${this.apiBase}/dashboards/ranked-awcs${this.dashboardFilters.block_id ? `?block_id=${this.dashboardFilters.block_id}` : ''}`);
      if (resRanked.ok) {
        this.rankedAwcs = await resRanked.json();
        this.renderRankedAwcsTable();
      }
    } catch (e) {
      console.warn("Dashboard load error (offline):", e);
    }
  }

  onDashboardFilterChange() {
    this.dashboardFilters.block_id = document.getElementById("dashBlockFilter")?.value || "";
    this.dashboardFilters.sector_id = document.getElementById("dashSectorFilter")?.value || "";
    this.dashboardFilters.awc_id = document.getElementById("dashAwcFilter")?.value || "";
    this.dashboardFilters.age_group = document.getElementById("dashAgeFilter")?.value || "";
    this.dashboardFilters.sex = document.getElementById("dashSexFilter")?.value || "";
    this.loadDashboard();
  }

  resetDashboardFilters() {
    this.dashboardFilters = { block_id: '', sector_id: '', awc_id: '', age_group: '', sex: '' };
    if (document.getElementById("dashBlockFilter")) document.getElementById("dashBlockFilter").value = "";
    if (document.getElementById("dashSectorFilter")) document.getElementById("dashSectorFilter").value = "";
    if (document.getElementById("dashAwcFilter")) document.getElementById("dashAwcFilter").value = "";
    if (document.getElementById("dashAgeFilter")) document.getElementById("dashAgeFilter").value = "";
    if (document.getElementById("dashSexFilter")) document.getElementById("dashSexFilter").value = "";
    this.loadDashboard();
  }

  renderDashboardKPIs(s) {
    document.getElementById("kpiEnrolled").textContent = s.total_children || 0;
    document.getElementById("kpiMeasured").textContent = `${s.measured_this_month || 0} (${s.measurement_coverage_pct || 0}%)`;
    document.getElementById("kpiSAM").textContent = `${s.sam_count || 0} (${s.sam_pct || 0}%)`;
    document.getElementById("kpiMAM").textContent = `${s.mam_count || 0} (${s.mam_pct || 0}%)`;
    document.getElementById("kpiRecovering").textContent = `${s.recovering_count || 0} (${s.recovering_pct || 0}%)`;
    document.getElementById("kpiNormal").textContent = `${s.normal_count || 0} (${s.normal_pct || 0}%)`;
    document.getElementById("kpiUnderweight").textContent = `${s.underweight_count || 0} (${s.underweight_pct || 0}%)`;
    document.getElementById("kpiStunted").textContent = `${s.stunted_count || 0} (${s.stunted_pct || 0}%)`;
    document.getElementById("kpiVisitCoverage").textContent = `${s.visited_awcs_last_30d || 0} / ${s.total_awcs || 0} (${s.visit_coverage_pct || 0}%)`;
    document.getElementById("kpiAdherence").textContent = `${s.avg_immunisation_adherence_pct || 0}%`;
  }

  renderCharts(summary, trends) {
    // 1. Doughnut Chart for Nutritional Breakdown
    const distCanvas = document.getElementById("malnutritionDistChart");
    if (distCanvas) {
      if (this.distChart) this.distChart.destroy();
      this.distChart = new Chart(distCanvas, {
        type: "doughnut",
        data: {
          labels: ["Normal", "MAM", "SAM", "Recovering"],
          datasets: [{
            data: [summary.normal_count, summary.mam_count, summary.sam_count, summary.recovering_count],
            backgroundColor: ["#16a34a", "#f59e0b", "#dc2626", "#0284c7"],
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12 } }
          }
        }
      });
    }

    // 2. Trend Line Chart for Past 6 Months
    const trendCanvas = document.getElementById("momTrendChart");
    if (trendCanvas && trends) {
      if (this.trendChart) this.trendChart.destroy();
      this.trendChart = new Chart(trendCanvas, {
        type: "line",
        data: {
          labels: trends.map(t => t.month),
          datasets: [
            {
              label: "Normal",
              data: trends.map(t => t.normal),
              borderColor: "#16a34a",
              backgroundColor: "rgba(22, 163, 74, 0.1)",
              fill: true,
              tension: 0.3
            },
            {
              label: "MAM",
              data: trends.map(t => t.mam),
              borderColor: "#f59e0b",
              backgroundColor: "transparent",
              tension: 0.3
            },
            {
              label: "SAM (Severe)",
              data: trends.map(t => t.sam),
              borderColor: "#dc2626",
              backgroundColor: "transparent",
              borderWidth: 3,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12 } }
          },
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    }
  }

  renderRankedAwcsTable() {
    const tbody = document.getElementById("rankedAwcsTableBody");
    if (!tbody) return;
    tbody.innerHTML = this.rankedAwcs.map(a => `
      <tr class="hover:bg-slate-50 border-b border-slate-100">
        <td class="px-4 py-3 font-semibold text-slate-800">${a.awc_name} <span class="text-xs text-slate-400 block">${a.awc_code}</span></td>
        <td class="px-4 py-3 text-slate-600">${a.village} (${a.sector_name})</td>
        <td class="px-4 py-3 text-center text-slate-700">${a.total_enrolled}</td>
        <td class="px-4 py-3 text-center">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${a.coverage_pct >= 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${a.measured_this_month} (${a.coverage_pct}%)
          </span>
        </td>
        <td class="px-4 py-3 text-center">
          <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${a.sam_count > 0 ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-slate-100 text-slate-600'}">
            ${a.sam_count} (${a.sam_prevalence_pct}%)
          </span>
        </td>
        <td class="px-4 py-3 text-center text-slate-700">${a.mam_count}</td>
      </tr>
    `).join("");
  }

  // ==========================================
  // CHILDREN DIRECTORY
  // ==========================================
  async loadChildren() {
    const search = document.getElementById("childSearchInput")?.value || "";
    const stateFilter = document.getElementById("childStateFilter")?.value || "";
    const ageFilter = document.getElementById("childAgeFilter")?.value || "";

    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (stateFilter) params.append("nutritional_state", stateFilter);
    if (ageFilter) params.append("age_group", ageFilter);

    try {
      const res = await this.authFetch(`${this.apiBase}/children?${params.toString()}`);
      if (res.ok) {
        this.children = await res.json();
        this.renderChildrenTable();
      }
    } catch (e) {
      console.warn("Children fetch error (offline):", e);
    }
  }

  renderChildrenTable() {
    const tbody = document.getElementById("childrenTableBody");
    if (!tbody) return;

    if (this.children.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-8 text-center text-slate-400">No children found matching the selected criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.children.map(c => {
      let stateBadge = "badge-normal";
      if (c.current_state === "SAM") stateBadge = "badge-sam pulse-urgent";
      else if (c.current_state === "MAM") stateBadge = "badge-mam";
      else if (c.current_state === "Recovering") stateBadge = "badge-recovering";

      const genderBadge = c.sex === "M"
        ? '<span class="text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded text-xs">Boy</span>'
        : '<span class="text-pink-600 font-semibold bg-pink-50 px-2 py-0.5 rounded text-xs">Girl</span>';

      return `
        <tr class="hover:bg-slate-50 border-b border-slate-100">
          <td class="px-4 py-3 font-semibold text-slate-800">
            ${c.name}
            <span class="text-xs text-slate-400 block">${c.child_id}</span>
          </td>
          <td class="px-4 py-3 text-center">${genderBadge}</td>
          <td class="px-4 py-3 text-slate-600">
            ${c.age_months !== undefined ? c.age_months : '-'} mos
            <span class="text-xs text-slate-400 block">${c.dob}</span>
          </td>
          <td class="px-4 py-3 text-slate-700">
            ${c.guardian_name}
            <span class="text-xs text-slate-400 block">${c.address_village} • ${c.mobile || 'No mobile'}</span>
          </td>
          <td class="px-4 py-3 text-center">
            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs ${stateBadge}">
              ${c.current_state}
            </span>
          </td>
          <td class="px-4 py-3 text-center">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${c.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}">
              ${c.status}
            </span>
          </td>
          <td class="px-4 py-3 text-right">
            <div class="inline-flex items-center gap-1.5 flex-wrap justify-end">
              <button onclick="app.openMeasurementModal(${c.id})" class="px-2 py-1 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold" title="Record Growth">
                + Measure
              </button>
              <button onclick="app.openGrowthChartModal(${c.id})" class="px-2 py-1 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-xs font-semibold" title="WHO Growth Curves">
                Chart
              </button>
              <button onclick="app.openImmunisationModal(${c.id})" class="px-2 py-1 rounded bg-purple-50 text-purple-700 hover:bg-purple-100 text-xs font-semibold" title="Vaccines">
                Vaccines
              </button>
              <button onclick="app.openChildHistoryModal(${c.id})" class="px-2 py-1 rounded bg-amber-50 text-amber-700 hover:bg-amber-100 text-xs font-semibold" title="History & 7-Day Correction">
                History
              </button>
              <button onclick="app.openTransferChildModal(${c.id})" class="px-2 py-1 rounded bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-semibold" title="Transfer Centre">
                Transfer
              </button>
              <button onclick="app.openChildStatusModal(${c.id})" class="px-2 py-1 rounded bg-rose-50 text-rose-700 hover:bg-rose-100 text-xs font-semibold" title="Lifecycle Status">
                Status
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  }

  // ==========================================
  // LIVE MEASUREMENT MODAL & PREVIEW
  // ==========================================
  openMeasurementModal(childId) {
    const child = this.children.find(c => c.id === childId);
    if (!child) return;
    this.selectedChild = child;

    document.getElementById("measChildName").textContent = `${child.name} (${child.sex === 'M' ? 'Boy' : 'Girl'}, ${child.age_months} months)`;
    document.getElementById("measChildId").value = child.id;
    document.getElementById("measDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("measWeight").value = "";
    document.getElementById("measHeight").value = "";
    document.getElementById("measMUAC").value = "";
    document.getElementById("measOedema").checked = false;
    document.getElementById("measConfirmImplausible").checked = false;
    document.getElementById("implausibleWarningBox").classList.add("hidden");

    // Default recommended posture based on age (<24m recumbent, >=24m standing)
    const postureSelect = document.getElementById("measPosture");
    if (postureSelect) {
      postureSelect.value = (child.age_months < 24) ? "RECUMBENT" : "STANDING";
    }

    this.resetLivePreview();
    document.getElementById("measurementModal").classList.remove("hidden");
  }

  closeMeasurementModal() {
    document.getElementById("measurementModal").classList.add("hidden");
  }

  async updateLiveMeasurementPreview() {
    if (!this.selectedChild) return;
    const weight = parseFloat(document.getElementById("measWeight").value);
    const height = parseFloat(document.getElementById("measHeight").value);
    const posture = document.getElementById("measPosture").value;
    const muac = parseFloat(document.getElementById("measMUAC").value) || null;
    const oedema = document.getElementById("measOedema").checked;
    const measDate = document.getElementById("measDate").value;

    if (!weight || !height || weight <= 0 || height <= 0) {
      this.resetLivePreview();
      return;
    }

    try {
      const res = await fetch(`${this.apiBase}/measurements/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sex: this.selectedChild.sex,
          dob: this.selectedChild.dob,
          measurement_date: measDate,
          weight_kg: weight,
          length_height_cm: height,
          posture: posture,
          muac_cm: muac,
          oedema: oedema
        })
      });

      if (res.ok) {
        const preview = await res.json();
        if (preview.is_valid) {
          document.getElementById("previewWHZ").textContent = preview.zscores.whz;
          document.getElementById("previewWAZ").textContent = preview.zscores.waz;
          document.getElementById("previewHAZ").textContent = preview.zscores.haz;

          const classBadge = document.getElementById("previewClassBadge");
          classBadge.textContent = preview.acute_class;
          classBadge.className = "inline-flex items-center px-3 py-1 rounded-full text-xs font-bold " +
            (preview.acute_class === "SAM" ? "badge-sam pulse-urgent" : (preview.acute_class === "MAM" ? "badge-mam" : "badge-normal"));

          // Posture correction banner (FR-GM-03)
          const postureBanner = document.getElementById("previewPostureCorrection");
          if (preview.zscores.posture_corrected) {
            postureBanner.classList.remove("hidden");
            postureBanner.textContent = `Posture correction applied: Adjusted dimension is ${preview.zscores.corrected_dimension} cm (±0.7 cm rule)`;
          } else {
            postureBanner.classList.add("hidden");
          }

          // Implausible warning (FR-GM-05)
          const implausibleBox = document.getElementById("implausibleWarningBox");
          if (preview.is_implausible) {
            implausibleBox.classList.remove("hidden");
            document.getElementById("implausibleReason").textContent = preview.plausibility_flags.join("; ");
          } else {
            implausibleBox.classList.add("hidden");
          }
        }
      }
    } catch (e) {
      console.warn("Live preview offline or error:", e);
    }
  }

  resetLivePreview() {
    document.getElementById("previewWHZ").textContent = "--";
    document.getElementById("previewWAZ").textContent = "--";
    document.getElementById("previewHAZ").textContent = "--";
    const classBadge = document.getElementById("previewClassBadge");
    classBadge.textContent = "Awaiting input";
    classBadge.className = "inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-600";
    document.getElementById("previewPostureCorrection").classList.add("hidden");
  }

  async saveMeasurement() {
    if (!this.selectedChild) return;
    const weight = parseFloat(document.getElementById("measWeight").value);
    const height = parseFloat(document.getElementById("measHeight").value);
    const posture = document.getElementById("measPosture").value;
    const muac = parseFloat(document.getElementById("measMUAC").value) || null;
    const oedema = document.getElementById("measOedema").checked;
    const dateVal = document.getElementById("measDate").value;
    const confirmImplausible = document.getElementById("measConfirmImplausible").checked;

    if (!weight || !height) {
      this.showToast("Please enter weight and length/height.", "error");
      return;
    }

    const payload = {
      child_id: this.selectedChild.id,
      date: dateVal,
      weight_kg: weight,
      length_height_cm: height,
      posture: posture,
      muac_cm: muac,
      oedema: oedema,
      confirm_implausible: confirmImplausible
    };

    // If simulated offline or disconnected, queue into IndexedDB!
    if (this.isOfflineSimulated || !navigator.onLine) {
      await window.offlineDB.queueMeasurement(payload);
      await this.updateOfflineCounter();
      this.closeMeasurementModal();
      this.showToast("Saved offline to pending queue! Will sync automatically when online.", "info");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/measurements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        this.closeMeasurementModal();
        this.showToast("Measurement & WHO Z-scores recorded successfully!", "success");
        await this.refreshCurrentView();
      } else {
        const err = await res.json();
        const msg = (err.detail && err.detail.message) ? `${err.detail.message}: ${err.detail.errors?.join(", ") || ""}` : (err.detail || "Error saving measurement");
        this.showToast(msg, "error");
      }
    } catch (e) {
      // Network failure -> automatically store offline
      await window.offlineDB.queueMeasurement(payload);
      await this.updateOfflineCounter();
      this.closeMeasurementModal();
      this.showToast("Network unreachable. Measurement saved to offline queue.", "info");
    }
  }

  // ==========================================
  // WHO GROWTH CHART MODAL (FR-GM-08)
  // ==========================================
  async openGrowthChartModal(childId) {
    this.selectedChartChildId = childId;
    this.currentChartIndicator = "WFA";
    this.updateGrowthChartTabs("WFA");
    await this.fetchAndRenderGrowthChart("WFA");
    document.getElementById("growthChartModal").classList.remove("hidden");
  }

  updateGrowthChartTabs(activeInd) {
    ["WFA", "HFA", "WFH"].forEach(ind => {
      const btn = document.getElementById(`chartTab${ind}`);
      if (btn) {
        if (ind === activeInd) {
          btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-600 text-white shadow-sm transition-all";
        } else {
          btn.className = "px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all";
        }
      }
    });
  }

  async switchGrowthChartIndicator(indicator) {
    this.currentChartIndicator = indicator;
    this.updateGrowthChartTabs(indicator);
    await this.fetchAndRenderGrowthChart(indicator);
  }

  async fetchAndRenderGrowthChart(indicator) {
    if (!this.selectedChartChildId) return;
    try {
      const res = await this.authFetch(`${this.apiBase}/measurements/child/${this.selectedChartChildId}/growth-chart?indicator=${indicator}`);
      if (res.ok) {
        const chartData = await res.json();
        document.getElementById("chartModalChildName").textContent = `${chartData.child.name} (${chartData.child.child_id}) — Status: ${chartData.child.current_state}`;
        this.chartRenderer.render(chartData);
      }
    } catch (e) {
      this.showToast("Failed to load growth chart data", "error");
    }
  }

  closeGrowthChartModal() {
    document.getElementById("growthChartModal").classList.add("hidden");
  }

  // ==========================================
  // DIGITAL IMMUNISATION CARD
  // ==========================================
  async openImmunisationModal(childId) {
    try {
      const res = await this.authFetch(`${this.apiBase}/immunisation/child/${childId}`);
      if (res.ok) {
        const card = await res.json();
        this.selectedChild = { id: childId, name: card.name };
        document.getElementById("immuChildName").textContent = `${card.name} (Adherence: ${card.adherence_pct}%)`;
        document.getElementById("immuAdherenceBar").style.width = `${card.adherence_pct}%`;
        document.getElementById("immuAdherenceText").textContent = `${card.adherence_pct}% Adherence`;

        const container = document.getElementById("immuDosesContainer");
        container.innerHTML = card.doses.map(d => {
          let badge = "bg-slate-100 text-slate-600";
          if (d.status === "GIVEN") badge = "bg-emerald-100 text-emerald-800 font-bold border border-emerald-300";
          else if (d.status === "DUE") badge = "bg-amber-100 text-amber-800 font-bold border border-amber-300";
          else if (d.status === "OVERDUE") badge = "bg-red-100 text-red-800 font-bold border border-red-300 pulse-urgent";

          return `
            <div class="flex items-center justify-between p-3 rounded-lg border border-slate-200 bg-white">
              <div>
                <span class="font-bold text-slate-800 text-sm">${d.name} (${d.code})</span>
                <span class="text-xs text-slate-400 block">${d.category} • Target Date: ${d.target_date}</span>
                ${d.given_date ? `<span class="text-xs text-emerald-600 font-semibold block">Given on: ${d.given_date} (Batch: ${d.batch_no || 'N/A'})</span>` : ''}
                ${d.escalate_to_ls ? `<span class="text-xs text-red-600 font-bold block">⚠️ Escalated to Supervisor (>30 days overdue)</span>` : ''}
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2.5 py-1 rounded-full text-xs ${badge}">${d.status}</span>
                ${d.status !== 'GIVEN' ? `
                  <button onclick="app.recordVaccineGiven('${d.code}', ${d.dose_no})" class="px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 text-xs font-semibold">
                    Mark Given
                  </button>
                ` : ''}
              </div>
            </div>
          `;
        }).join("");

        document.getElementById("immunisationModal").classList.remove("hidden");
      }
    } catch (e) {
      this.showToast("Failed to load immunisation card", "error");
    }
  }

  closeImmunisationModal() {
    document.getElementById("immunisationModal").classList.add("hidden");
  }

  async recordVaccineGiven(code, doseNo) {
    if (!this.selectedChild) return;
    const batch = prompt(`Enter batch number for ${code} (optional):`, "B-" + Math.floor(Math.random() * 900 + 100));
    try {
      const res = await this.authFetch(`${this.apiBase}/immunisation/record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          child_id: this.selectedChild.id,
          vaccine_code: code,
          dose_no: doseNo,
          given_date: new Date().toISOString().split("T")[0],
          batch_no: batch || "B-GENERAL"
        })
      });
      if (res.ok) {
        this.showToast(`Vaccine ${code} marked as given!`, "success");
        await this.openImmunisationModal(this.selectedChild.id);
      }
    } catch (e) {
      this.showToast("Failed to record vaccine dose", "error");
    }
  }

  // ==========================================
  // CHILD REGISTRATION MODAL
  // ==========================================
  openRegisterChildModal() {
    document.getElementById("regName").value = "";
    document.getElementById("regDob").value = "";
    document.getElementById("regGuardian").value = "";
    document.getElementById("regVillage").value = "Rampur";
    document.getElementById("regMobile").value = "";
    document.getElementById("regBirthWeight").value = "";
    document.getElementById("registerChildModal").classList.remove("hidden");
  }

  closeRegisterChildModal() {
    document.getElementById("registerChildModal").classList.add("hidden");
  }

  async saveChildRegistration() {
    const name = document.getElementById("regName").value.trim();
    const sex = document.getElementById("regSex").value;
    const dob = document.getElementById("regDob").value;
    const guardian = document.getElementById("regGuardian").value.trim();
    const relationship = document.getElementById("regRelationship").value;
    const village = document.getElementById("regVillage").value.trim();
    const mobile = document.getElementById("regMobile").value.trim() || null;
    const consent = document.getElementById("regConsent").checked;
    const birthWeight = parseFloat(document.getElementById("regBirthWeight").value) || null;

    if (!name || !dob || !guardian || !village) {
      this.showToast("Please fill in child name, DOB, guardian, and village.", "error");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/children`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          sex: sex,
          dob: dob,
          guardian_name: guardian,
          guardian_relationship: relationship,
          mobile: mobile,
          guardian_consent_sms: consent,
          address_village: village,
          awc_id: this.currentUser?.jurisdiction_id || 1,
          birth_weight_kg: birthWeight
        })
      });

      if (res.ok) {
        this.closeRegisterChildModal();
        this.showToast(`Child ${name} registered successfully!`, "success");
        await this.loadChildren();
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Registration failed", "error");
      }
    } catch (e) {
      this.showToast("Registration error", "error");
    }
  }

  // ==========================================
  // ALERTS & TASKS
  // ==========================================
  async loadAlerts() {
    try {
      const res = await this.authFetch(`${this.apiBase}/alerts`);
      if (res.ok) {
        this.alerts = await res.json();
        this.renderAlertsTable();
      }
    } catch (e) {
      console.warn("Alerts load error:", e);
    }
  }

  renderAlertsTable() {
    const container = document.getElementById("alertsListContainer");
    if (!container) return;

    if (this.alerts.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-400 bg-white rounded-xl border border-slate-200">No open alerts or pending tasks. All clear!</div>`;
      return;
    }

    container.innerHTML = this.alerts.map(a => {
      let badge = "bg-amber-100 text-amber-800 border-amber-200";
      if (a.priority === "HIGH") badge = "bg-red-100 text-red-800 border-red-200 pulse-urgent";
      
      let escalationBadge = "";
      if (a.escalation_level === 1) escalationBadge = '<span class="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded font-bold">Escalated to Supervisor (>7d)</span>';
      else if (a.escalation_level === 2) escalationBadge = '<span class="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded font-bold">Escalated to CDPO (>14d)</span>';

      return `
        <div class="p-4 rounded-xl border border-slate-200 bg-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="px-2.5 py-0.5 rounded-full text-xs font-bold border ${badge}">${a.priority} Priority</span>
              <span class="text-xs text-slate-400 font-mono">${a.alert_id}</span>
              ${escalationBadge}
            </div>
            <h4 class="font-bold text-slate-800 text-sm">${a.description}</h4>
            <span class="text-xs text-slate-400">Centre: ${a.awc_name || 'AWC'} • Created: ${a.created_at?.split("T")[0]}</span>
          </div>
          <div>
            ${a.status !== 'CLOSED' ? `
              <button onclick="app.openAcknowledgeModal(${a.id})" class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-semibold">
                Take Action / Resolve
              </button>
            ` : `
              <span class="text-xs text-emerald-700 font-semibold bg-emerald-50 px-3 py-1 rounded-full">Resolved: ${a.action_taken || 'Closed'}</span>
            `}
          </div>
        </div>
      `;
    }).join("");
  }

  openAcknowledgeModal(alertId) {
    const alert = this.alerts.find(a => a.id === alertId);
    if (!alert) return;
    this.selectedAlert = alert;
    document.getElementById("ackAlertDesc").textContent = alert.description;
    document.getElementById("acknowledgeModal").classList.remove("hidden");
  }

  closeAcknowledgeModal() {
    document.getElementById("acknowledgeModal").classList.add("hidden");
  }

  async submitAcknowledgeAlert() {
    if (!this.selectedAlert) return;
    const action = document.getElementById("ackActionSelect").value;
    const notes = document.getElementById("ackNotes").value;

    try {
      const res = await this.authFetch(`${this.apiBase}/alerts/${this.selectedAlert.id}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_taken: action, notes: notes })
      });
      if (res.ok) {
        this.closeAcknowledgeModal();
        this.showToast("Alert resolved and action recorded!", "success");
        await this.loadAlerts();
      }
    } catch (e) {
      this.showToast("Error acknowledging alert", "error");
    }
  }

  // ==========================================
  // SUPERVISOR VISITS & INSPECTIONS (FR-SV-01 to FR-SV-06)
  // ==========================================
  async changeSupervisorAwc(awcId) {
    this.selectedSupervisorAwcId = parseInt(awcId) || 1;
    await this.loadSupervisorView(this.selectedSupervisorAwcId);
  }

  async loadSupervisorView(awcId = null) {
    const targetAwcId = awcId || this.selectedSupervisorAwcId || 1;
    this.selectedSupervisorAwcId = targetAwcId;
    try {
      const resStats = await this.authFetch(`${this.apiBase}/visits/awc-stats/${targetAwcId}`);
      if (resStats.ok) {
        const stats = await resStats.json();
        document.getElementById("visitAwcName").textContent = `${stats.awc_name} (${stats.awc_code})`;
        document.getElementById("visitEnrolled").textContent = stats.enrolled_children;
        document.getElementById("visitMeasured").textContent = `${stats.measured_this_month} (${stats.coverage_pct}%)`;
        document.getElementById("visitSAM").textContent = stats.sam_count;
        document.getElementById("visitMAM").textContent = stats.mam_count;
      }

      const resVisits = await this.authFetch(`${this.apiBase}/visits/awc/${targetAwcId}`);
      if (resVisits.ok) {
        const visits = await resVisits.json();
        this.renderVisitsHistory(visits);
      }
    } catch (e) {
      console.warn("Supervisor load error:", e);
    }
  }

  renderVisitsHistory(visits) {
    const container = document.getElementById("visitsHistoryContainer");
    if (!container) return;
    if (visits.length === 0) {
      container.innerHTML = `<div class="p-6 text-center text-slate-400">No prior inspection reports on record for this centre.</div>`;
      return;
    }

    container.innerHTML = visits.map(v => `
      <div class="p-4 rounded-xl border border-slate-200 bg-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <span class="text-xs text-blue-600 font-mono font-bold">${v.visit_id}</span>
          <h4 class="font-bold text-slate-800 text-sm">Inspection on ${v.visit_date} (Attendance: ${v.attendance_count} children)</h4>
          <p class="text-xs text-slate-500 mt-1">${v.observations || 'Routine monthly supervision.'}</p>
        </div>
        <div>
          <a href="${this.apiBase}/visits/${v.id}/pdf" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 text-xs font-semibold">
            📄 Download Official PDF Report
          </a>
        </div>
      </div>
    `).join("");
  }

  async saveSupervisorInspection() {
    const awcId = this.selectedSupervisorAwcId || 1;
    const dateVal = document.getElementById("visitDate").value || new Date().toISOString().split("T")[0];
    const attendance = parseInt(document.getElementById("visitAttendance").value) || 15;
    const registerScore = parseInt(document.getElementById("visitRegisterScore").value) || 5;
    const equipmentCalib = document.getElementById("visitEquipmentCalib").checked;
    const cleanlinessScore = parseInt(document.getElementById("visitCleanlinessScore").value) || 5;
    const thrDelivered = document.getElementById("visitTHRDelivered").checked;
    const observations = document.getElementById("visitObservations").value;

    try {
      const res = await this.authFetch(`${this.apiBase}/visits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          awc_id: awcId,
          visit_date: dateVal,
          attendance_count: attendance,
          register_upkeep_score: registerScore,
          equipment_functional: equipmentCalib,
          cleanliness_score: cleanlinessScore,
          sn_delivered: thrDelivered,
          observations: observations,
          action_items: [
            {
              description: "Review dietary supplement allocation for MAM children",
              owner_role: "AWW",
              owner_name: "Sunita Devi",
              due_date: new Date(Date.now() + 5*86400000).toISOString().split("T")[0]
            }
          ]
        })
      });

      if (res.ok) {
        this.showToast("Inspection visit report saved! PDF ready for download.", "success");
        await this.loadSupervisorView(awcId);
      }
    } catch (e) {
      this.showToast("Failed to save inspection report", "error");
    }
  }

  // ==========================================
  // CHILD MEASUREMENT HISTORY & 7-DAY CORRECTION (FR-GM-06)
  // ==========================================
  async openChildHistoryModal(childId) {
    const child = this.children.find(c => c.id === childId);
    if (!child) return;
    this.selectedChild = child;
    document.getElementById("historyChildName").textContent = `${child.name} (${child.child_id}, Status: ${child.current_state})`;
    document.getElementById("correctionFormPanel").classList.add("hidden");
    
    try {
      const res = await this.authFetch(`${this.apiBase}/measurements/child/${childId}`);
      if (res.ok) {
        this.childMeasurements = await res.json();
        this.renderHistoryTable();
        document.getElementById("childHistoryModal").classList.remove("hidden");
      }
    } catch (e) {
      this.showToast("Failed to load measurement history", "error");
    }
  }

  closeChildHistoryModal() {
    document.getElementById("childHistoryModal").classList.add("hidden");
  }

  renderHistoryTable() {
    const tbody = document.getElementById("historyTableBody");
    if (!tbody) return;
    if (this.childMeasurements.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="p-4 text-center text-slate-400">No longitudinal measurements recorded yet.</td></tr>`;
      return;
    }

    const today = new Date();
    tbody.innerHTML = this.childMeasurements.map(m => {
      const mDate = new Date(m.date);
      const daysDiff = Math.floor((today - mDate) / (1000 * 60 * 60 * 24));
      const canEdit = daysDiff <= 7 || (this.currentUser && this.currentUser.role === "ADMIN");

      let clsBadge = "bg-emerald-100 text-emerald-800";
      if (m.acute_class === "SAM") clsBadge = "bg-red-100 text-red-800 font-bold";
      else if (m.acute_class === "MAM") clsBadge = "bg-amber-100 text-amber-800 font-bold";

      return `
        <tr class="hover:bg-slate-50 border-b border-slate-100">
          <td class="px-3 py-2 font-mono">${m.date}</td>
          <td class="px-3 py-2">${m.age_months}m</td>
          <td class="px-3 py-2 font-bold">${m.weight_kg} kg</td>
          <td class="px-3 py-2">${m.length_height_cm} cm</td>
          <td class="px-3 py-2">${m.muac_cm ? m.muac_cm + ' cm' : '-'}</td>
          <td class="px-3 py-2 text-center font-bold font-mono">${m.whz}</td>
          <td class="px-3 py-2 text-center font-mono">${m.waz}</td>
          <td class="px-3 py-2 text-center font-mono">${m.haz}</td>
          <td class="px-3 py-2 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] ${clsBadge}">${m.acute_class}</span></td>
          <td class="px-3 py-2 text-right">
            ${canEdit ? `
              <button onclick="app.startCorrection(${m.id})" class="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-600 text-white font-bold text-[11px] shadow-sm">
                ✏️ Correct
              </button>
            ` : `<span class="text-slate-400 text-[10px]">Locked (>7d)</span>`}
          </td>
        </tr>
      `;
    }).join("");
  }

  startCorrection(measId) {
    const meas = this.childMeasurements.find(m => m.id === measId);
    if (!meas) return;
    document.getElementById("corrMeasId").value = meas.id;
    document.getElementById("corrWeight").value = meas.weight_kg;
    document.getElementById("corrHeight").value = meas.length_height_cm;
    document.getElementById("corrPosture").value = meas.posture || "RECUMBENT";
    document.getElementById("corrMUAC").value = meas.muac_cm || "";
    document.getElementById("corrReason").value = "";
    document.getElementById("correctionFormPanel").classList.remove("hidden");
  }

  cancelCorrection() {
    document.getElementById("correctionFormPanel").classList.add("hidden");
  }

  async submitMeasurementCorrection() {
    const measId = document.getElementById("corrMeasId").value;
    const weight = parseFloat(document.getElementById("corrWeight").value);
    const height = parseFloat(document.getElementById("corrHeight").value);
    const posture = document.getElementById("corrPosture").value;
    const muac = parseFloat(document.getElementById("corrMUAC").value) || null;
    const reason = document.getElementById("corrReason").value.trim();

    if (!reason) {
      this.showToast("Please provide a mandatory reason for correction", "error");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/measurements/${measId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          weight_kg: weight,
          length_height_cm: height,
          posture: posture,
          muac_cm: muac,
          correction_reason: reason
        })
      });

      if (res.ok) {
        this.showToast("Measurement corrected! State trajectory re-evaluated.", "success");
        this.cancelCorrection();
        await this.openChildHistoryModal(this.selectedChild.id);
        await this.loadChildren();
        if (this.currentView === "dashboard") await this.loadDashboard();
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Correction failed", "error");
      }
    } catch (e) {
      this.showToast("Error saving correction", "error");
    }
  }

  // ==========================================
  // CHILD TRANSFER & STATUS (FR-REG-04, FR-REG-05)
  // ==========================================
  openTransferChildModal(childId) {
    const child = this.children.find(c => c.id === childId);
    if (!child) return;
    this.selectedChild = child;
    document.getElementById("transferChildId").value = child.id;
    document.getElementById("transferChildName").textContent = `${child.name} (${child.child_id})`;
    document.getElementById("transferCurrentAwc").value = child.awc_name || `AWC #${child.awc_id}`;
    document.getElementById("transferReason").value = "";
    this.populateAwcSelectors();
    document.getElementById("transferChildModal").classList.remove("hidden");
  }

  closeTransferChildModal() {
    document.getElementById("transferChildModal").classList.add("hidden");
  }

  async submitChildTransfer() {
    const childId = document.getElementById("transferChildId").value;
    const targetAwcId = parseInt(document.getElementById("transferTargetAwc").value);
    const reason = document.getElementById("transferReason").value.trim();

    if (!targetAwcId || !reason) {
      this.showToast("Target AWC and reason are required", "error");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/children/${childId}/transfer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_awc_id: targetAwcId,
          reason: reason
        })
      });

      if (res.ok) {
        this.closeTransferChildModal();
        this.showToast("Child transferred successfully!", "success");
        await this.loadChildren();
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Transfer failed", "error");
      }
    } catch (e) {
      this.showToast("Transfer request error", "error");
    }
  }

  openChildStatusModal(childId) {
    const child = this.children.find(c => c.id === childId);
    if (!child) return;
    this.selectedChild = child;
    document.getElementById("statusChildId").value = child.id;
    document.getElementById("statusChildName").textContent = `${child.name} (Current: ${child.status})`;
    document.getElementById("childNewStatus").value = child.status || "ACTIVE";
    document.getElementById("childStatusDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("childStatusReason").value = "";
    document.getElementById("childStatusModal").classList.remove("hidden");
  }

  closeChildStatusModal() {
    document.getElementById("childStatusModal").classList.add("hidden");
  }

  async submitChildStatusUpdate() {
    const childId = document.getElementById("statusChildId").value;
    const statusVal = document.getElementById("childNewStatus").value;
    const statusDate = document.getElementById("childStatusDate").value;
    const reason = document.getElementById("childStatusReason").value.trim();

    if (!reason) {
      this.showToast("Please provide a reason / case note", "error");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/children/${childId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: statusVal,
          status_date: statusDate,
          reason: reason
        })
      });

      if (res.ok) {
        this.closeChildStatusModal();
        this.showToast(`Child status updated to ${statusVal}!`, "success");
        await this.loadChildren();
      } else {
        const err = await res.json();
        this.showToast(err.detail || "Status update failed", "error");
      }
    } catch (e) {
      this.showToast("Status update error", "error");
    }
  }

  // ==========================================
  // OFFLINE QUEUE & BACKGROUND SYNC
  // ==========================================
  async toggleOfflineSimulation() {
    this.isOfflineSimulated = !this.isOfflineSimulated;
    const banner = document.getElementById("offlineBanner");
    const toggleBtn = document.getElementById("offlineToggleBtn");

    if (this.isOfflineSimulated) {
      banner.classList.remove("hidden");
      toggleBtn.textContent = "Switch to Online Mode";
      toggleBtn.classList.replace("bg-slate-200", "bg-emerald-600");
      toggleBtn.classList.replace("text-slate-800", "text-white");
      this.showToast("Simulating offline field environment (2G/No connectivity). Entries will queue in IndexedDB.", "info");
    } else {
      banner.classList.add("hidden");
      toggleBtn.textContent = "Simulate Offline Mode";
      toggleBtn.classList.replace("bg-emerald-600", "bg-slate-200");
      toggleBtn.classList.replace("text-white", "text-slate-800");
      this.showToast("Restored online mode. Ready to sync pending records.", "success");
      await this.triggerSync();
    }
  }

  async updateOfflineCounter() {
    const count = await window.offlineDB.getPendingCount();
    const badge = document.getElementById("pendingSyncBadge");
    if (badge) {
      badge.textContent = `${count} pending`;
      if (count > 0) {
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
  }

  async triggerSync() {
    const pending = await window.offlineDB.getAllPending();
    if (pending.measurements.length === 0 && pending.vaccine_records.length === 0) {
      this.showToast("No pending records to sync. All records are up to date!", "info");
      return;
    }

    try {
      const res = await this.authFetch(`${this.apiBase}/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pending)
      });

      if (res.ok) {
        const result = await res.json();
        await window.offlineDB.clearPending();
        await this.updateOfflineCounter();
        this.showToast(`Sync complete! ${result.synced_measurements} measurements & ${result.synced_vaccines} vaccines synced to server.`, "success");
        await this.refreshCurrentView();
      }
    } catch (e) {
      this.showToast("Sync failed: Check network connection.", "error");
    }
  }

  handleNetworkChange(isOnline) {
    if (isOnline && !this.isOfflineSimulated) {
      this.showToast("Network restored. Syncing pending data...", "info");
      this.triggerSync();
    }
  }

  showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    let bg = "bg-slate-800 text-white";
    if (type === "success") bg = "bg-emerald-700 text-white";
    else if (type === "error") bg = "bg-red-700 text-white";
    else if (type === "info") bg = "bg-blue-700 text-white";

    toast.className = `px-4 py-2.5 rounded-lg shadow-lg text-sm font-semibold flex items-center gap-2 transform transition-all duration-300 ${bg}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}

window.app = new ACGMSApp();
document.addEventListener("DOMContentLoaded", () => window.app.init());

(function() {
'use strict';

      document.addEventListener('DOMContentLoaded', function() {
      console.log('DOM loaded, initializing...');
      const C = window.CTCC;
      const form = document.getElementById("demo-form");
      console.log('Form element:', form);
      const apiBaseInput = document.getElementById("api-base");
      const messageInput = document.getElementById("message");
      const valuesInput = document.getElementById("values");
      const resultEl = document.getElementById("result");
      const statusEl = document.getElementById("status");
      const modeInputs = document.querySelectorAll('input[name="mode"]');
      const simpleSection = document.getElementById("simple-section");
      const bulkSection = document.getElementById("bulk-section");
      const ctccSection = document.getElementById("ctcc-section");
      console.log('Sections found:', {simpleSection, bulkSection, ctccSection});
      const loadStatus = document.getElementById("load-status");
      const tabsContainer = document.getElementById("tabs-container");
      const tabButtonsContainer = document.getElementById("tab-buttons");
      const tabContentsContainer = document.getElementById("tab-contents");
      const ctccJsonInputs = document.getElementById("ctcc-json-inputs");
      const ctccYamlMessage = document.getElementById("ctcc-yaml-message");
      const ctccInputModeInputs = document.querySelectorAll('input[name="ctcc-input-mode"]');
      const bulkSourceInputs = document.querySelectorAll('input[name="bulk-source"]');
      const bulkFileInput = document.getElementById("bulk-file-input");

      // Main tab elements
      const mainTabButtons = document.querySelectorAll('.main-tab-button');
      const mainTabContents = document.querySelectorAll('.main-tab-content');
      const statusBar = document.getElementById('status-bar');
      const statusBarIcon = document.getElementById('status-bar-icon');
      const statusBarLabel = document.getElementById('status-bar-label');
      const statusBarTimestamp = document.getElementById('status-bar-timestamp');
      const statusBarViewBtn = document.getElementById('status-bar-view-btn');
      document.getElementById('status-bar-save-btn').addEventListener('click', function(e) {
        e.preventDefault();
        showSaveDialog();
      });

      C.ctccJsonData = null;
      /** Cached from GET /api/fuel_mix_presets for Fuel Mixes dropdown. */
      C.cachedFuelMixPresets = [];

      // Taxonomy state (loaded once from GET /api/C.taxonomy)
      C.taxonomy = null;
      C.taxonomyById = {};
      C.taxonomyBySide = {};
      C.taxonomyByBucket = {};

      // Input metadata state (loaded once from GET /api/input_metadata)
      C.inputMetadata = null;
      C.activeTabIndex = 0;

      // Scenario management state
      C.sessionScenarios = [];
      C.activeScenarioId = null;
      C.activeScenarioName = '';
      C.lastRunResults = null;
      C.scenarioCounter = 0;
      C.comparisonScenarioIds = new Set();
      C.comparisonBaselineId = null;
      C.showDeltaVsBaseline = false;
      /** @type {'values_plus_delta'|'delta_only'} */
      C.comparisonDeltaDisplayMode = 'values_plus_delta';
      C.showComparisonPercentDelta = false;
      C.comparisonAutoSort = false;
      C.comparisonColumns = ['bcr_societal', 'grand_total_pv', 'total_capital_pv', 'total_benefits_pv'];

      C.routingValid = true;


      C.latestValidResults = null;
      C.autoCalcInFlight = false;
      C.autoCalcQueued = false;

      const autoCalculate = debounce(async function() {
        if (!C.activeScenarioId) return;
        if (typeof hasRequiredFields === 'function' && !hasRequiredFields()) return;
        if (C.autoCalcInFlight) { C.autoCalcQueued = true; return; }
        C.autoCalcInFlight = true;
        const calcScenarioId = C.activeScenarioId;
        document.dispatchEvent(new CustomEvent('ctcc-calc-started'));
        try {
          const baseUrl = apiBaseInput.value.trim();
          const payload = {
            mode: 'calculate',
            input_mode: 'json',
            output_mode: 'json',
            scenario_id: C.activeScenarioId,
            combined_data: collectJsonData()
          };
          const _authToken = await _getAuthToken();
          const _calcHeaders = { 'Content-Type': 'application/json' };
          if (_authToken) _calcHeaders['Authorization'] = 'Bearer ' + _authToken;
          const resp = await fetch(
            new URL('/api/ctcc/calculate', baseUrl).toString(),
            { method: 'POST', headers: _calcHeaders,
              body: JSON.stringify(payload) }
          );
          const json = await resp.json();
          if (calcScenarioId !== C.activeScenarioId) return;
          if (json.results) {
            C.latestValidResults = json.results;
            C.lastRunResults = json.results;
            renderCTCCResults(json.results);
            markResultsAvailable(0);
            document.dispatchEvent(new CustomEvent('ctcc-results-updated',
              { detail: { results: json.results } }));
            if (json.results._partial) {
              const warnings = json.results._warnings || [];
              const banner = document.createElement('div');
              banner.className = 'partial-results-banner';
              banner.innerHTML = '\u26a0\ufe0f Partial results \u2014 some modules failed: ' +
                  warnings.join(', ') +
                  ' <button onclick="this.parentElement.remove()" style="margin-left:1rem;cursor:pointer;border:none;background:none;color:#856404;font-weight:600;">Dismiss</button>';
              banner.style.cssText = 'background:#fff3cd;color:#856404;padding:0.75rem 1rem;border-radius:6px;margin-bottom:1rem;font-size:0.9rem;';
              const resultEl = document.getElementById('result');
              if (resultEl) resultEl.insertBefore(banner, resultEl.firstChild);
            }
          } else {
            if (json.error) {
              console.warn('Calculator error:', json.error);
              clearResults();
              const _re = document.getElementById('result');
              if (_re) {
                _re.innerHTML = '<div style="display:flex; align-items:center; justify-content:center; min-height:300px; color:#b00020; font-size:1.1rem; text-align:center;">' +
                  '<div><div style="font-size:2rem; margin-bottom:0.5rem;">&#9888;</div>' +
                  'Calculation error \u2014 check inputs and try again.<br>' +
                  '<span style="font-size:0.85rem; color:#999;">' + (json.error || '') + '</span></div></div>';
              }
            }
          }
        } catch (e) {
          console.error('Auto-calculate error:', e);
        } finally {
          C.autoCalcInFlight = false;
          const ind = document.getElementById('rcp-computing');
          if (ind) ind.style.display = 'none';
          if (C.autoCalcQueued) { C.autoCalcQueued = false; autoCalculate(); }
        }
      }, 300);


      /** Hierarchical add-column picker (fixed popover); see spec Tooling UX 3/23. */


      // Modal dialog — showModal/hideModal now in utils.js
      const modalOverlay = document.getElementById('modal-overlay');
      modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
          hideModal();
        }
      });

      // =============================================
      // Scenario Management
      // =============================================
      // Comparison: format 'text' / 'boolean' = absolutes only (no Δ / % Δ); see metricSupportsComparisonDelta.


      // --- Scenario Data Layer ---


      // --- Scenario List Rendering ---


      // --- Save & Export ---


      // Save dialog option selection
      document.querySelectorAll('.save-dialog .save-option').forEach(opt => {
        opt.addEventListener('click', () => {
          document.querySelectorAll('.save-dialog .save-option').forEach(o => o.classList.remove('selected'));
          opt.classList.add('selected');
        });
      });

      document.getElementById('save-cancel-btn').addEventListener('click', hideSaveDialog);

      let saveOverlayMouseDownTarget = null;
      document.getElementById('save-overlay').addEventListener('mousedown', function(e) {
        saveOverlayMouseDownTarget = e.target;
      });
      document.getElementById('save-overlay').addEventListener('click', function(e) {
        if (e.target === this && saveOverlayMouseDownTarget === this) hideSaveDialog();
      });

      document.getElementById('save-confirm-btn').addEventListener('click', async function() {
        const selected = document.querySelector('.save-dialog .save-option.selected');
        if (!selected) return;
        const option = selected.dataset.option;
        const currentInputs = collectJsonData();
        const resultsToSave = C.latestValidResults;

        if (option === 'memory') {
          const name = document.getElementById('save-memory-name').value.trim() || C.activeScenarioName || generateScenarioName('Scenario');
          if (C.activeScenarioId) {
            const s = C.sessionScenarios.find(s => s.id === C.activeScenarioId);
            if (s) {
              s.customName = name;
              s.inputs = JSON.parse(JSON.stringify(currentInputs));
              s.results = resultsToSave ? JSON.parse(JSON.stringify(resultsToSave)) : null;
              s.metadata.timestamp = new Date().toISOString();
              C.activeScenarioName = name;
              updateScenarioBreadcrumb();
              renderScenarioList();
              updateScenarioBadge();
              await saveScenarioToDB(s);
            }
          } else {
            addScenarioToSession(currentInputs, resultsToSave,
              { timestamp: new Date().toISOString(), source: 'manual' },
              name);
          }
          hideSaveDialog();
        } else if (option === 'ctcc') {
          const scenario = {
            version: '1.0',
            customName: document.getElementById('save-memory-name').value.trim() || 'Scenario',
            inputs: currentInputs,
            results: resultsToSave,
            metadata: { timestamp: new Date().toISOString(), source: 'export' }
          };
          exportAsCtcc(scenario);
          hideSaveDialog();
        } else if (option === 'csv') {
          const scenario = {
            version: '1.0',
            customName: document.getElementById('save-memory-name').value.trim() || 'Scenario',
            inputs: currentInputs,
            results: resultsToSave,
            metadata: { timestamp: new Date().toISOString(), source: 'export' }
          };
          exportAsCsv(scenario);
          hideSaveDialog();
        }
      });

      document.getElementById('save-scenario-main-btn').addEventListener('click', async () => {
        if (!C.activeScenarioId) {
          showToast('No active scenario to save.');
          return;
        }
        const scenario = C.sessionScenarios.find(s => s.id === C.activeScenarioId);
        if (!scenario) return;
        scenario.inputs = collectJsonData();
        scenario.results = C.lastRunResults;
        scenario.metadata.timestamp = new Date().toISOString();
        scenario.metadata.source = 'manual';
        renderScenarioList();
        await saveScenarioToDB(scenario);
        showToast('Scenario saved.');
      });

      document.getElementById('save-copy-btn').addEventListener('click', () => {
        if (!C.activeScenarioId) {
          showToast('No active scenario to copy.');
          return;
        }
        const copyName = C.activeScenarioName + ' (copy)';
        addScenarioToSession(collectJsonData(), C.lastRunResults,
          { timestamp: new Date().toISOString(), source: 'manual' }, copyName);
        showToast('Saved as "' + copyName + '".');
      });

      document.getElementById('scenario-breadcrumb').addEventListener('click', (e) => {
        const nameEl = e.target.closest('#scenario-breadcrumb-name');
        if (!nameEl || !C.activeScenarioId) return;

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'scenario-card-name-input';
        input.value = C.activeScenarioName;
        input.size = Math.max(C.activeScenarioName.length, 5);
        nameEl.replaceWith(input);
        input.focus();
        input.select();
        input.addEventListener('input', () => { input.size = Math.max(input.value.length, 5); });
        const finishEdit = () => {
          const newName = input.value.trim();
          const restored = document.createElement('span');
          restored.id = 'scenario-breadcrumb-name';
          restored.title = 'Click to rename';
          if (newName && newName !== C.activeScenarioName) {
            input.replaceWith(restored);
            renameScenario(C.activeScenarioId, newName);
          } else {
            restored.textContent = C.activeScenarioName;
            input.replaceWith(restored);
          }
        };
        input.addEventListener('blur', finishEdit);
        input.addEventListener('keydown', (e2) => {
          if (e2.key === 'Enter') { e2.preventDefault(); input.blur(); }
          if (e2.key === 'Escape') { input.value = C.activeScenarioName; input.blur(); }
        });
      });

      document.getElementById('tab-contents').addEventListener('click', (e) => {
        if (e.target.closest('.sub-sub-tab-button')) {
          setTimeout(updateBreadcrumb, 0);
        }
      });


      // Smart tooltip positioning (activeTooltip moved to utils.js)


      // Delegate tooltip events to document
      document.addEventListener('mouseenter', function(e) {
        if (e.target && e.target.classList && e.target.classList.contains('help-icon')) {
          showTooltip(e.target);
        }
      }, true);

      document.addEventListener('mouseleave', function(e) {
        if (e.target && e.target.classList && e.target.classList.contains('help-icon')) {
          hideTooltip();
        }
      }, true);


      // Main tab switching
      function switchMainTab(tabName) {
        mainTabButtons.forEach(btn => {
          const isActive = btn.dataset.tab === tabName;
          const isDisabled = btn.classList.contains('disabled');

          if (isActive && !isDisabled) {
            btn.classList.add('active');
          } else {
            btn.classList.remove('active');
          }
        });

        mainTabContents.forEach(content => {
          if (content.id === `main-tab-${tabName}`) {
            content.classList.add('active');
          } else {
            content.classList.remove('active');
          }
        });

        // Only show status bar on Inputs tab
        if (tabName === 'inputs') {
          if (statusBar.dataset.wasVisible === 'true') {
            statusBar.classList.add('visible');
          }
        } else {
          if (statusBar.classList.contains('visible')) {
            statusBar.dataset.wasVisible = 'true';
          }
          statusBar.classList.remove('visible');
        }

        updateBreadcrumb();
      }

      function updateTabStates() {
        const inputsBtn = document.querySelector('.main-tab-button[data-tab="inputs"]');
        const resultsBtn = document.querySelector('.main-tab-button[data-tab="results"]');
        if (C.activeScenarioId) {
          if (inputsBtn) inputsBtn.classList.remove('disabled');
          if (resultsBtn && C.latestValidResults) resultsBtn.classList.remove('disabled');
        } else {
          if (inputsBtn) inputsBtn.classList.add('disabled');
          if (resultsBtn) resultsBtn.classList.add('disabled');
        }
      }


      function showCalculating() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        statusBar.classList.remove('success');
        statusBar.classList.remove('error');
        statusBar.classList.add('visible');
        statusBar.dataset.wasVisible = 'true';
        statusBarIcon.textContent = '⏳';
        statusBarLabel.textContent = 'Calculating...';
        statusBarTimestamp.textContent = `Started ${timeStr}`;
        statusBarViewBtn.style.display = 'none';
        document.getElementById('status-bar-save-btn').style.display = 'none';
      }

      function markResultsAvailable(durationMs) {
        const durationSeconds = (durationMs / 1000).toFixed(2);
        const resultsButton = document.querySelector('.main-tab-button[data-tab="results"]');

        if (resultsButton) {
          resultsButton.classList.remove('disabled');
          resultsButton.classList.add('results-available');
        }
      }

      function hideStatusBar() {
        statusBar.classList.remove('visible');
        statusBar.classList.remove('success');
        statusBar.classList.remove('error');
        statusBar.dataset.wasVisible = 'false';
      }

      // Attach click handlers to main tabs
      mainTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          if (!btn.classList.contains('disabled')) {
            switchMainTab(btn.dataset.tab);
          }
        });
      });

      const DEFAULT_PORT = Number(apiBaseInput.dataset.defaultPort || "8000");


      function initialiseApiBase() {
        const derived = deriveDefaultApiBase(window.location.href, DEFAULT_PORT);
        apiBaseInput.value = derived;
      }

      function selectedMode() {
        const checked = Array.from(modeInputs).find((input) => input.checked);
        return checked ? checked.value : "simple";
      }

      function updateModeVisibility() {
        const mode = selectedMode();
        console.log('updateModeVisibility called, mode:', mode);
        console.log('Setting hidden properties...');
        simpleSection.hidden = mode !== "simple";
        bulkSection.hidden = mode !== "bulk";
        ctccSection.hidden = mode !== "ctcc";
        console.log('Hidden states - simple:', simpleSection.hidden, 'bulk:', bulkSection.hidden, 'ctcc:', ctccSection.hidden);

        // Update mode-specific visibility
        if (mode === "ctcc") {
          updateCtccInputVisibility();
        } else if (mode === "bulk") {
          updateBulkSourceVisibility();
        }
      }

      function updateCtccInputVisibility() {
        const inputMode = Array.from(ctccInputModeInputs).find((input) => input.checked)?.value ?? "json";

        if (inputMode === "json") {
          ctccJsonInputs.hidden = false;
          ctccYamlMessage.hidden = true;
          // Auto-load JSON data if not already loaded
          if (!C.ctccJsonData) {
            loadCtccJson();
          }
        } else {
          ctccJsonInputs.hidden = true;
          ctccYamlMessage.hidden = false;
        }
        syncFuelMixPresetBarVisibility();
      }

      function updateBulkSourceVisibility() {
        const bulkSource = Array.from(bulkSourceInputs).find((input) => input.checked)?.value ?? "server";
        bulkFileInput.hidden = bulkSource !== "file";
      }


      async function fetchFinalCombined(baseUrl) {
        const finalUrl = new URL("/api/final_combined", baseUrl).toString();
        const response = await fetch(finalUrl);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to load final_combined.json: ${response.status} ${response.statusText} ${errorText}`);
        }
        return response.json();
      }

      async function fetchTaxonomy(baseUrl) {
        const resp = await fetch(new URL("/api/taxonomy", baseUrl).toString());
        if (!resp.ok) throw new Error("Failed to load taxonomy: " + resp.status);
        return resp.json();
      }

      async function fetchInputMetadata(baseUrl) {
        const resp = await fetch(new URL("/api/input_metadata", baseUrl).toString());
        if (!resp.ok) throw new Error("Failed to load input_metadata: " + resp.status);
        return resp.json();
      }

      async function fetchFuelMixPresets(baseUrl) {
        const url = new URL("/api/fuel_mix_presets", baseUrl).toString();
        const response = await fetch(url);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to load fuel_mix_presets: ${response.status} ${response.statusText} ${errorText}`);
        }
        return response.json();
      }


      function switchTab(index) {
        const buttons = tabButtonsContainer.querySelectorAll('.tab-button');
        const contents = tabContentsContainer.querySelectorAll('.tab-content');

        buttons.forEach((btn, i) => {
          btn.classList.toggle('active', i === index);
        });

        contents.forEach((content, i) => {
          content.classList.toggle('active', i === index);
        });

        C.activeTabIndex = index;
        updateBreadcrumb();
      }

      // Expose closure-scoped functions for external modules
      window.autoCalculate = autoCalculate;
      window.switchMainTab = switchMainTab;
      window.switchTab = switchTab;
      window.collectJsonData = collectJsonData;
      window.markResultsAvailable = markResultsAvailable;
      window.updateTabStates = updateTabStates;
      window.showCalculating = showCalculating;
      window.hideStatusBar = hideStatusBar;
      window.fetchFinalCombined = fetchFinalCombined;
      window.fetchTaxonomy = fetchTaxonomy;
      window.fetchInputMetadata = fetchInputMetadata;
      window.fetchFuelMixPresets = fetchFuelMixPresets;

      function collectJsonData() {
        if (!C.ctccJsonData) return null;

        // Deep clone the original data to preserve nested structures
        const result = JSON.parse(JSON.stringify(C.ctccJsonData));

        // Helper function to set value at path
        function setValueAtPath(path, value) {
          const keys = path.split('.');
          let current = result;

          for (let i = 0; i < keys.length - 1; i++) {
            if (!current[keys[i]]) {
              current[keys[i]] = {};
            }
            current = current[keys[i]];
          }

          current[keys[keys.length - 1]] = value;
        }

        // Update with edited values from form inputs
        const inputs = tabContentsContainer.querySelectorAll('input');
        inputs.forEach(input => {
          const path = input.dataset.path;
          if (!path) return;

          let value;
          if (input.type === 'checkbox') {
            value = input.checked;
          } else if (input.type === 'number') {
            value = input.value === '' ? null : parseFloat(input.value);
            // Percent sliders display ×100; convert back to decimal for JSON
            if (value !== null && input.classList.contains('slider-pct')) {
              value = value / 100;
            }
          } else if (input.classList.contains('currency-input')) {
            value = parseCurrencyInput(input.value);
          } else if (input.classList.contains('percentage-input')) {
            value = parsePercentageInput(input.value);
          } else if (input.classList.contains('number-input')) {
            value = parseNumberInput(input.value);
          } else if (input.classList.contains('year-input')) {
            value = input.value === '' ? null : parseInt(input.value, 10);
          } else {
            value = input.value;
          }

          setValueAtPath(path, value);
        });

        // Update with edited values from select dropdowns
        const selects = tabContentsContainer.querySelectorAll('select');
        selects.forEach(select => {
          const path = select.dataset.path;
          if (!path) return;

          let value = select.value;
          const meta = C.inputMetadata
            ? C.inputMetadata.find(m => m.yaml_section + '.' + m.field_path === path)
            : null;
          if (meta && meta.input_type === 'dynamic_dropdown') {
            const parsed = parseInt(value, 10);
            value = value === '' ? null : (isNaN(parsed) ? value : parsed);
          } else if (meta && meta.validation && Array.isArray(meta.validation.options)
                     && meta.validation.options.some(opt => typeof opt === 'number')) {
            value = value === '' ? null : parseInt(value, 10);
          } else if (value === '') {
            value = null;
          }

          setValueAtPath(path, value);
        });

        return result;
      }


      // ===== Taxonomy-Driven Renderers (Phase 3) =====


      // ===== Taxonomy-Driven Input Form Renderer (Phase 4) =====

      C.INPUT_TAB_ORDER = ['project-technical', 'benefits', 'financial', 'capital-costs', 'operational', 'delay-costs', 'emissions', 'risk'];
      C.INPUT_TAB_LABELS = {
        'project-technical': 'Project Details', 'financial': 'Financial',
        'capital-costs': 'Capital Costs',
        'operational': 'Operational Costs', 'delay-costs': 'Delay Costs',
        'risk': 'Risk Profiles', 'emissions': 'Energy and Emissions', 'benefits': 'System Details',
      };
      C.SUB_TAB_LABELS = {
        'terrain-mix': 'Terrain Mix',
        'rights-of-way': 'Rights of Way',
        'conductor': 'Conductor',
        'structure': 'Structure',
        'converter': 'Converter',
        'base-mitigation': 'Base Mitigation',
        'credits': 'Habitat Credits',
        'technology': 'Technology',
        'conductor-details': 'Conductor Details',
        'structure-details': 'Structure Details',
        'converter-details': 'Converter Details',
        'timeline': 'Timeline',
        'routing': 'Routing',
        'operational-insurance': 'Operational Insurance',
        'maintenance-costs': 'Maintenance Costs',
        'vegetation-management': 'Vegetation Management',
        'conductor-maintenance': 'Conductor Maintenance',
        'structure-maintenance': 'Structure Maintenance',
        'converter-maintenance': 'Converter Maintenance',
        'energy-emissions-energy': 'Energy',
        'energy-emissions-emissions': 'Emissions',
        'environmental-mitigation': 'Environmental Mitigation',
        'energy-mix': 'Energy Mix',
        'energy-losses': 'Losses',
        'emission-intensities': 'Intensities',
        'emission-externality-costs': 'Externality Costs',
        'wildfire-risk': 'Wildfire Risk',
        'outage-risk': 'Outage Risk',
        'wf-severity': 'Severity',
        'wf-ignition-profile': 'Ignition Profile',
        'out-exposure': 'Exposure',
        'out-outage-profile': 'Outage Profile',
        'economic-details': 'Economic Details',
        'system-constraints': 'Constraints',
        'congestion': 'Congestion',
        'curtailment': 'Curtailment',
        'rates': 'Rates',
        'afudc': 'AFUDC',
      };


      // ============================================================
      // Tab guide banners — contextual onboarding
      // ============================================================


      // emissionsChartInstances defined near renderEmissionsImpactPanel


      document.addEventListener('ctcc-results-updated', (e) => {
        updateROWCostPanel(e.detail.results);
      });
      document.addEventListener('ctcc-calc-started', () => {
        const ind = document.getElementById('rcp-computing');
        if (ind) ind.style.display = '';
        const dInd = document.getElementById('dcp-computing');
        if (dInd) dInd.style.display = '';
        const eInd = document.getElementById('eip-computing');
        if (eInd) eInd.style.display = '';
        const emInd = document.getElementById('emip-computing');
        if (emInd) emInd.style.display = '';
      });


      document.addEventListener('ctcc-results-updated', (e) => {
        updateDelayCostPanel(e.detail.results);
        updateEnergyImpactPanel(e.detail.results);
        updateEmissionsImpactPanel(e.detail.results);
      });


      // ===== Capital Costs tab — Pattern 7 locked cost tables =====


      // ============================================================
      // Operational Costs — Maintenance tables + rebuild functions
      // ============================================================


      // ============================================================
      // Energy and Emissions — render functions
      // ============================================================


      // ============================================================
      // Risk Profiles — render functions
      // ============================================================


      // ============================================================
      // Financial — render functions
      // ============================================================


      // ============================================================
      // System Details — render functions
      // ============================================================


      // ===== BCR Tab Renderers =====


      form.addEventListener("submit", async (event) => {
        event.preventDefault();

        // Pre-run validation: category string (Fix 6)
        const catCheck = validateCategoryString();
        if (!catCheck.valid) {
          statusBar.classList.add('error');
          statusBar.classList.add('visible');
          statusBarIcon.textContent = '✗';
          statusBarLabel.textContent = 'Invalid configuration';
          statusBarTimestamp.textContent = catCheck.reason;
          return;
        }

        // Pre-run validation: AFUDC timing patterns (Fix 5)
        if (!validateCostTimingPatterns()) {
          statusBar.classList.add('error');
          statusBar.classList.add('visible');
          statusBarIcon.textContent = '✗';
          statusBarLabel.textContent = 'AFUDC timing invalid';
          statusBarTimestamp.textContent = 'during_delay + during_construction must equal 1.0 for AFUDC-eligible categories';
          return;
        }

        if (!C.routingValid) {
          showToast('Cannot run — terrain and zone miles don\'t match');
          return;
        }

        const startTime = performance.now();
        showCalculating();
        statusEl.textContent = "";
        statusEl.classList.remove("error");
        resultEl.textContent = "";

        try {
          const baseUrl = apiBaseInput.value.trim();
          const mode = selectedMode();
          let payload = { mode };
          let endpoint;

          if (mode === "simple") {
            payload.message = messageInput.value;
            payload.values = parseValues(valuesInput.value);
            endpoint = new URL("/api/process", baseUrl).toString();
          } else if (mode === "bulk") {
            const bulkSource = Array.from(
              document.querySelectorAll('input[name="bulk-source"]')
            ).find((input) => input.checked)?.value ?? "server";
            if (bulkSource === "file") {
              const fileInput = document.getElementById("bulk-file");
              const file = fileInput?.files?.[0];
              if (!file) {
                throw new Error("Choose a JSON file or switch back to server mode.");
              }
              payload.combinedData = await readFileAsJson(file);
            } else {
              payload.combinedData = await fetchFinalCombined(baseUrl);
            }
            endpoint = new URL("/api/process", baseUrl).toString();
          } else if (mode === "ctcc") {

            // Get CTCC configuration
            const inputMode = Array.from(
              document.querySelectorAll('input[name="ctcc-input-mode"]')
            ).find((input) => input.checked)?.value ?? "json";

            const scenarioId = C.activeScenarioId;

            // Build CTCC payload (calculator is JSON-out only; output_mode accepted but ignored server-side)
            payload = {
              mode: "calculate",
              input_mode: inputMode,
              output_mode: "json",
              scenario_id: scenarioId,
              combined_data: null
            };

            // If input mode is JSON, use the edited data or fetch from server
            if (inputMode === "json") {
              if (C.ctccJsonData && !tabsContainer.classList.contains('tabs-hidden')) {
                payload.combined_data = collectJsonData();
              } else {
                payload.combined_data = await fetchFinalCombined(baseUrl);
              }
            }

            endpoint = new URL("/api/ctcc/calculate", baseUrl).toString();
          }

          const _fAuthToken = await _getAuthToken();
          const _fHeaders = { "Content-Type": "application/json" };
          if (_fAuthToken) _fHeaders["Authorization"] = "Bearer " + _fAuthToken;
          const response = await fetch(endpoint, {
            method: "POST",
            headers: _fHeaders,
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`${response.status} ${response.statusText}: ${errorText}`);
          }

          const json = await response.json();

          if (json.mode === "bulk" && json.text) {
            resultEl.textContent = json.text;
          } else if (mode === "ctcc" && json.csv_files) {
            // CSV output mode - fetch and display CSV contents
            await displayCsvFiles(json, baseUrl);
          } else if (mode === "ctcc" && json.results) {
            renderCTCCResults(json.results);
            C.lastRunResults = json.results;
            C.latestValidResults = json.results;
            document.dispatchEvent(new CustomEvent('ctcc-results-ready'));
          } else {
            // Fallback to raw JSON display
            resultEl.textContent = JSON.stringify(json, null, 2);
          }

          // Mark results available (but don't switch tabs)
          const endTime = performance.now();
          const duration = endTime - startTime;
          markResultsAvailable(duration);
        } catch (error) {
          statusBar.classList.remove('success');
          statusBar.classList.add('error');
          statusBarIcon.textContent = '✗';
          statusBarLabel.textContent = 'Request failed';
          statusBarTimestamp.textContent = error.message;
          statusBarViewBtn.style.display = 'none';
          resultEl.textContent = error.message;
        }
      });

      C.unsavedChanges = false;
      form.addEventListener('input', () => {
          if (C.activeScenarioId) C.unsavedChanges = true;
      });
      window.addEventListener('beforeunload', (e) => {
          if (C.unsavedChanges) {
              e.preventDefault();
              e.returnValue = '';
          }
      });

      // Always-solving: auto-calculate on every input change
      form.addEventListener('input', () => autoCalculate());
      form.addEventListener('change', () => autoCalculate());

      // Initial calculation removed — gated on C.activeScenarioId (§13 Scenarios Tab)

      // =============================================
      // Conditional Field Visibility
      // =============================================

      // Set up event listeners for controlling fields after JSON loads


      // =============================================
      // Post-Render Functions
      // =============================================


      // Change 1: Update dynamic dropdowns (capacity MW) when AC/DC changes


      // createEnvironmentalSubTabs — retired, replaced by metadata-driven sub-tabs in renderInputsFromTaxonomy


      // cleanUpProjectOverviewHeaders() — absorbed into TAB_HIERARCHY engine


      console.log('Calling initialiseApiBase and updateModeVisibility...');
      initialiseApiBase();
      updateModeVisibility();
      console.log('Event listeners being attached to mode inputs:', modeInputs.length);
      modeInputs.forEach((input) => {
        input.addEventListener("change", updateModeVisibility);
      });
      ctccInputModeInputs.forEach((input) => {
        input.addEventListener("change", updateCtccInputVisibility);
      });
      bulkSourceInputs.forEach((input) => {
        input.addEventListener("change", updateBulkSourceVisibility);
      });

      // --- App entry (waits for auth check to resolve) ---
      if (window._authReady) {
        window._authReady.then(async function(auth) {
          if (!auth) return;
          var profile = auth.profile;
          var session = auth.session;

          window.CTCC.userProfile = profile;
          window.CTCC.currentUserId = session.user.id;
          document.querySelectorAll('.ctcc-user-display').forEach(function(el) {
            el.textContent = profile.username || '';
          });

          await loadScenariosFromDB();
          if (typeof renderScenarioList === 'function') renderScenarioList();

          _sb.from('ref_snapshot').select('id').order('created_at', { ascending: false }).limit(1).single()
            .then(function(res) { if (res.data) loadSnapshot(res.data.id); });

          if (typeof initAssistant === 'function') initAssistant();

          var params = new URLSearchParams(window.location.search);
          if (params.get('new') === '1') {
            if (typeof showWizard === 'function') showWizard();
          } else if (params.get('scenario')) {
            var scenarioId = params.get('scenario');
            var found = window.CTCC.sessionScenarios.find(function(s) { return s.id === scenarioId; });
            if (found && typeof setActiveScenario === 'function') setActiveScenario(found.id);
          } else if (window.CTCC.sessionScenarios.length > 0) {
            var userScenarios = window.CTCC.sessionScenarios.filter(function(s) { return s.user_id === session.user.id; });
            var latest = userScenarios.length > 0 ? userScenarios[0] : window.CTCC.sessionScenarios[0];
            if (typeof setActiveScenario === 'function') setActiveScenario(latest.id);
          }
        });
      }

      }); // End DOMContentLoaded

})();

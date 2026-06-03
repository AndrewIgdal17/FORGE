// CTCC Scenario Manager
// Extracted from index.html — loaded via <script src="/static/scenarios.js">
// Forward references: autoCalculate, switchMainTab, switchTab, collectJsonData,
// renderJsonInputs, renderCTCCResults are exposed as window globals from inline script.

(function() {
'use strict';

  const C = window.CTCC;

const RESULTS_EXPORT_FIELDS = [
  { key: 'capacity_mw', path: 'technical_parameters.capacity_mw' },
  { key: 'line_length_miles', path: 'technical_parameters.line_length_miles' },
  { key: 'project_lifetime_years', path: 'technical_parameters.project_lifetime_years' },
  { key: 'delay_years', path: 'technical_parameters.delay_years' },
  { key: 'build_cost_pv', path: 'costs.build.total_pv' },
  { key: 'row_capital_pv', path: 'costs.row.row_capital_pv' },
  { key: 'row_rent_pv', path: 'costs.row.row_rent_pv' },
  { key: 'env_mitigation_pv', path: 'costs.environmental.total_pv' },
  { key: 'total_capital_pv', path: 'summary.total_capital_pv' },
  { key: 'insurance_pv', path: 'costs.insurance.pv_total' },
  { key: 'oandm_pv', path: 'costs.oandm.total_pv' },
  { key: 'total_operational_pv', path: 'summary.total_operational_pv' },
  { key: 'wildfire_pv', path: 'costs.wildfire.pv_cost' },
  { key: 'outage_pv', path: 'costs.outage.pv_cost' },
  { key: 'total_risk_pv', path: 'summary.total_risk_pv' },
  { key: 'delay_pv', path: 'costs.delay.total_pv' },
  { key: 'line_loss_pv', path: 'costs.line_loss.total_pv' },
  { key: 'emissions_pv', path: 'costs.emissions.total_pv' },
  { key: 'fac_emissions_project_pv', path: 'bcr.fac_emissions_project_pv' },
  { key: 'displacement_avoided_cost_pv', path: 'bcr.displacement_avoided_cost_pv' },
  { key: 'total_energy_emissions_pv', path: 'summary.total_energy_emissions_pv' },
  { key: 'grand_total_cost_pv', path: 'summary.total_costs_pv' },
  { key: 'hard_costs_pv', path: 'bcr.hard_costs_pv' },
  { key: 'soft_costs_pv', path: 'bcr.soft_costs_pv' },
  { key: 'emissions_costs_pv', path: 'bcr.emissions_costs_pv' },
  { key: 'revenue_pv', path: 'bcr.revenue_pv' },
  { key: 'bcr_system', path: 'bcr.bcr_system' },
  { key: 'bcr_capital', path: 'bcr.bcr_capital' },
  { key: 'bcr_utility', path: 'bcr.bcr_utility' },
  { key: 'bcr_ratepayer', path: 'bcr.bcr_ratepayer' },
  { key: 'net_benefit_pv', path: 'bcr.net_benefit_pv' },
  { key: 'net_benefit_utility_pv', path: 'bcr.net_benefit_utility_pv' },
  { key: 'net_benefit_ratepayer_pv', path: 'bcr.net_benefit_ratepayer_pv' },
];

function generateScenarioName(baseName) {
  const existingNames = C.sessionScenarios.map(s => s.customName);
  if (!existingNames.includes(baseName)) return baseName;
  let counter = 2;
  while (existingNames.includes(`${baseName} (${counter})`)) counter++;
  return `${baseName} (${counter})`;
}

function updateScenarioBadge() {
  // No-op: badge removed by design
}

function addScenarioToSession(inputs, results, metadata, customName) {
  const scenario = {
    version: '1.0',
    id: crypto.randomUUID(),
    customName: customName || generateScenarioName('Scenario'),
    inputs: inputs ? JSON.parse(JSON.stringify(inputs)) : null,
    results: results ? JSON.parse(JSON.stringify(results)) : null,
    metadata: metadata || { timestamp: new Date().toISOString(), source: 'manual' }
  };
  C.sessionScenarios.push(scenario);
  renderScenarioList();
  updateScenarioBadge();
  return scenario;
}

function setActiveScenario(scenario) {
  C.activeScenarioId = scenario.id;
  C.activeScenarioName = scenario.customName;
  updateScenarioBreadcrumb();
  updateTabStates();
  if (scenario.inputs) {
    renderJsonInputs(scenario.inputs);
  }
  if (scenario.results) {
    renderCTCCResults(scenario.results);
    C.lastRunResults = JSON.parse(JSON.stringify(scenario.results));
    markResultsAvailable(0);
  }
  renderScenarioList();
  autoCalculate();
}

function updateBreadcrumb() {
  const pill = document.getElementById('scenario-breadcrumb-pill');
  const crumb = document.getElementById('scenario-breadcrumb');
  if (!pill || !crumb) return;

  const segments = [];

  if (!C.activeScenarioId) {
    crumb.style.display = 'none';
    return;
  }

  segments.push({ label: 'Scenarios', action: () => switchMainTab('scenarios') });
  segments.push({ label: C.activeScenarioName, editable: true });

  const activeL1 = document.querySelector('.main-tab-button.active')?.dataset.tab;

  if (activeL1 === 'inputs') {
    segments.push({ label: 'Inputs', action: () => switchMainTab('inputs') });
    const activeL2Btn = document.querySelector('#tab-buttons .tab-button.active');
    if (activeL2Btn) {
      const tabId = C.INPUT_TAB_ORDER[C.activeTabIndex];
      const tabLabel = C.INPUT_TAB_LABELS[tabId] || tabId;
      segments.push({ label: tabLabel, action: () => activeL2Btn.click() });
      const activeL2Content = document.querySelector('#tab-contents .tab-content.active');
      if (activeL2Content) {
        const l3Btn = activeL2Content.querySelector(':scope > .sub-tabs .sub-tab-button.active');
        if (l3Btn) {
          segments.push({ label: btnLabel(l3Btn), action: () => l3Btn.click() });
          let visibleL3Content = null;
          activeL2Content.querySelectorAll(':scope > .sub-tab-content').forEach(c => {
            if (c.style.display !== 'none') visibleL3Content = c;
          });
          if (!visibleL3Content && tabId === 'project-technical') {
            const routingPanel = activeL2Content.querySelector('.routing-panel');
            if (routingPanel) visibleL3Content = routingPanel;
          }
          if (visibleL3Content) {
            const l4Btn = visibleL3Content.querySelector('.sub-sub-tabs .sub-sub-tab-button.active');
            if (l4Btn) {
              segments.push({ label: btnLabel(l4Btn) });
            }
          }
        }
      }
    }
  } else if (activeL1 === 'results') {
    segments.push({ label: 'Results', action: () => switchMainTab('results') });
    const activeResultBtn = document.querySelector('.results-tabs-container .tab-button.active');
    if (activeResultBtn) {
      segments.push({ label: btnLabel(activeResultBtn) });
    }
  } else if (activeL1 === 'scenarios') {
    const activeScnBtn = document.querySelector('#scenario-subtabs .tab-button.active');
    if (activeScnBtn && activeScnBtn.dataset.scenarioTab !== 'scenario-comparison') {
      segments.push({ label: btnLabel(activeScnBtn) });
    }
  }

  pill.innerHTML = '';
  segments.forEach((seg, i) => {
    if (i > 0) {
      const sep = document.createElement('span');
      sep.className = 'breadcrumb-separator';
      sep.textContent = ' / ';
      pill.appendChild(sep);
    }
    const span = document.createElement('span');
    span.textContent = seg.label;
    if (seg.editable) {
      span.id = 'scenario-breadcrumb-name';
      span.title = 'Click to rename';
    } else if (seg.action && i < segments.length - 1) {
      span.style.cursor = 'pointer';
      span.addEventListener('click', (e) => { e.stopPropagation(); seg.action(); });
      span.addEventListener('mouseenter', () => { span.style.textDecoration = 'underline'; });
      span.addEventListener('mouseleave', () => { span.style.textDecoration = ''; });
    }
    pill.appendChild(span);
  });

  crumb.style.display = '';
}

function updateScenarioBreadcrumb() { updateBreadcrumb(); }


function createNewScenario(name) {
  const trimmed = name.trim();
  if (!trimmed) return;
  const scenario = addScenarioToSession(null, null,
    { timestamp: new Date().toISOString(), source: 'manual' },
    trimmed
  );
  C.activeScenarioId = scenario.id;
  C.activeScenarioName = trimmed;
  updateScenarioBreadcrumb();
  updateTabStates();
  switchMainTab('inputs');
  switchTab(0);
  autoCalculate();
}

function removeScenarioFromSession(id) {
  C.sessionScenarios = C.sessionScenarios.filter(s => s.id !== id);
  C.comparisonScenarioIds.delete(id);
  if (C.comparisonBaselineId === id) C.comparisonBaselineId = null;
  renderScenarioList();
  updateScenarioBadge();
  renderComparisonTable();
}

function renameScenario(id, newName) {
  const scenario = C.sessionScenarios.find(s => s.id === id);
  if (scenario && newName.trim()) {
    scenario.customName = newName.trim();
    if (id === C.activeScenarioId) {
      C.activeScenarioName = scenario.customName;
      updateScenarioBreadcrumb();
    }
    renderScenarioList();
  }
}

function loadScenarioIntoUI(scenario) {
  setActiveScenario(scenario);
}

function getScenarioParams(scenario) {
  const parts = [];
  if (scenario.results?.technical_parameters) {
    const tp = scenario.results.technical_parameters;
    if (tp.project_name) parts.push(tp.project_name);
    if (tp.capacity_mw) parts.push(tp.capacity_mw + ' MW');
    if (tp.ac_dc) parts.push(tp.ac_dc);
    if (tp.construction_type) parts.push(tp.construction_type);
    if (tp.line_length_miles) parts.push(tp.line_length_miles + ' mi');
  } else if (scenario.inputs) {
    const proj = scenario.inputs['01_project_technical_details']?.project;
    if (proj) {
      if (proj.name) parts.push(proj.name);
      if (proj.capacity_mw) parts.push(proj.capacity_mw + ' MW');
      if (proj.ac_dc) parts.push(proj.ac_dc);
      if (proj.construction_type) parts.push(proj.construction_type);
    }
    const terrain = scenario.inputs['02_project_physical_details']?.terrain?.terrain_miles;
    if (terrain) {
      const totalMiles = Object.values(terrain).reduce((sum, v) => sum + (Number(v) || 0), 0);
      if (totalMiles > 0) parts.push(totalMiles + ' mi');
    }
  }
  return parts.join(' | ') || 'No parameters available';
}

function renderScenarioList() {
  const container = document.getElementById('scenario-list');
  if (!container) return;
  container.innerHTML = '';

  if (C.sessionScenarios.length === 0) {
    container.innerHTML = '<div class="scenario-empty">No scenarios yet.</div>';
    renderComparisonTable();
    return;
  }

  const table = document.createElement('table');
  table.className = 'scenario-list-table';
  table.style.cssText = 'width: 100%; border-collapse: collapse;';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  const thCmp = document.createElement('th');
  thCmp.className = 'scenario-compare-col';
  thCmp.title = 'Include in comparison table';
  const selectAllCmp = document.createElement('input');
  selectAllCmp.type = 'checkbox';
  selectAllCmp.id = 'scenario-compare-select-all';
  selectAllCmp.setAttribute('aria-label', 'Select all scenarios for comparison');
  selectAllCmp.title = 'Select all scenarios for comparison';
  selectAllCmp.addEventListener('click', (e) => e.stopPropagation());
  selectAllCmp.addEventListener('change', () => {
    if (selectAllCmp.checked) {
      C.sessionScenarios.forEach(s => C.comparisonScenarioIds.add(s.id));
    } else {
      C.comparisonScenarioIds.clear();
      C.comparisonBaselineId = null;
    }
    renderScenarioList();
  });
  thCmp.appendChild(selectAllCmp);
  syncComparisonSelectAllCheckbox(selectAllCmp);
  const thBase = document.createElement('th');
  thBase.className = 'scenario-base-col';
  thBase.innerHTML = 'Set as<br>baseline';
  thBase.style.textAlign = 'center';
  thBase.style.lineHeight = '1.1';
  thBase.title = 'Set as baseline for Δ comparison';
  const thScenario = document.createElement('th');
  thScenario.textContent = 'Scenario';
  const thActions = document.createElement('th');
  thActions.textContent = '';
  const thFill = document.createElement('th');
  thFill.style.width = '100%';
  const thDrag = document.createElement('th');
  thDrag.style.width = '20px';
  headRow.appendChild(thCmp);
  headRow.appendChild(thBase);
  headRow.appendChild(thScenario);
  headRow.appendChild(thActions);
  headRow.appendChild(thDrag);
  headRow.appendChild(thFill);
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  table.appendChild(tbody);

  C.sessionScenarios.forEach(scenario => {
    const isActive = scenario.id === C.activeScenarioId;
    const card = document.createElement('tr');
    card.className = 'scenario-card' + (isActive ? ' scenario-card-active' : '');
    card.dataset.scenarioId = scenario.id;

    // Row click toggles checkbox (except buttons, checkbox, radio, name editing)
    card.addEventListener('click', (e) => {
      if (e.target.closest('.scenario-card-actions') || e.target.closest('.scenario-drag-handle') || e.target.closest('.scenario-card-name') || e.target.closest('.scenario-card-name-input') || e.target.type === 'checkbox' || e.target.type === 'radio' || e.target.closest('.scenario-base-cell')) return;
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event('change'));
    });

    // Checkbox cell
    const checkTd = document.createElement('td');
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'scenario-card-checkbox';
    checkbox.checked = C.comparisonScenarioIds.has(scenario.id);
    checkbox.title = 'Select for comparison';
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        C.comparisonScenarioIds.add(scenario.id);
      } else {
        C.comparisonScenarioIds.delete(scenario.id);
        if (C.comparisonBaselineId === scenario.id) C.comparisonBaselineId = null;
      }
      renderScenarioList();
    });
    checkTd.appendChild(checkbox);
    card.appendChild(checkTd);

    // Baseline radio cell
    const baseTd = document.createElement('td');
    baseTd.className = 'scenario-base-cell';
    const baseRadio = document.createElement('input');
    baseRadio.type = 'radio';
    baseRadio.name = 'comparison-baseline';
    baseRadio.checked = C.comparisonBaselineId === scenario.id;
    baseRadio.title = 'Set as comparison baseline';
    baseRadio.setAttribute('aria-label', 'Set as comparison baseline');
    baseRadio.addEventListener('click', (e) => e.stopPropagation());
    baseRadio.addEventListener('change', () => {
      if (baseRadio.checked) {
        C.comparisonBaselineId = scenario.id;
        C.comparisonScenarioIds.add(scenario.id);
        renderScenarioList();
      }
    });
    baseTd.appendChild(baseRadio);
    card.appendChild(baseTd);

    // Info cell
    const infoTd = document.createElement('td');
    infoTd.className = 'scenario-card-info';

    // Editable name
    const nameSpan = document.createElement('span');
    nameSpan.className = 'scenario-card-name';
    nameSpan.textContent = scenario.customName;
    nameSpan.title = 'Click to rename';
    nameSpan.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'scenario-card-name-input';
      input.value = scenario.customName;
      input.size = Math.max(scenario.customName.length, 5);
      nameSpan.replaceWith(input);
      input.focus();
      input.select();
      input.addEventListener('input', () => { input.size = Math.max(input.value.length, 5); });
      const finishEdit = () => {
        const newName = input.value.trim();
        if (newName && newName !== scenario.customName) {
          renameScenario(scenario.id, newName);
        } else {
          renderScenarioList();
        }
      };
      input.addEventListener('blur', finishEdit);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
        if (e.key === 'Escape') { input.value = scenario.customName; input.blur(); }
      });
    });
    infoTd.appendChild(nameSpan);

    // Params
    const params = document.createElement('span');
    params.className = 'scenario-card-params';
    params.textContent = getScenarioParams(scenario);
    infoTd.appendChild(params);

    // Meta
    const meta = document.createElement('span');
    meta.className = 'scenario-card-meta';
    const sourceLabel = scenario.metadata?.source === 'run' ? 'Calculated' :
                        scenario.metadata?.source === 'upload-ctcc' ? 'Uploaded (.ctcc)' :
                        scenario.metadata?.source === 'upload-csv' ? 'Uploaded (.csv)' : 'Saved';
    const ts = scenario.metadata?.timestamp ? formatTimestamp(scenario.metadata.timestamp) : '';
    meta.textContent = sourceLabel + (ts ? ' ' + ts : '');
    infoTd.appendChild(meta);

    card.appendChild(infoTd);

    // Actions cell
    const actionsTd = document.createElement('td');
    actionsTd.className = 'scenario-actions-cell';
    const actions = document.createElement('div');
    actions.className = 'scenario-card-actions';

    if (isActive) {
      const badge = document.createElement('span');
      badge.className = 'active-badge';
      badge.textContent = 'Active';
      actions.appendChild(badge);
    } else {
      const setActiveBtn = document.createElement('button');
      setActiveBtn.type = 'button';
      setActiveBtn.className = 'load-btn';
      setActiveBtn.textContent = 'Set Active';
      setActiveBtn.addEventListener('click', () => setActiveScenario(scenario));
      actions.appendChild(setActiveBtn);
    }

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.textContent = 'Remove';
    removeBtn.addEventListener('click', () => {
      removeScenarioFromSession(scenario.id);
    });
    actions.appendChild(removeBtn);

    const saveHereBtn = document.createElement('button');
    saveHereBtn.type = 'button';
    saveHereBtn.textContent = 'Save here';
    saveHereBtn.dataset.tooltip = 'Overwrite with current inputs and results';
    saveHereBtn.addEventListener('click', () => {
      const currentInputs = collectJsonData();
      scenario.inputs = currentInputs;
      scenario.results = C.lastRunResults;
      scenario.metadata.timestamp = new Date().toISOString();
      scenario.metadata.source = 'manual';
      renderScenarioList();
    });
    actions.appendChild(saveHereBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'delete-btn';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', () => {
      showModal('Delete Scenario', `Delete "${scenario.customName}"?`, () => {
        removeScenarioFromSession(scenario.id);
      });
    });
    actions.appendChild(deleteBtn);

    actionsTd.appendChild(actions);
    card.appendChild(actionsTd);

    // Drag handle cell
    const dragTd = document.createElement('td');
    dragTd.className = 'scenario-drag-cell';
    const dragHandle = document.createElement('span');
    dragHandle.className = 'scenario-drag-handle';
    dragHandle.title = 'Drag to reorder';
    dragHandle.draggable = true;
    dragTd.appendChild(dragHandle);
    card.appendChild(dragTd);

    // Filler cell
    const fillerTd = document.createElement('td');
    fillerTd.style.cssText = 'width: 100%;';
    card.appendChild(fillerTd);

    tbody.appendChild(card);
  });

  // Row drag-and-drop reordering
  (function initRowDrag() {
    let dragRowIdx = null;
    let dropRowIdx = null;

    function clearRowDropIndicators() {
      tbody.querySelectorAll('.scenario-drop-above, .scenario-drop-below').forEach(el => {
        el.classList.remove('scenario-drop-above', 'scenario-drop-below');
      });
    }

    const rows = tbody.querySelectorAll('tr.scenario-card');
    rows.forEach((row, rowIdx) => {
      const handle = row.querySelector('.scenario-drag-handle');
      if (!handle) return;

      handle.addEventListener('dragstart', function(e) {
        e.stopPropagation();
        dragRowIdx = rowIdx;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', '' + rowIdx);
        const ghost = document.createElement('div');
        ghost.textContent = C.sessionScenarios[rowIdx].customName;
        ghost.style.cssText = 'position:absolute;top:-9999px;padding:4px 10px;background:rgba(0,0,0,0.08);border:1px solid rgba(0,0,0,0.2);border-radius:4px;font-size:0.8rem;font-weight:600;color:rgba(0,0,0,0.5);white-space:nowrap;';
        document.body.appendChild(ghost);
        e.dataTransfer.setDragImage(ghost, ghost.offsetWidth / 2, ghost.offsetHeight / 2);
        requestAnimationFrame(() => document.body.removeChild(ghost));
        setTimeout(() => row.classList.add('scenario-row-dragging'), 0);
      });

      handle.addEventListener('dragend', function() {
        row.classList.remove('scenario-row-dragging');
        clearRowDropIndicators();
        if (dragRowIdx !== null && dropRowIdx !== null && dragRowIdx !== dropRowIdx) {
          const moved = C.sessionScenarios.splice(dragRowIdx, 1)[0];
          const insertAt = dropRowIdx > dragRowIdx ? dropRowIdx - 1 : dropRowIdx;
          C.sessionScenarios.splice(insertAt, 0, moved);
          renderScenarioList();
        }
        dragRowIdx = null;
        dropRowIdx = null;
      });

      row.addEventListener('dragover', function(e) {
        if (dragRowIdx === null) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const targetIdx = rowIdx;
        if (targetIdx === dragRowIdx) { clearRowDropIndicators(); dropRowIdx = null; return; }
        clearRowDropIndicators();
        const rect = row.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (e.clientY < midY) {
          dropRowIdx = targetIdx;
          row.classList.add('scenario-drop-above');
        } else {
          dropRowIdx = targetIdx + 1;
          row.classList.add('scenario-drop-below');
        }
      });

      row.addEventListener('drop', function(e) {
        e.preventDefault();
      });
    });
  })();

  container.appendChild(table);

  renderComparisonTable();
}

function showSaveDialog() {
  const overlay = document.getElementById('save-overlay');
  const nameInput = document.getElementById('save-memory-name');
  nameInput.value = C.activeScenarioName || generateScenarioName('Scenario');
  // Reset selection
  document.querySelectorAll('.save-dialog .save-option').forEach(o => o.classList.remove('selected'));
  document.getElementById('save-opt-memory').classList.add('selected');
  // Update status indicators
  const notCalcIndicator = document.getElementById('save-status-indicator');
  const savedIndicator = document.getElementById('save-saved-indicator');

  if (!C.latestValidResults) {
    notCalcIndicator.textContent = 'Calculating initial results\u2026';
    notCalcIndicator.style.color = '#b00020';
  } else {
    notCalcIndicator.textContent = '';
  }
  savedIndicator.textContent = '';
  overlay.classList.add('visible');
}

function hideSaveDialog() {
  document.getElementById('save-overlay').classList.remove('visible');
}

function exportAsCtcc(scenario) {
  const data = {
    version: '1.0',
    customName: scenario.customName,
    inputs: scenario.inputs,
    results: scenario.results,
    metadata: scenario.metadata
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (scenario.customName || 'scenario').replace(/[^a-zA-Z0-9_-]/g, '_') + '.ctcc';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportAsCsv(scenario) {
  let csv = '';
  // METADATA
  csv += '[METADATA]\n';
  csv += 'version,' + (scenario.version || '1.0') + '\n';
  csv += 'customName,' + csvEscape(scenario.customName || '') + '\n';
  csv += 'scenario_id,' + csvEscape(scenario.metadata?.scenario_id || '') + '\n';
  csv += 'timestamp,' + (scenario.metadata?.timestamp || new Date().toISOString()) + '\n';
  csv += '\n';

  // INPUTS
  if (scenario.inputs) {
    csv += '[INPUTS]\n';
    csv += 'section,key,value\n';
    for (const sectionKey of Object.keys(scenario.inputs)) {
      const flat = flattenObject(scenario.inputs[sectionKey], sectionKey);
      for (const row of flat) {
        const lastDot = row.path.lastIndexOf('.');
        const section = row.path.substring(0, lastDot);
        const key = row.path.substring(lastDot + 1);
        csv += csvEscape(section) + ',' + csvEscape(key) + ',' + csvEscape(String(row.value ?? '')) + '\n';
      }
    }
    csv += '\n';
  }

  // RESULTS (full recursive export)
  if (scenario.results) {
    csv += '[RESULTS]\n';
    csv += 'field,value\n';
    const flatResults = flattenObject(scenario.results, '');
    for (const row of flatResults) {
      csv += csvEscape(row.path) + ',' + csvEscape(String(row.value ?? '')) + '\n';
    }
  }

  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (scenario.customName || 'scenario').replace(/[^a-zA-Z0-9_-]/g, '_') + '.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function validateCtccFile(data) {
  const errors = [];
  if (!data || typeof data !== 'object') errors.push('Invalid JSON structure');
  if (!data.version) errors.push('Missing version field');
  if (!data.inputs || typeof data.inputs !== 'object') errors.push('Missing or invalid inputs field');
  else if (!data.inputs['01_project_technical_details']) errors.push('Missing 01_project_technical_details in inputs');
  if (data.results && typeof data.results !== 'object') errors.push('Results field must be an object');
  return { valid: errors.length === 0, errors };
}

function loadCtccFile(text, fileName) {
  try {
    const data = JSON.parse(text);
    const validation = validateCtccFile(data);
    if (!validation.valid) {
      alert('Invalid .ctcc file:\n' + validation.errors.join('\n'));
      return;
    }
    // Unwrap double-nested results from old .ctcc files (rerun_paper_scenarios wrote full API envelope)
    if (data.results && data.results.results && data.results.results.bcr) {
      data.results = data.results.results;
    }
    const name = data.customName || fileName.replace('.ctcc', '');
    addScenarioToSession(data.inputs, data.results || null,
      { timestamp: data.metadata?.timestamp || new Date().toISOString(),
        scenario_id: data.metadata?.scenario_id || '',
        source: 'upload-ctcc' },
      generateScenarioName(name));
  } catch (e) {
    alert('Failed to parse .ctcc file: ' + e.message);
  }
}

function loadCsvFile(text, fileName) {
  try {
    const sections = {};
    let currentSection = null;
    const lines = text.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.match(/^\[([A-Z]+)\]$/)) {
        currentSection = trimmed.match(/^\[([A-Z]+)\]$/)[1];
        sections[currentSection] = [];
      } else if (currentSection && trimmed) {
        sections[currentSection].push(trimmed);
      }
    }

    if (!sections.METADATA) {
      alert('Invalid CSV: missing [METADATA] section');
      return;
    }

    // Parse metadata
    const metadata = {};
    for (const line of sections.METADATA) {
      const idx = line.indexOf(',');
      if (idx > 0) {
        metadata[line.substring(0, idx)] = line.substring(idx + 1);
      }
    }

    // Parse inputs
    let inputs = null;
    if (sections.INPUTS && sections.INPUTS.length > 1) {
      // Skip header row
      inputs = C.ctccJsonData ? JSON.parse(JSON.stringify(C.ctccJsonData)) : {};
      for (let i = 1; i < sections.INPUTS.length; i++) {
        const parts = parseCsvLine(sections.INPUTS[i]);
        if (parts.length >= 3) {
          const fullPath = parts[0] + '.' + parts[1];
          let val = parts[2];
          // Try to parse numeric values
          if (val !== '' && !isNaN(Number(val))) val = Number(val);
          else if (val === 'true') val = true;
          else if (val === 'false') val = false;
          setValueAtPath(inputs, fullPath, val);
        }
      }
    }

    // Parse results
    let results = null;
    if (sections.RESULTS && sections.RESULTS.length > 1) {
      results = {};
      for (let i = 1; i < sections.RESULTS.length; i++) {
        const parts = parseCsvLine(sections.RESULTS[i]);
        if (parts.length >= 2) {
          const field = RESULTS_EXPORT_FIELDS.find(f => f.key === parts[0]);
          if (field) {
            let val = parts[1];
            if (val !== '' && !isNaN(Number(val))) val = Number(val);
            setValueAtPath(results, field.path, val);
          }
        }
      }
    }

    const name = metadata.customName || fileName.replace('.csv', '');
    addScenarioToSession(inputs, results,
      { timestamp: metadata.timestamp || new Date().toISOString(),
        scenario_id: metadata.scenario_id || '',
        source: 'upload-csv' },
      generateScenarioName(name));
  } catch (e) {
    alert('Failed to parse CSV file: ' + e.message);
  }
}

async function loadCtccJson() {
  try {
    const baseUrl = document.getElementById('api-base').value.trim();
    // Ensure C.taxonomy + input metadata are loaded before rendering
    if (!C.taxonomy || !C.inputMetadata) {
      try {
        const [taxData, metaData] = await Promise.all([
          C.taxonomy ? Promise.resolve(C.taxonomy) : fetchTaxonomy(baseUrl),
          C.inputMetadata ? Promise.resolve(C.inputMetadata) : fetchInputMetadata(baseUrl),
          fetchRowWidths(baseUrl),
          fetchBuildCosts(baseUrl),
          fetchCircuitDetails(baseUrl),
          fetchStructureDetails(baseUrl),
          fetchConverterDetails(baseUrl),
          fetchConductorOm(baseUrl),
          fetchVegetationManagement(baseUrl),
        ]);
        if (!C.taxonomy) {
          C.taxonomy = taxData;
          C.taxonomyById = {};
          C.taxonomyBySide = {};
          C.taxonomyByBucket = {};
          (taxData.items || []).forEach(item => {
            C.taxonomyById[item.id] = item;
            (C.taxonomyBySide[item.side] ??= []).push(item);
            (C.taxonomyByBucket[item.bucket] ??= []).push(item);
          });
        }
        if (!C.inputMetadata) C.inputMetadata = metaData;
      } catch (err) {
        console.warn('Taxonomy/metadata pre-load failed, using legacy renderer:', err);
      }
    }
    const data = await fetchFinalCombined(baseUrl);
    renderJsonInputs(data);
  } catch (error) {
    const _ls = document.getElementById('load-status');
    if (_ls) { _ls.textContent = '✗ ' + error.message; _ls.style.color = '#b00020'; }
  }
}

async function displayCsvFiles(apiResponse, baseUrl) {
  try {
    const csvFiles = apiResponse.csv_files || [];
    const outputDir = apiResponse.output_dir || '../outputs';

    if (csvFiles.length === 0) {
      document.getElementById('result').textContent = "No CSV files generated.";
      document.getElementById('status').textContent = "Success (no CSV files)";
      return;
    }

    // Create HTML structure to display CSV files
    let html = '<div style="font-family: monospace; white-space: pre-wrap;">';
    html += `<h3>Generated ${csvFiles.length} CSV file(s):</h3>`;

    // Add "Download All" button
    html += `<div style="margin-bottom: 20px;">`;
    html += `<button onclick="downloadAllCsvFiles()" style="padding: 10px 20px; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">Download All CSV Files</button>`;
    html += `</div>\n\n`;

    // Fetch and display each CSV file
    for (const csvFile of csvFiles) {
      try {
        // Construct URL to fetch CSV from server
        const csvUrl = new URL(`/api/outputs/${csvFile}`, baseUrl).toString();
        const response = await fetch(csvUrl);

        if (response.ok) {
          const csvContent = await response.text();
          html += `<div style="margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 4px;">`;
          html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">`;
          html += `<h4 style="margin: 0; color: #0066cc;">${csvFile}</h4>`;
          html += `<button onclick="downloadCsvFile('${csvFile}', '${csvUrl}')" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">Download</button>`;
          html += `</div>`;
          html += `<pre style="overflow-x: auto; background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 400px;">${csvContent}</pre>`;
          html += `</div>`;
        } else {
          html += `<div style="margin-bottom: 20px;">`;
          html += `<h4 style="color: #b00020;">${csvFile}</h4>`;
          html += `<p>Could not fetch file (${response.status})</p>`;
          html += `</div>`;
        }
      } catch (error) {
        html += `<div style="margin-bottom: 20px;">`;
        html += `<h4 style="color: #b00020;">${csvFile}</h4>`;
        html += `<p>Error: ${error.message}</p>`;
        html += `</div>`;
      }
    }

    html += '</div>';
    document.getElementById('result').innerHTML = html;
    document.getElementById('status').textContent = `Success - ${csvFiles.length} CSV file(s) displayed`;
  } catch (error) {
    document.getElementById('result').textContent = `Error displaying CSV files: ${error.message}`;
    document.getElementById('status').textContent = "Error";
  }
}

function downloadCsvFile(filename, url) {
  // Add download=true parameter to force download
  const downloadUrl = url.includes('?') ? `${url}&download=true` : `${url}?download=true`;

  // Create a temporary link element and trigger download
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function downloadAllCsvFiles() {
  // Get all download buttons
  const buttons = document.getElementById('result').querySelectorAll('button[onclick^="downloadCsvFile"]');

  if (buttons.length === 0) {
    alert('No CSV files to download');
    return;
  }

  // Extract filename and URL from each button's onclick attribute
  buttons.forEach((button, index) => {
    setTimeout(() => {
      // Parse the onclick attribute to get filename and URL
      const onclickAttr = button.getAttribute('onclick');
      const match = onclickAttr.match(/downloadCsvFile\('([^']+)',\s*'([^']+)'\)/);
      if (match) {
        const filename = match[1];
        const url = match[2];
        downloadCsvFile(filename, url);
      }
    }, index * 200); // Stagger downloads by 200ms to avoid browser blocking
  });
}



  // Public API
  window.generateScenarioName = generateScenarioName;
  window.updateScenarioBadge = updateScenarioBadge;
  window.addScenarioToSession = addScenarioToSession;
  window.setActiveScenario = setActiveScenario;
  window.updateBreadcrumb = updateBreadcrumb;
  window.updateScenarioBreadcrumb = updateScenarioBreadcrumb;
  window.createNewScenario = createNewScenario;
  window.removeScenarioFromSession = removeScenarioFromSession;
  window.renameScenario = renameScenario;
  window.loadScenarioIntoUI = loadScenarioIntoUI;
  window.getScenarioParams = getScenarioParams;
  window.renderScenarioList = renderScenarioList;
  window.showSaveDialog = showSaveDialog;
  window.hideSaveDialog = hideSaveDialog;
  window.exportAsCtcc = exportAsCtcc;
  window.exportAsCsv = exportAsCsv;
  window.validateCtccFile = validateCtccFile;
  window.loadCtccFile = loadCtccFile;
  window.loadCsvFile = loadCsvFile;
  window.loadCtccJson = loadCtccJson;
  window.displayCsvFiles = displayCsvFiles;
  window.downloadCsvFile = downloadCsvFile;
  window.downloadAllCsvFiles = downloadAllCsvFiles;
})();

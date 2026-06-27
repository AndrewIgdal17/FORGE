// CTCC Scenario UI Layer
// Extracted from scenarios.js — loaded via <script src="/static/scenario-ui.js">
// Depends on: scenario-data.js, comparison.js, utils.js, scenario-workspace.js (workspace only)

(function() {
'use strict';
var C = window.CTCC;

async function removeScenarioFromSession(id) {
  await deleteScenarioFromDB(id);
  C.sessionScenarios = C.sessionScenarios.filter(s => s.id !== id);
  C.comparisonScenarioIds.delete(id);
  if (C.comparisonBaselineId === id) C.comparisonBaselineId = null;
  renderScenarioList();
  renderCompareSelector();
  updateScenarioBadge();
}

function renameScenario(id, newName) {
  const scenario = C.sessionScenarios.find(s => s.id === id);
  if (scenario && newName.trim()) {
    scenario.customName = newName.trim();
    _sb.from('scenario').update({ name: scenario.customName, updated_at: new Date().toISOString() })
      .eq('id', id).then(({ error }) => { if (error) console.error('Failed to rename:', error); });
    if (id === C.activeScenarioId) {
      C.activeScenarioName = scenario.customName;
      updateScenarioBreadcrumb();
    }
    renderScenarioList();
    renderCompareSelector();
  }
}

async function duplicateScenario(sourceScenario) {
  const newName = generateScenarioName(sourceScenario.customName + ' (copy)');
  let fullInputs = sourceScenario.inputs;
  if (sourceScenario.ref_snapshot_id) {
    const snap = await loadSnapshot(sourceScenario.ref_snapshot_id);
    if (snap) {
      fullInputs = assembleFullInputs(
        snap,
        sourceScenario.overrides,
        sourceScenario.inputs || {}
      );
    }
  }
  if (sourceScenario.id === C.activeScenarioId && typeof collectJsonData === 'function') {
    fullInputs = collectJsonData() || fullInputs;
  }
  const scenario = await addScenarioToSession(
    fullInputs,
    sourceScenario.results ? JSON.parse(JSON.stringify(sourceScenario.results)) : null,
    { timestamp: new Date().toISOString(), source: 'manual' },
    newName
  );
  if (window.location.pathname === '/app/workspace' && typeof setActiveScenario === 'function') {
    setActiveScenario(scenario);
  } else {
    renderScenarioList();
    renderCompareSelector();
  }
}

function loadScenarioIntoUI(scenario) {
  if (window.location.pathname === '/app/workspace' && typeof setActiveScenario === 'function') {
    setActiveScenario(scenario);
  } else {
    window.location.href = '/app/workspace?scenario=' + scenario.id;
  }
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
    return;
  }

  const table = document.createElement('table');
  table.className = 'scenario-list-table';
  table.style.cssText = 'width: 100%; border-collapse: collapse;';

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  const thScenario = document.createElement('th');
  thScenario.textContent = 'Scenario';
  const thActions = document.createElement('th');
  thActions.textContent = '';
  const thFill = document.createElement('th');
  thFill.style.width = '100%';
  const thDrag = document.createElement('th');
  thDrag.style.width = '20px';
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
    const isOwner = !C.currentUserId || scenario.user_id === C.currentUserId;
    const card = document.createElement('tr');
    card.className = 'scenario-card' + (isActive ? ' scenario-card-active' : '');
    card.dataset.scenarioId = scenario.id;

    const infoTd = document.createElement('td');
    infoTd.className = 'scenario-card-info';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'scenario-card-name';
    nameSpan.textContent = scenario.customName;
    if (isOwner) {
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
    } else {
      nameSpan.style.cursor = 'default';
      nameSpan.title = '';
    }
    infoTd.appendChild(nameSpan);

    const params = document.createElement('span');
    params.className = 'scenario-card-params';
    params.textContent = getScenarioParams(scenario);
    infoTd.appendChild(params);

    const meta = document.createElement('span');
    meta.className = 'scenario-card-meta';
    const sourceLabel = scenario.metadata?.source === 'run' ? 'Calculated' :
                        scenario.metadata?.source === 'upload-ctcc' ? 'Uploaded (.ctcc)' :
                        scenario.metadata?.source === 'upload-csv' ? 'Uploaded (.csv)' :
                        scenario.metadata?.source === 'new' ? 'Draft' :
                        scenario.metadata?.source === 'wizard' ? 'Wizard' : 'Saved';
    const ts = scenario.metadata?.timestamp ? formatTimestamp(scenario.metadata.timestamp) : '';
    meta.textContent = sourceLabel + (ts ? ' ' + ts : '');
    infoTd.appendChild(meta);

    if (scenario._owner) {
      const owner = document.createElement('span');
      owner.className = 'scenario-card-meta';
      owner.style.fontStyle = 'italic';
      const ownerParts = [scenario._owner.username];
      if (scenario._owner.org) ownerParts.push(scenario._owner.org);
      owner.textContent = 'Created by ' + ownerParts.join(' \u00b7 ');
      infoTd.appendChild(owner);
    }

    card.appendChild(infoTd);

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
      const openBtn = document.createElement('button');
      openBtn.type = 'button';
      openBtn.className = 'load-btn';
      openBtn.textContent = 'Open';
      openBtn.addEventListener('click', function() {
        if (window.location.pathname === '/app/workspace') {
          setActiveScenario(scenario);
        } else {
          window.location.href = '/app/workspace?scenario=' + scenario.id;
        }
      });
      actions.appendChild(openBtn);
    }

    if (isOwner) {
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
      saveHereBtn.addEventListener('click', async () => {
        var currentInputs = typeof collectJsonData === 'function' ? collectJsonData() : null;
        if (!currentInputs) return;
        scenario.inputs = currentInputs;
        scenario.results = C.lastRunResults;
        scenario.metadata.timestamp = new Date().toISOString();
        scenario.metadata.source = 'manual';
        await saveScenarioToDB(scenario);
        renderScenarioList();
        renderCompareSelector();
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

      const dupBtn = document.createElement('button');
      dupBtn.type = 'button';
      dupBtn.textContent = 'Duplicate';
      dupBtn.addEventListener('click', () => duplicateScenario(scenario));
      actions.appendChild(dupBtn);
    }

    if (!isOwner) {
      const dupBtn = document.createElement('button');
      dupBtn.type = 'button';
      dupBtn.textContent = 'Duplicate';
      dupBtn.addEventListener('click', () => duplicateScenario(scenario));
      actions.appendChild(dupBtn);
    }

    actionsTd.appendChild(actions);
    card.appendChild(actionsTd);

    const dragTd = document.createElement('td');
    dragTd.className = 'scenario-drag-cell';
    if (isOwner) {
      const dragHandle = document.createElement('span');
      dragHandle.className = 'scenario-drag-handle';
      dragHandle.title = 'Drag to reorder';
      dragHandle.draggable = true;
      dragTd.appendChild(dragHandle);
    }
    card.appendChild(dragTd);

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
          renderCompareSelector();
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
}

function renderCompareSelector() {
  const container = document.getElementById('compare-scenario-selector');
  if (!container) return;
  container.innerHTML = '';

  if (C.sessionScenarios.length === 0) {
    container.innerHTML = '<p style="color: rgba(0,0,0,0.5); padding: 1rem;">No scenarios to compare.</p>';
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
    renderCompareSelector();
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

  const thFill = document.createElement('th');
  thFill.style.width = '100%';

  headRow.appendChild(thCmp);
  headRow.appendChild(thBase);
  headRow.appendChild(thScenario);
  headRow.appendChild(thFill);
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  table.appendChild(tbody);

  C.sessionScenarios.forEach(scenario => {
    const row = document.createElement('tr');
    row.className = 'scenario-card';

    row.addEventListener('click', (e) => {
      if (e.target.type === 'checkbox' || e.target.type === 'radio' || e.target.closest('.scenario-base-cell')) return;
      checkbox.checked = !checkbox.checked;
      checkbox.dispatchEvent(new Event('change'));
    });

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
      renderCompareSelector();
    });
    checkTd.appendChild(checkbox);
    row.appendChild(checkTd);

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
        renderCompareSelector();
      }
    });
    baseTd.appendChild(baseRadio);
    row.appendChild(baseTd);

    const infoTd = document.createElement('td');
    infoTd.className = 'scenario-card-info';
    const nameSpan = document.createElement('span');
    nameSpan.className = 'scenario-card-name';
    nameSpan.style.cursor = 'default';
    nameSpan.textContent = scenario.customName;
    infoTd.appendChild(nameSpan);
    const params = document.createElement('span');
    params.className = 'scenario-card-params';
    params.textContent = getScenarioParams(scenario);
    infoTd.appendChild(params);
    row.appendChild(infoTd);

    const fillerTd = document.createElement('td');
    fillerTd.style.width = '100%';
    row.appendChild(fillerTd);

    tbody.appendChild(row);
  });

  container.appendChild(table);
  renderComparisonTable();
}

function showSaveDialog() {
  var overlay = document.getElementById('save-overlay');
  if (!overlay) {
    if (C.activeScenarioId) window.location.href = '/app/workspace?scenario=' + C.activeScenarioId;
    else window.location.href = '/app/workspace';
    return;
  }
  const nameInput = document.getElementById('save-memory-name');
  nameInput.value = C.activeScenarioName || generateScenarioName('Scenario');
  // Reset selection
  document.querySelectorAll('.save-dialog .save-option').forEach(o => o.classList.remove('selected'));
  document.getElementById('save-opt-memory').classList.add('selected');
  // Update status indicators
  const notCalcIndicator = document.getElementById('save-status-indicator');
  const savedIndicator = document.getElementById('save-saved-indicator');

  if (!C.latestValidResults) {
    notCalcIndicator.textContent = 'No results yet \u2014 fill required fields to calculate';
    notCalcIndicator.style.color = '#b00020';
  } else {
    notCalcIndicator.textContent = '';
  }
  savedIndicator.textContent = '';
  overlay.classList.add('visible');
}

function hideSaveDialog() {
  var el = document.getElementById('save-overlay');
  if (el) el.classList.remove('visible');
}

window.renderScenarioList = renderScenarioList;
window.renderCompareSelector = renderCompareSelector;
window.removeScenarioFromSession = removeScenarioFromSession;
window.renameScenario = renameScenario;
window.duplicateScenario = duplicateScenario;
window.loadScenarioIntoUI = loadScenarioIntoUI;
window.getScenarioParams = getScenarioParams;
window.showSaveDialog = showSaveDialog;
window.hideSaveDialog = hideSaveDialog;

})();

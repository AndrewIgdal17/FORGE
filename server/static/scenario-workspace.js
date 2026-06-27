// CTCC Scenario Workspace UI
// Extracted from scenarios.js — loaded only on workspace.html
// Depends on: scenario-data.js, scenario-ui.js, workspace inline globals
// (autoCalculate, switchMainTab, switchTab, renderJsonInputs, renderCTCCResults,
//  updateTabStates, markResultsAvailable, setSnapshotOriginalData)

(function() {
'use strict';
var C = window.CTCC;

function setActiveScenario(scenario) {
  C.activeScenarioId = scenario.id;
  C.unsavedChanges = false;
  C.activeScenarioName = scenario.customName;
  updateScenarioBreadcrumb();
  updateTabStates();
  if (scenario.ref_snapshot_id && window._snapshotCache[scenario.ref_snapshot_id]) {
    const snap = window._snapshotCache[scenario.ref_snapshot_id];
    if (typeof setSnapshotOriginalData === 'function') {
      setSnapshotOriginalData(snap);
    }
    const full = assembleFullInputs(snap, scenario.overrides, scenario.inputs || {});
    renderJsonInputs(full);
  } else if (scenario.inputs && Object.keys(scenario.inputs).length > 0) {
    renderJsonInputs(scenario.inputs);
  }
  if (scenario.results) {
    renderCTCCResults(scenario.results);
    C.lastRunResults = JSON.parse(JSON.stringify(scenario.results));
    markResultsAvailable(0);
  } else {
    clearResults();
  }
  renderScenarioList();
  renderCompareSelector();
  if (!scenario.results && hasRequiredFields()) {
    autoCalculate();
  }
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

  segments.push({ label: 'Scenarios', action: function() { window.location.href = '/app/scenarios-manager'; } });
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


async function createNewScenario(name) {
  const trimmed = name.trim();
  if (!trimmed) return;
  const scenario = await addScenarioToSession(null, null,
    { timestamp: new Date().toISOString(), source: 'new' },
    trimmed
  );
  setActiveScenario(scenario);
  switchMainTab('inputs');
  switchTab(0);
  setTimeout(() => {
    const techBtn = document.querySelector('[data-sub-tab="technology"]');
    if (techBtn) techBtn.click();
  }, 50);
}

window.setActiveScenario = setActiveScenario;
window.createNewScenario = createNewScenario;
window.updateBreadcrumb = updateBreadcrumb;
window.updateScenarioBreadcrumb = updateScenarioBreadcrumb;

})();

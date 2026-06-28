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
    C.latestValidResults = scenario.results;
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

function lookupSidebarLabels(view, sectionId, subItemId) {
  var sections = window.SIDEBAR_SECTIONS && window.SIDEBAR_SECTIONS[view];
  if (!sections || !sectionId) return null;
  for (var i = 0; i < sections.length; i++) {
    if (sections[i].id !== sectionId) continue;
    var section = sections[i];
    if (!subItemId) return { section: section, subItem: null };
    for (var j = 0; j < section.subItems.length; j++) {
      if (section.subItems[j].id === subItemId) {
        return { section: section, subItem: section.subItems[j] };
      }
    }
    return { section: section, subItem: null };
  }
  return null;
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

  if (activeL1 === 'inputs' || activeL1 === 'results') {
    const viewKey = activeL1 === 'results' ? 'results' : 'inputs';
    const viewLabel = activeL1 === 'results' ? 'Results' : 'Inputs';
    segments.push({ label: viewLabel, action: () => switchMainTab(activeL1) });

    if (typeof getCurrentSubItem === 'function') {
      const current = getCurrentSubItem();
      const labels = lookupSidebarLabels(viewKey, current.sectionId, current.subItemId);
      if (labels && labels.section) {
        segments.push({
          label: labels.section.label,
          action: labels.section.subItems.length ? () => {
            if (typeof navigateToSubItem === 'function') {
              navigateToSubItem(labels.section.id, labels.section.subItems[0].id);
            }
          } : null
        });
        if (labels.subItem) {
          segments.push({
            label: labels.subItem.label,
            action: () => {
              if (typeof navigateToSubItem === 'function') {
                navigateToSubItem(labels.section.id, labels.subItem.id);
              }
            }
          });
        }
      }
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
  if (typeof navigateToSubItem === 'function') {
    navigateToSubItem('project-identity', 'technology');
  }
}

window.setActiveScenario = setActiveScenario;
window.createNewScenario = createNewScenario;
window.updateBreadcrumb = updateBreadcrumb;
window.updateScenarioBreadcrumb = updateScenarioBreadcrumb;

})();

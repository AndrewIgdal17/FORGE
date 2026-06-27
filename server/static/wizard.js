// CTCC New Scenario Wizard — full-screen multi-step flow for creating scenarios.

(function() {
'use strict';

  const CONSTRUCTION_TYPES = [
    'Overhead',
    'Underground Direct-Buried',
    'Underground Tunnel',
    'Subsea'
  ];

  const CAPACITY_OPTIONS = {
    AC: [140, 329, 394, 460, 657, 1792, 2598, 6625],
    DC: [500, 1500, 2000, 2400, 6000]
  };

  const CONDUCTOR_OPTIONS = {
    'Overhead': ['Standard Aluminum Conductor', 'Advanced Aluminum Conductor'],
    'Underground Direct-Buried': ['Underground Copper Conductor'],
    'Underground Tunnel': ['Underground Copper Conductor'],
    'Subsea': ['Subsea Copper Conductor']
  };

  const CONVERTER_OPTIONS = ['LCC Converter', 'VSC Converter'];

  const TERRAINS = [
    { key: 'farmland', label: 'Farmland' },
    { key: 'forested', label: 'Forested' },
    { key: 'rolling_hills', label: 'Rolling Hills' },
    { key: 'mountain', label: 'Mountain' },
    { key: 'desert_barren', label: 'Desert/Barren' },
    { key: 'urban', label: 'Urban' },
    { key: 'wetland', label: 'Wetland' },
    { key: 'scrubbed_flat', label: 'Scrubbed Flat' },
    { key: 'subsea', label: 'Subsea' }
  ];

  const ROW_ZONES = [1, 2, 3, 4, 5, 6];

  let state = createInitialState();

  function createInitialState() {
    const terrainMiles = {};
    TERRAINS.forEach(t => { terrainMiles[t.key] = 0; });
    const rowZoneMiles = {};
    ROW_ZONES.forEach(z => { rowZoneMiles[z] = 0; });
    return {
      step: 0,
      name: '',
      constructionType: '',
      acDc: '',
      projectType: 'greenfield',
      capacityMw: null,
      conductorType: '',
      converterType: '',
      oldAcDc: '',
      oldCapacityMw: null,
      oldConductorType: '',
      oldConverterType: '',
      terrainMiles,
      rowZoneMiles
    };
  }

  function getTotalSteps() {
    return state.projectType === 'reconductoring' ? 4 : 3;
  }

  function isRouteStep() {
    return state.step === (state.projectType === 'reconductoring' ? 3 : 2);
  }

  function isOldLineStep() {
    return state.projectType === 'reconductoring' && state.step === 2;
  }

  function validateCurrentStep() {
    switch (state.step) {
      case 0:
        return state.name.trim().length > 0;
      case 1:
        if (!state.constructionType || !state.acDc || !state.capacityMw || !state.conductorType) return false;
        if (state.acDc === 'DC' && !state.converterType) return false;
        return true;
      case 2:
        if (state.projectType === 'reconductoring') {
          if (!state.oldAcDc || !state.oldCapacityMw || !state.oldConductorType) return false;
          if (state.oldAcDc === 'DC' && !state.oldConverterType) return false;
          return true;
        }
        return hasTerrainMiles();
      default:
        return hasTerrainMiles();
    }
  }

  function hasTerrainMiles() {
    return TERRAINS.some(t => (state.terrainMiles[t.key] || 0) > 0);
  }

  function terrainTotal() {
    return TERRAINS.reduce((sum, t) => sum + (state.terrainMiles[t.key] || 0), 0);
  }

  function rowZoneTotal() {
    return ROW_ZONES.reduce((sum, z) => sum + (state.rowZoneMiles[z] || 0), 0);
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function makeSelect(className, options, value, placeholder) {
    const select = el('select', className);
    if (placeholder) {
      const ph = el('option');
      ph.value = '';
      ph.textContent = placeholder;
      ph.disabled = true;
      if (!value) ph.selected = true;
      select.appendChild(ph);
    }
    options.forEach(opt => {
      const o = el('option');
      const val = typeof opt === 'object' ? opt.value : opt;
      o.value = String(val);
      o.textContent = typeof opt === 'object' ? opt.label : String(opt);
      select.appendChild(o);
    });
    if (value != null && value !== '') select.value = String(value);
    return select;
  }

  function makeRadioGroup(name, choices, current, onChange) {
    const group = el('div', 'wizard-radio-group');
    choices.forEach(choice => {
      const label = el('label', 'wizard-radio');
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = name;
      input.value = choice.value;
      if (current === choice.value) input.checked = true;
      input.addEventListener('change', () => {
        if (input.checked) onChange(choice.value);
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(choice.label));
      group.appendChild(label);
    });
    return group;
  }

  function renderStepIndicator(container) {
    const total = getTotalSteps();
    const current = state.step + 1;
    container.innerHTML = '';
    const indicator = el('div', 'wizard-step-indicator');
    const dots = Array.from({ length: total }, (_, i) =>
      i <= state.step ? '\u25CF' : '\u25CB'
    ).join(' ');
    indicator.appendChild(el('div', null, 'Step ' + current + ' of ' + total));
    indicator.appendChild(el('div', null, dots));
    container.appendChild(indicator);
  }

  function renderNameScreen(content) {
    content.appendChild(el('h2', null, 'Name your scenario'));
    const field = el('div', 'wizard-field');
    const input = el('input', 'wizard-input');
    input.type = 'text';
    input.placeholder = 'Scenario name';
    input.value = state.name;
    input.addEventListener('input', () => {
      state.name = input.value;
      updateNavButtons();
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && validateCurrentStep()) goNext();
      if (e.key === 'Escape') hideWizard();
    });
    field.appendChild(input);
    content.appendChild(field);
    content.appendChild(el('p', 'wizard-hint',
      'This identifies your scenario in the comparison table and exports. You can rename it later.'));
    setTimeout(() => input.focus(), 0);
  }

  function renderProjectTypeScreen(content) {
    content.appendChild(el('h2', null, 'Define your project'));

    const ctField = el('div', 'wizard-field');
    ctField.appendChild(el('label', null, 'Construction type'));
    const ctGroup = makeRadioGroup('wizard-construction', CONSTRUCTION_TYPES.map(v => ({ value: v, label: v })),
      state.constructionType, (val) => {
        state.constructionType = val;
        if (!CONDUCTOR_OPTIONS[val]?.includes(state.conductorType)) state.conductorType = '';
        renderWizard();
      });
    ctField.appendChild(ctGroup);
    content.appendChild(ctField);

    const acField = el('div', 'wizard-field');
    acField.appendChild(el('label', null, 'AC/DC'));
    const acGroup = makeRadioGroup('wizard-acdc', [
      { value: 'AC', label: 'AC' },
      { value: 'DC', label: 'DC' }
    ], state.acDc, (val) => {
      state.acDc = val;
      if (state.capacityMw && !CAPACITY_OPTIONS[val]?.includes(state.capacityMw)) {
        state.capacityMw = null;
      }
      if (val === 'AC') state.converterType = '';
      renderWizard();
    });
    acField.appendChild(acGroup);
    content.appendChild(acField);

    const ptField = el('div', 'wizard-field');
    ptField.appendChild(el('label', null, 'Project type'));
    const ptGroup = makeRadioGroup('wizard-project-type', [
      { value: 'greenfield', label: 'Greenfield (new build)' },
      { value: 'reconductoring', label: 'Reconductoring (existing corridor)' }
    ], state.projectType, (val) => {
      state.projectType = val;
      if (state.step >= getTotalSteps()) state.step = getTotalSteps() - 1;
      renderWizard();
    });
    ptField.appendChild(ptGroup);
    content.appendChild(ptField);

    const capField = el('div', 'wizard-field');
    capField.appendChild(el('label', null, 'Capacity (MW)'));
    const capOpts = state.acDc ? CAPACITY_OPTIONS[state.acDc] || [] : [];
    const capSelect = makeSelect('wizard-select', capOpts, state.capacityMw, '\u2014 Select \u2014');
    capSelect.disabled = !state.acDc;
    capSelect.addEventListener('change', () => {
      state.capacityMw = capSelect.value ? parseInt(capSelect.value, 10) : null;
      updateNavButtons();
    });
    capField.appendChild(capSelect);
    content.appendChild(capField);

    const condField = el('div', 'wizard-field');
    condField.appendChild(el('label', null, 'Conductor'));
    const condOpts = state.constructionType ? CONDUCTOR_OPTIONS[state.constructionType] || [] : [];
    const condSelect = makeSelect('wizard-select', condOpts, state.conductorType, '\u2014 Select \u2014');
    condSelect.disabled = !state.constructionType;
    condSelect.addEventListener('change', () => {
      state.conductorType = condSelect.value;
      updateNavButtons();
    });
    condField.appendChild(condSelect);
    content.appendChild(condField);

    if (state.acDc === 'DC') {
      const convField = el('div', 'wizard-field');
      convField.appendChild(el('label', null, 'Converter'));
      const convGroup = makeRadioGroup('wizard-converter', CONVERTER_OPTIONS.map(v => ({ value: v, label: v })),
        state.converterType, (val) => {
          state.converterType = val;
          updateNavButtons();
        });
      convField.appendChild(convGroup);
      content.appendChild(convField);
    }
  }

  function renderOldLineScreen(content) {
    content.appendChild(el('h2', null, 'Existing line details'));

    const acField = el('div', 'wizard-field');
    acField.appendChild(el('label', null, 'Old AC/DC'));
    const acGroup = makeRadioGroup('wizard-old-acdc', [
      { value: 'AC', label: 'AC' },
      { value: 'DC', label: 'DC' }
    ], state.oldAcDc, (val) => {
      state.oldAcDc = val;
      if (state.oldCapacityMw && !CAPACITY_OPTIONS[val]?.includes(state.oldCapacityMw)) {
        state.oldCapacityMw = null;
      }
      if (val === 'AC') state.oldConverterType = '';
      renderWizard();
    });
    acField.appendChild(acGroup);
    content.appendChild(acField);

    const capField = el('div', 'wizard-field');
    capField.appendChild(el('label', null, 'Old capacity (MW)'));
    const capOpts = state.oldAcDc ? CAPACITY_OPTIONS[state.oldAcDc] || [] : [];
    const capSelect = makeSelect('wizard-select', capOpts, state.oldCapacityMw, '\u2014 Select \u2014');
    capSelect.disabled = !state.oldAcDc;
    capSelect.addEventListener('change', () => {
      state.oldCapacityMw = capSelect.value ? parseInt(capSelect.value, 10) : null;
      updateNavButtons();
    });
    capField.appendChild(capSelect);
    content.appendChild(capField);

    const condField = el('div', 'wizard-field');
    condField.appendChild(el('label', null, 'Old conductor'));
    const condOpts = state.constructionType ? CONDUCTOR_OPTIONS[state.constructionType] || [] : [];
    const condSelect = makeSelect('wizard-select', condOpts, state.oldConductorType, '\u2014 Select \u2014');
    condSelect.addEventListener('change', () => {
      state.oldConductorType = condSelect.value;
      updateNavButtons();
    });
    condField.appendChild(condSelect);
    content.appendChild(condField);

    if (state.oldAcDc === 'DC') {
      const convField = el('div', 'wizard-field');
      convField.appendChild(el('label', null, 'Old converter'));
      const convGroup = makeRadioGroup('wizard-old-converter', CONVERTER_OPTIONS.map(v => ({ value: v, label: v })),
        state.oldConverterType, (val) => {
          state.oldConverterType = val;
          updateNavButtons();
        });
      convField.appendChild(convGroup);
      content.appendChild(convField);
    }
  }

  function renderRouteScreen(content) {
    content.appendChild(el('h2', null, 'Define your route'));

    const grid = el('div', 'wizard-route-grid');

    const terrainCol = el('div');
    terrainCol.appendChild(el('h3', null, 'Terrain miles'));
    const terrainTable = el('table', 'wizard-table');
    const terrainThead = document.createElement('thead');
    const terrainHeadRow = document.createElement('tr');
    terrainHeadRow.appendChild(el('th', null, 'Terrain'));
    terrainHeadRow.appendChild(el('th', null, 'Miles'));
    terrainThead.appendChild(terrainHeadRow);
    terrainTable.appendChild(terrainThead);
    const terrainTbody = document.createElement('tbody');
    const totalRow = document.createElement('tr');
    const totalLabelTd = el('td', null, 'Total');
    const totalValueTd = el('td', null, '0 mi');
    totalValueTd.id = 'wizard-terrain-total';

    TERRAINS.forEach(t => {
      const row = document.createElement('tr');
      row.appendChild(el('td', null, t.label));
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.type = 'number';
      input.min = '0';
      input.step = 'any';
      input.value = state.terrainMiles[t.key] || 0;
      input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        state.terrainMiles[t.key] = isNaN(val) ? 0 : Math.max(0, val);
        totalValueTd.textContent = terrainTotal().toFixed(2).replace(/\.?0+$/, '') + ' mi';
        updateNavButtons();
      });
      td.appendChild(input);
      row.appendChild(td);
      terrainTbody.appendChild(row);
    });

    totalRow.appendChild(totalLabelTd);
    totalRow.appendChild(totalValueTd);
    terrainTbody.appendChild(totalRow);
    terrainTable.appendChild(terrainTbody);
    terrainCol.appendChild(terrainTable);
    grid.appendChild(terrainCol);

    const rowCol = el('div');
    rowCol.appendChild(el('h3', null, 'ROW zones'));
    const rowTable = el('table', 'wizard-table');
    const rowThead = document.createElement('thead');
    const rowHeadRow = document.createElement('tr');
    rowHeadRow.appendChild(el('th', null, 'Zone'));
    rowHeadRow.appendChild(el('th', null, 'Miles'));
    rowThead.appendChild(rowHeadRow);
    rowTable.appendChild(rowThead);
    const rowTbody = document.createElement('tbody');
    const rowTotalRow = document.createElement('tr');
    const rowTotalLabelTd = el('td', null, 'Total');
    const rowTotalValueTd = el('td', null, '0 miles');
    rowTotalValueTd.id = 'wizard-row-total';

    ROW_ZONES.forEach(z => {
      const row = document.createElement('tr');
      row.appendChild(el('td', null, 'Zone ' + z));
      const td = document.createElement('td');
      const input = document.createElement('input');
      input.type = 'number';
      input.min = '0';
      input.step = 'any';
      input.value = state.rowZoneMiles[z] || 0;
      input.addEventListener('input', () => {
        const val = parseFloat(input.value);
        state.rowZoneMiles[z] = isNaN(val) ? 0 : Math.max(0, val);
        rowTotalValueTd.textContent = rowZoneTotal().toFixed(2).replace(/\.?0+$/, '') + ' miles';
      });
      td.appendChild(input);
      row.appendChild(td);
      rowTbody.appendChild(row);
    });

    rowTotalRow.appendChild(rowTotalLabelTd);
    rowTotalRow.appendChild(rowTotalValueTd);
    rowTbody.appendChild(rowTotalRow);
    rowTable.appendChild(rowTbody);
    rowCol.appendChild(rowTable);
    grid.appendChild(rowCol);

    content.appendChild(grid);
    content.appendChild(el('p', 'wizard-hint', 'At least one terrain must have miles greater than 0.'));

    totalValueTd.textContent = terrainTotal().toFixed(2).replace(/\.?0+$/, '') + ' mi';
    rowTotalValueTd.textContent = rowZoneTotal().toFixed(2).replace(/\.?0+$/, '') + ' miles';
  }

  function renderWizard() {
    const content = document.getElementById('wizard-content');
    const nav = document.getElementById('wizard-nav');
    if (!content || !nav) return;

    content.innerHTML = '';
    nav.innerHTML = '';

    renderStepIndicator(content);

    if (state.step === 0) {
      renderNameScreen(content);
    } else if (state.step === 1) {
      renderProjectTypeScreen(content);
    } else if (isOldLineStep()) {
      renderOldLineScreen(content);
    } else if (isRouteStep()) {
      renderRouteScreen(content);
    }

    const backBtn = el('button', 'wizard-btn wizard-btn-back', '\u2190 Back');
    backBtn.type = 'button';
    backBtn.addEventListener('click', goBack);

    const nextBtn = el('button', 'wizard-btn wizard-btn-next', 'Next \u2192');
    nextBtn.type = 'button';
    nextBtn.id = 'wizard-next-btn';
    nextBtn.addEventListener('click', () => {
      if (state.step === getTotalSteps() - 1) completeWizard();
      else goNext();
    });

    if (state.step > 0) nav.appendChild(backBtn);
    nav.appendChild(nextBtn);

    updateNavButtons();
  }

  function updateNavButtons() {
    const nextBtn = document.getElementById('wizard-next-btn');
    if (!nextBtn) return;
    const onLast = state.step === getTotalSteps() - 1;
    nextBtn.textContent = onLast ? 'Create Scenario \u2192' : 'Next \u2192';
    nextBtn.disabled = !validateCurrentStep();
  }

  function goNext() {
    if (!validateCurrentStep()) return;
    if (state.step < getTotalSteps() - 1) {
      state.step += 1;
      renderWizard();
    }
  }

  function goBack() {
    if (state.step > 0) {
      state.step -= 1;
      renderWizard();
    }
  }

  function mergeWizardIntoSnapshot(snapshot) {
    const full = JSON.parse(JSON.stringify(snapshot));
    const set = window.setValueAtPath;

    set(full, '01_project_technical_details.project.name', state.name.trim());
    set(full, '01_project_technical_details.project.construction_type', state.constructionType);
    set(full, '01_project_technical_details.project.ac_dc', state.acDc);
    set(full, '01_project_technical_details.project.capacity_mw', state.capacityMw);
    set(full, '01_project_technical_details.project.conductor_type', state.conductorType);
    set(full, '01_project_technical_details.project.converter_type',
      state.acDc === 'AC' ? 'NA' : state.converterType);
    set(full, '01_project_technical_details.project.reconductoring',
      state.projectType === 'reconductoring');

    if (state.projectType === 'reconductoring') {
      set(full, '01_project_technical_details.project.old_ac_dc', state.oldAcDc);
      set(full, '01_project_technical_details.project.old_capacity_mw', state.oldCapacityMw);
      set(full, '01_project_technical_details.project.old_conductor_type', state.oldConductorType);
      if (state.oldAcDc === 'DC') {
        set(full, '01_project_technical_details.project.old_converter_type', state.oldConverterType);
      }
    }

    TERRAINS.forEach(t => {
      set(full, '02_project_physical_details.terrain.terrain_miles.' + t.key, state.terrainMiles[t.key] || 0);
    });

    ROW_ZONES.forEach(z => {
      set(full, '11_project_row_details.right_of_way.zone_' + z + '.miles', state.rowZoneMiles[z] || 0);
    });

    return full;
  }

  async function completeWizard() {
    if (!validateCurrentStep()) return;

    const snapshot = window._latestSnapshot;
    if (!snapshot) {
      alert('Reference data is not loaded yet. Please wait a moment and try again.');
      return;
    }

    const fullInputs = mergeWizardIntoSnapshot(snapshot);
    const name = state.name.trim();
    const metadata = { timestamp: new Date().toISOString(), source: 'wizard' };

    hideWizard();

    const scenario = await addScenarioToSession(fullInputs, null, metadata, name);
    setActiveScenario(scenario);
    if (typeof showApp === 'function') showApp();
    switchMainTab('inputs');
    switchTab(0);
  }

  function showWizard() {
    state = createInitialState();
    const overlay = document.getElementById('wizard-overlay');
    if (!overlay) return;
    overlay.style.display = 'flex';
    renderWizard();
  }

  function hideWizard() {
    const overlay = document.getElementById('wizard-overlay');
    if (overlay) overlay.style.display = 'none';
  }

  document.addEventListener('keydown', (e) => {
    const overlay = document.getElementById('wizard-overlay');
    if (!overlay || overlay.style.display === 'none') return;
    if (e.key === 'Escape') hideWizard();
  });

  window.showWizard = showWizard;
  window.hideWizard = hideWizard;

})();

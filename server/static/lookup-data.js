// CTCC Lookup Data Tables
// Extracted from index.html — loaded via <script src="/static/lookup-data.js">

// -----------------------------------------------------------------
// Derived parameter utilities (client-side subset)
// ROW width lookup table loaded once at startup; enables live
// acres calculations without a server round-trip.
// -----------------------------------------------------------------
let rowWidthLookup = null;
let buildCostLookup = null;
let circuitDetailsLookup = null;
let structureDetailsLookup = null;
let converterDetailsLookup = null;
let conductorOmLookup = null;
let vegetationManagementLookup = null;

async function fetchRowWidths(baseUrl) {
  if (rowWidthLookup) return rowWidthLookup;
  const resp = await fetch(new URL("/static/row_widths.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load row_widths.json: " + resp.status);
  rowWidthLookup = await resp.json();
  return rowWidthLookup;
}

async function fetchBuildCosts(baseUrl) {
  if (buildCostLookup) return buildCostLookup;
  const resp = await fetch(new URL("/static/build_costs.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load build_costs.json: " + resp.status);
  buildCostLookup = await resp.json();
  return buildCostLookup;
}

async function fetchCircuitDetails(baseUrl) {
  if (circuitDetailsLookup) return circuitDetailsLookup;
  const resp = await fetch(new URL("/static/circuit_details.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load circuit_details.json: " + resp.status);
  circuitDetailsLookup = await resp.json();
  return circuitDetailsLookup;
}

async function fetchStructureDetails(baseUrl) {
  if (structureDetailsLookup) return structureDetailsLookup;
  const resp = await fetch(new URL("/static/structure_details.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load structure_details.json: " + resp.status);
  structureDetailsLookup = await resp.json();
  return structureDetailsLookup;
}

async function fetchConverterDetails(baseUrl) {
  if (converterDetailsLookup) return converterDetailsLookup;
  const resp = await fetch(new URL("/static/converter_details.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load converter_details.json: " + resp.status);
  converterDetailsLookup = await resp.json();
  return converterDetailsLookup;
}

async function fetchConductorOm(baseUrl) {
  if (conductorOmLookup) return conductorOmLookup;
  const resp = await fetch(new URL("/static/conductor_om.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load conductor_om.json: " + resp.status);
  conductorOmLookup = await resp.json();
  return conductorOmLookup;
}

async function fetchVegetationManagement(baseUrl) {
  if (vegetationManagementLookup) return vegetationManagementLookup;
  const resp = await fetch(new URL("/static/vegetation_management.json", baseUrl).toString());
  if (!resp.ok) throw new Error("Failed to load vegetation_management.json: " + resp.status);
  vegetationManagementLookup = await resp.json();
  return vegetationManagementLookup;
}

function normalizeCT(ct) {
  const ctNorm = {'Underground Direct-Buried':'Underground direct-buried','Underground Tunnel':'Underground tunnel'};
  return ctNorm[ct] || ct;
}

function buildCategoryString() {
  const get = path => {
    const el = document.querySelector(`[data-path="${path}"]`);
    return el ? el.value : '';
  };
  let ct = get('01_project_technical_details.project.construction_type');
  const acDc = get('01_project_technical_details.project.ac_dc');
  const cap = get('01_project_technical_details.project.capacity_mw');
  const cond = get('01_project_technical_details.project.conductor_type');
  const conv = acDc === 'DC'
    ? get('01_project_technical_details.project.converter_type')
    : 'NA';
  if (!ct || !acDc || !cap || !cond) return null;
  ct = normalizeCT(ct);
  const capNum = String(cap).replace(/\s*MW\s*/i, '');
  return `${ct}/${acDc}/${capNum}MW/${cond}/${conv}`;
}

function getRowWidthFeet() {
  if (!rowWidthLookup) return null;
  const cat = buildCategoryString();
  return cat ? (rowWidthLookup[cat] ?? null) : null;
}

function validateCategoryString() {
  const cat = buildCategoryString();
  if (!cat) return { valid: false, reason: 'Incomplete category fields' };

  const missing = [];
  if (buildCostLookup && !(cat in buildCostLookup)) missing.push('build_costs');
  if (circuitDetailsLookup && !(cat in circuitDetailsLookup)) missing.push('circuit_details');
  if (rowWidthLookup && !(cat in rowWidthLookup)) missing.push('row_widths');

  const acDc = document.querySelector('[data-path="01_project_technical_details.project.ac_dc"]')?.value;
  if (acDc === 'DC' && converterDetailsLookup && !(cat in converterDetailsLookup)) {
    missing.push('converter_details');
  }

  if (missing.length > 0) {
    return { valid: false, reason: `Configuration "${cat}" not found in: ${missing.join(', ')}` };
  }

  if (isReconductoring()) {
    const oldCat = buildOldCategoryString();
    if (oldCat) {
      const oldMissing = [];
      if (buildCostLookup && !(oldCat in buildCostLookup)) oldMissing.push('build_costs');
      if (circuitDetailsLookup && !(oldCat in circuitDetailsLookup)) oldMissing.push('circuit_details');
      if (oldMissing.length > 0) {
        return { valid: false, reason: `Old-line configuration "${oldCat}" not found in: ${oldMissing.join(', ')}` };
      }
    }
  }

  return { valid: true, key: cat };
}

function getBuildCostEntry() {
  if (!buildCostLookup) return null;
  const cat = buildCategoryString();
  return cat ? (buildCostLookup[cat] ?? null) : null;
}

function getCircuitDetailsEntry() {
  if (!circuitDetailsLookup) return null;
  const cat = buildCategoryString();
  const entry = cat ? circuitDetailsLookup[cat] : null;
  if (entry) return entry;
  const get = path => document.querySelector(`[data-path="${path}"]`)?.value || '';
  const acDc = get('01_project_technical_details.project.ac_dc');
  if (acDc === 'DC') {
    let ct = get('01_project_technical_details.project.construction_type');
    const ctNorm = {'Underground Direct-Buried':'Underground direct-buried','Underground Tunnel':'Underground tunnel'};
    ct = ctNorm[ct] || ct;
    const cap = String(get('01_project_technical_details.project.capacity_mw')).replace(/\s*MW\s*/i, '');
    const cond = get('01_project_technical_details.project.conductor_type');
    if (ct && cap && cond) {
      return circuitDetailsLookup[`${ct}/${acDc}/${cap}MW/${cond}/VSC Converter`] ?? null;
    }
  }
  return null;
}

function getOldCircuitDetailsEntry() {
  if (!circuitDetailsLookup) return null;
  const oldCat = buildOldCategoryString();
  return oldCat ? (circuitDetailsLookup[oldCat] ?? null) : null;
}

function buildOldCategoryString() {
  const get = path => {
    const el = document.querySelector(`[data-path="${path}"]`);
    return el ? el.value : '';
  };
  let ct = get('01_project_technical_details.project.construction_type');
  const oldAcDc = get('01_project_technical_details.project.old_ac_dc');
  const oldCap = get('01_project_technical_details.project.old_capacity_mw');
  const oldCond = get('01_project_technical_details.project.old_conductor_type');
  if (!ct || !oldAcDc || !oldCap || !oldCond) return null;
  ct = normalizeCT(ct);
  const capNum = String(oldCap).replace(/\s*MW\s*/i, '');
  const oldConv = oldAcDc === 'DC'
    ? (document.querySelector('[data-path="01_project_technical_details.project.old_converter_type"]')?.value || 'NA')
    : 'NA';
  return `${ct}/${oldAcDc}/${capNum}MW/${oldCond}/${oldConv}`;
}


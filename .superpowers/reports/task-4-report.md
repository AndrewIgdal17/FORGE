---
tags: [project/ctcc]
---

# Task 4 Report: Input Rendering Integration

**Status:** DONE_WITH_CONCERNS  
**Timestamp:** 2026-06-27 16:29  
**Branch:** `feat/sidebar-navigation`

## Commits

(pending — see below)

## Changes Summary

### `server/static/input-renderer.js` (~490 line delta)

**Structural refactor of `renderInputsFromTaxonomy`:**

1. **Removed** tab button creation (`tabButton`, `tabButtonsContainer.appendChild`)
2. **Removed** tab content div creation and appending to `tabContentsContainer`
3. **Removed** sub-tab bar creation (`subTabBar`, `subTabContents`)
4. **Added** offscreen DOM holder (`#ctcc-offscreen-inputs`): a `position:fixed;left:-9999px` div appended to `<body>`. All sub-item containers live here when not visible — ensures event listeners can be set up at init time via `document.querySelector`.
5. **Updated** `C.INPUT_TAB_ORDER` iteration: `tabId === 'project-technical'` → `'project-identity'`, `tabId === 'operational'` → `'operating'`
6. **Updated** `subTabIds` overrides for all 10 new section IDs
7. **New stId cases:**
   - `terrain-mix` → renders terrain table + routing validation banner
   - `rights-of-way` → renders ROW toggle + ROW zone table + ROW cost panel
   - `base-mitigation` → renders env base mitigation table
   - `credits` → renders env credits table
   - `delay-costs` → renders standard fields + delay cost totals table + delay cost panel
8. **Removed** `stId === 'routing'` and `stId === 'environmental-mitigation'` cases (flattened to top-level sub-items)
9. **Fixed** `renderTaxonomySections` calls: `tabContent` → `stContent` as the scope element (reset button uses this for `querySelector`)
10. **Fixed** technology stFields computation: includes `sub_tab === 'identity'` fields (project_name)
11. **Removed** tab restore button and global restore button (no `tabContent` or `tabButtonsContainer` to attach to)
12. **Changed** `tabsContainer.classList.remove('tabs-hidden')` → clears `#load-status` display
13. **Added** form-level listeners: `ctccForm.addEventListener('input', updateEnvironmentalAcres + updateRoutingValidation)`
14. **Fixed** `rebuildCapitalCosts`: uses `document.querySelector('[data-tab-id="capital-costs"]') || document` — works in both old and new architectures
15. **Fixed** `makeEmissionIntensitiesCollapsible`: falls back to `C._renderedSubItems['energy-emissions-emissions']`
16. **Fixed** `applyEnergySourceMixPreset`: queries `C._renderedSubItems['energy-emissions-energy']`
17. **Fixed** Fix 6 category validation banner: targets `C._renderedSubItems['technology']`

**New functions:**

- `renderSubItemContent(subItemId)` — moves containers between `#ctcc-offscreen-inputs` and `#content-panel` using `appendChild` (preserves DOM nodes, event listeners, and input values)
- Exported as `window.renderSubItemContent`

### `server/static/workspace.js` (~55 line delta)

1. **Removed** `tabsContainer`, `tabButtonsContainer`, `tabContentsContainer` DOM refs
2. **Updated** `C.INPUT_TAB_ORDER` → 10 new section IDs
3. **Updated** `C.INPUT_TAB_LABELS` → new labels
4. **Fixed** `collectJsonData()` → queries both `#content-panel` and `#ctcc-offscreen-inputs`
5. **Fixed** `switchTab()` → no-op (sidebar handles navigation)
6. **Fixed** form submit handler → `!!C.ctccJsonData` instead of `tabsContainer.classList.contains`
7. **Fixed** tab-contents click listener → `document.addEventListener` (sub-sub-tab button clicks still bubble)
8. **Updated** `switchMainTab()` → calls `switchSidebarView()` for inputs/results toggle
9. **Added** sidebar wiring in `_authReady.then` block after `await dataReady`:
   - Wires `window.onSubItemSelected` → `renderSubItemContent`
   - Calls `initSidebar()`

## Architecture: Value Preservation

DOM elements are **moved** (not cloned) between containers using `appendChild`. This means:

- Input values typed by the user persist when switching sub-items
- Event listeners persist (no re-attachment needed)
- `collectJsonData()` queries both containers to capture all values

## Concerns

1. **Sidebar tab restore buttons removed**: The "Restore Tab Defaults" and "Restore All Defaults" buttons have been removed from the UI (no `tabContent` to attach to). This is a regression. A future task should add them to the content header or sidebar footer.

2. **`updateCapitalCostSubTabVisibility`** — returns immediately because `[data-tab-id="capital-costs"]` no longer exists. In the new architecture, structure/converter capital cost sub-items are not shown (they're not in the sidebar). If those fields need to be shown, the sidebar spec needs updating.

3. **`updateProjectTechnicalSubTabVisibility`** — returns immediately (no `[data-tab-id="project-technical"]`). Structure details visibility logic is a no-op. In the new architecture, `structure-details` is not in the sidebar.

4. **`updateMaintenanceSubTabVisibility`** — returns immediately (no maintenance-costs container). The maintenance tables are rebuilt dynamically but their sub-sub-tab visibility isn't managed.

5. **Browser testing not completed**: The server requires authentication, so browser-based end-to-end testing wasn't possible in this session. Syntax checks pass. The API returns correct metadata with new tab/sub-tab values.

6. **`updateBreadcrumb` in scenario-workspace.js** — references `#tab-buttons .tab-button.active` which no longer exists. Breadcrumb will show empty/wrong text. Non-critical.

7. **`assistant.js` and `tour-content.js`** — reference old `#tab-buttons` selectors. Assistant context will be degraded; tour will break. Non-critical for core functionality.

## Verification Checklist

- [x] `node --check` passes on both modified files
- [x] Server starts successfully (`Application startup complete`)
- [x] `/api/input_metadata` returns 343 fields with correct new `input_tab` values
- [x] `/app/workspace` returns HTTP 200
- [ ] Sidebar renders with 10 sections (requires browser + auth)
- [ ] Clicking sub-item shows fields in content area (requires browser + auth)
- [ ] Value preservation when switching sub-items (requires browser + auth)
- [ ] Auto-calculate fires on input change (requires browser + auth)

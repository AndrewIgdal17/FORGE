# Task 8 Report — Dead Code Removal + Tour Updates + Wire Search

**Status:** DONE_WITH_CONCERNS  
**Branch:** `feat/sidebar-navigation`  
**Date:** 2026-06-27

## Summary

Cleaned up legacy tab-system DOM/CSS references, wired sidebar search init, updated breadcrumb and tour targets for the sidebar layout, and removed the dead `#main-tab-results` container.

## Changes

### `workspace.js`
- Wired `initSidebarSearch()` immediately after `initSidebar()` in auth-ready init sequence
- Removed unused `ctccSection` / `ctcc-json-inputs` DOM refs and simplified `initCtccInputs()`
- Removed dead `.sub-sub-tab-button` click listener that called `updateBreadcrumb`
- Simplified `switchMainTab` main-tab-content toggling (single active panel)
- Added `updateBreadcrumb()` call in `onSubItemSelected` callback

### `scenario-workspace.js`
- Rewrote `updateBreadcrumb()` to use `getCurrentSubItem()` + `SIDEBAR_SECTIONS` instead of `#tab-buttons` / `#tab-contents` DOM queries
- Updated `createNewScenario()` to navigate via `navigateToSubItem('project-identity', 'technology')` instead of old tab clicks

### `tour-content.js`
- Replaced obsolete `.workspace-tab` and `#tab-buttons` selectors with sidebar/main-tab targets:
  - `.sidebar-section-header`
  - `.sidebar-subitem`
  - `.main-tab-button[data-tab="results"]`
  - `#content-panel`

### `workspace.html`
- Removed dead `#main-tab-results` wrapper
- Kept hidden `#result` element for legacy `renderCTCCResults` / `clearResults` sink

### `results-renderer.js`
- Updated scroll-container refs from `#main-tab-results` → `.content-area`

### `styles.css`
- Removed dead ID rules: `#ctcc-json-inputs`, `#tabs-container`, `#tabs-container.tabs-hidden`, `#tab-contents`
- **Kept** `.tab-button`, `.tab-content`, `.tabs`, `.sub-tab-*`, `.sub-sub-tab-*` — still used by `scenarios-manager.html`, `results-renderer.js` (legacy full render), and `input-renderer.js` (in-panel L3/L4 tabs)

### `input-renderer.js`
- Verified: no remaining old tab button/container creation (`tabButtonsContainer`, `#tab-buttons`, etc.)
- `C.SUB_TAB_LABELS` retained — still referenced for in-panel sub-sub-tab labels

## Verification

| Check | Result |
|-------|--------|
| JS syntax (`node --check`) | PASS — workspace.js, scenario-workspace.js, tour-content.js, results-renderer.js |
| `/app/workspace` HTTP 200 | PASS |
| Browser console / search / tour | Not run (auth-gated page) |

## Concerns

1. **`assistant.js`** still queries `#tab-buttons .tab-button.active` — assistant context for current sub-tab will be stale until a follow-up task updates it (out of scope for Task 8 file list).
2. **`renderCTCCResults`** still builds legacy tab UI into hidden `#result` — functional but redundant now that sidebar uses `renderResultsSubItem` + `C.latestValidResults`. Full removal would be a separate refactor.
3. **Tour step 4** (`#content-panel`) may show empty placeholder before first calculation — acceptable per brief ("even if steps need refinement").

## Commit

```
chore: remove dead tab code, wire search, update breadcrumb and tour targets
```

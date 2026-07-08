# Task 4: Input Rendering Integration

## Files
- Modify: `repos/ctcc/server/static/input-renderer.js` (~5460 lines)
- Modify: `repos/ctcc/server/static/workspace.js` (~847 lines)

## Context

This is Task 4 of 9 — the core integration task. Tasks 1-3 set up metadata (10 tabs), HTML shell (sidebar + content area), and sidebar.js (tree navigation). This task wires it all together so clicking a sidebar sub-item actually renders the corresponding input fields in the content area.

**Critical file: `input-renderer.js`** — This is a large file (5460 lines) that contains the taxonomy-driven form renderer. The key function is `renderInputsFromTaxonomy(data, taxonomyData, metadataList)` which currently:
1. Iterates over `C.INPUT_TAB_ORDER` (tab IDs)
2. Creates tab buttons (`.tab-button`) in `#tab-buttons`
3. Creates tab content divs (`.tab-content`) in `#tab-contents`
4. For each tab, iterates metadata to create sub-tab buttons and field inputs
5. After all tabs are built, runs post-render transforms

The refactor changes this to:
1. Build all field DOM elements and group them by `sub_tab` (sub-item ID)
2. Store groups in `C._renderedSubItems` (map of subItemId → DOM container)
3. Do NOT create any tab buttons
4. New function `renderSubItemContent(subItemId)` swaps the active content

**Critical file: `workspace.js`** — Contains the init sequence that calls `renderInputsFromTaxonomy`, sets up auto-calculate, and manages the tab config (`C.INPUT_TAB_ORDER`, `C.INPUT_TAB_LABELS`, `C.SUB_TAB_LABELS`).

Read BOTH files before making changes. Use semantic search or grep to understand the structure.

## Interfaces

### Consumed
- `window.initSidebar()` — from sidebar.js (Task 3)
- `window.onSubItemSelected` — callback property from sidebar.js
- `window.navigateToSubItem(sectionId, subItemId)` — from sidebar.js
- `window.SIDEBAR_SECTIONS` — from sidebar.js
- `C.inputMetadata` — array of field metadata objects (loaded from `/api/input_metadata`)
- `C.taxonomy` — taxonomy data (loaded from `/api/taxonomy`)
- `C.ctccJsonData` — the current input data object

### Produced
- `window.renderSubItemContent(subItemId)` — renders the fields for the given sub-item into `#content-panel`
- `C._renderedSubItems` — Map of subItemId → DOM container (DocumentFragment or div) holding the pre-built field elements for that sub-item
- `C._currentSubItemId` — string tracking which sub-item is currently rendered in the content panel

## Behavior Spec

### input-renderer.js changes

**Modify `renderInputsFromTaxonomy(data, taxonomyData, metadataList)`:**

The function currently builds tab buttons and tab content divs. Refactor it to:

1. **Keep the build phase** — still iterate metadata, still create all field DOM elements (inputs, selects, toggles, fuel mix rows, etc.) with all their attributes, event listeners, conditional visibility wiring, etc.

2. **Change the grouping** — instead of appending fields to tab-content divs organized by `input_tab`, group them by `sub_tab`. Create a container div for each unique `sub_tab` value. Store in `C._renderedSubItems`:
   ```javascript
   C._renderedSubItems = {};
   // For each field, determine its sub_tab and append to the right container
   ```

3. **Remove tab button creation** — do NOT create any `.tab-button`, `.sub-tab-button`, or `.sub-sub-tab-button` elements. Do not write to `#tab-buttons` (the element no longer exists in the DOM).

4. **Remove tab content div creation** — do NOT create `.tab-content` or `.sub-tab-content` divs in the DOM. The containers in `C._renderedSubItems` are held in memory, not attached to the document.

5. **Keep `#tabs-container` / class manipulation** — some code references `tabsContainer.classList.remove('tabs-hidden')`. Find the equivalent (the `#content-panel` is the new visible container — you may need to show/hide `#load-status` instead). The `tabs-hidden` class was used to hide the form until data loaded; now just clear `#load-status` text and let `#content-panel` show the content.

6. **After building, render the first sub-item** — call `renderSubItemContent` for the initially selected sub-item.

**New function `renderSubItemContent(subItemId)`:**

1. Serialize current sub-item's inputs into `C.ctccJsonData` before switching (so values are preserved):
   - Query all `input[data-path], select[data-path]` within `#content-panel`
   - For each, read the current value and write it back to `C.ctccJsonData` at the corresponding path
   - Use the existing `collectJsonData()` approach or a simpler per-field serialization

2. Clear `#content-panel` innerHTML (except keep `#load-status` if needed — or just clear everything since loading is done)

3. Get the pre-built container from `C._renderedSubItems[subItemId]`

4. Append (or clone) the container's children into `#content-panel`

5. Populate field values from `C.ctccJsonData` — iterate the rendered fields' `data-path` attributes and set their values from the data object

6. Run applicable post-render transforms:
   - `setupConditionalFieldListeners()` — conditional visibility
   - `insertCalculatedTotals()` — terrain, delay, ROW totals  
   - `restructureEnergySourceMix()` — fuel mix table (only if energy-mix sub-item)
   - `injectFuelMixPresetBar()` — preset dropdown (only if energy-mix)
   - `restructureEmissionIntensities()` — combined intensity table (only if emissions)
   - And other transforms that are relevant to the current sub-item
   - Note: many transforms are tab-scoped (they look for elements by ID that only exist in certain sub-items). They should be safe to call even when their target elements don't exist — they'll just find nothing. But verify this.

7. Set up auto-calculate listeners on the new content — attach `input` / `change` event listeners that trigger the debounced auto-calculate

8. Set `C._currentSubItemId = subItemId`

**IMPORTANT — Value preservation across sub-item switches:**
When the user switches from one sub-item to another, their edits must be preserved. The strategy:
- Before switching: serialize visible fields' values into `C.ctccJsonData`
- After switching: populate new fields from `C.ctccJsonData`
- `collectJsonData()` (used by auto-calculate and save) should read from `C.ctccJsonData` for non-visible fields and from DOM for the visible sub-item. OR: always serialize the current sub-item before calling `collectJsonData`. The simplest approach is to call a serialize function before any `collectJsonData` call.

### workspace.js changes

**Update `C.INPUT_TAB_ORDER`:**
Change from `['project-technical', 'benefits', ...]` to the new 10 tab IDs:
```javascript
C.INPUT_TAB_ORDER = ['project-identity', 'equipment', 'routing', 'benefits', 'financial', 'capital-costs', 'operating', 'risk', 'emissions', 'energy-mix'];
```

**Update `C.INPUT_TAB_LABELS`:**
Update to match new tab names. Also update `C.SUB_TAB_LABELS` if needed.

**Update the init sequence** (inside the `dataReady` resolution):
After loading metadata and taxonomy:
1. Call `renderInputsFromTaxonomy(data, taxonomy, metadata)` — builds all fields into `C._renderedSubItems`
2. Call `initSidebar()` — renders the sidebar tree
3. Wire the sidebar callback:
   ```javascript
   window.onSubItemSelected = function(sectionId, subItemId) {
     renderSubItemContent(subItemId);
   };
   ```
4. Render the first sub-item: `renderSubItemContent('technology')` (or whatever `initSidebar` selected)

**Remove old tab-switching code:**
- Remove event listeners on `.tab-button` elements (they no longer exist)
- Remove `switchInputTab()` or similar tab-switching functions
- Remove references to `#tab-buttons`, `#tab-contents`, `#tabs-container` (these DOM elements no longer exist)
- Keep `C.activeTabIndex` if it's still used elsewhere, or replace with `C._currentSubItemId`

**Wire Inputs/Results toggle to sidebar:**
The `.main-tab-button` click handlers should call `switchSidebarView`:
```javascript
// Inputs tab click
switchSidebarView('inputs');
// Results tab click  
switchSidebarView('results');
```

**Keep auto-calculate:**
The auto-calculate function (`autoCalculate` or similar) must still work. It calls `collectJsonData()` to gather all inputs, sends to `/api/ctcc/calculate`, and renders results. The key change: before calling `collectJsonData()`, serialize the current sub-item's visible fields into `C.ctccJsonData`.

**Keep save dialog:**
The save dialog calls `collectJsonData()` — same serialization requirement.

## Constraints

- This is the most complex task. Take time to understand the existing code before making changes.
- Do NOT rewrite `renderInputsFromTaxonomy` from scratch — refactor it. The field creation code (creating inputs, selects, toggles, attaching event listeners, setting data-path attributes, etc.) must be preserved exactly.
- The existing post-render transforms are complex and rely on specific DOM element IDs. They should continue to work when their elements are present in `#content-panel`.
- `collectJsonData()` must still be able to gather ALL input values (not just the visible sub-item). Use the serialization strategy described above.
- Keep the existing IIFE pattern and `window.X` exports.
- If `input-renderer.js` is too large to modify safely, focus on the minimal changes: (1) stop creating tab buttons, (2) group by sub_tab into `C._renderedSubItems`, (3) add `renderSubItemContent`. Leave all existing field creation and transform code intact.
- If you get stuck on the complexity of `input-renderer.js`, report NEEDS_CONTEXT or BLOCKED rather than guessing.

## Verification

After implementation:
1. Load `/app/workspace` in browser
2. Sidebar should render with 10 sections
3. Clicking a sub-item should show its fields in the content area
4. Editing a field, switching to another sub-item, and switching back should preserve the edited value
5. Auto-calculate should fire when inputs change
6. No console errors (except possibly from results-renderer.js which is Task 5)

## Commit
`feat(workspace): wire sidebar navigation to taxonomy-driven field rendering`

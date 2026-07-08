# Task 3: Sidebar Tree Module (`sidebar.js`)

## Files
- Create: `repos/ctcc/server/static/sidebar.js`

## Context

This is Task 3 of 9. Task 1 updated metadata with new `input_tab` values (10 tabs). Task 2 added the HTML shell: a `.sidebar` div with `#sidebar-tree` container and a `.content-area` div with `#content-header` and `#content-panel`. This task creates the sidebar.js module that renders the interactive tree into `#sidebar-tree`.

The sidebar shows 10 sections for the Inputs view and 3 sections for the Results view. Each section has sub-items. Clicking a sub-item calls a callback (`window.onSubItemSelected`) that later tasks will wire to render fields.

## Interfaces

### Consumed
- `window.CTCC.inputMetadata` — array of field metadata objects, each with `input_tab` (string) and `sub_tab` (string|null) properties. Available after workspace.js loads metadata from `/api/input_metadata`. Used to compute field counts per section.

### Produced (all exported via `window.X`)
- `window.SIDEBAR_SECTIONS` — object with keys `inputs` and `results`, each an array of section objects (see structure below)
- `window.initSidebar()` — builds sidebar tree for the `inputs` view, renders into `#sidebar-tree`, expands first section, selects first sub-item, calls `onSubItemSelected`
- `window.navigateToSubItem(sectionId, subItemId)` — programmatically navigate: expand the section, set the sub-item as active, call `onSubItemSelected`
- `window.switchSidebarView(view)` — `'inputs'` or `'results'`. Rebuilds sidebar tree for the selected view. Updates Inputs/Results main-tab-button active states (finds them via `document.querySelectorAll('.main-tab-button')`). Expands first section, selects first sub-item.
- `window.getCurrentSubItem()` — returns `{ sectionId: string, subItemId: string }` for the currently active selection
- `window.onSubItemSelected` — callback property. Set by workspace.js. Called with `(sectionId, subItemId)` when user clicks a sub-item. Initially null.

## Behavior Spec

### `SIDEBAR_SECTIONS` structure

```javascript
var SIDEBAR_SECTIONS = {
  inputs: [
    { id: 'project-identity', label: 'Project Identity', color: '#3b82f6',
      subItems: [
        { id: 'technology', label: 'Technology' },
        { id: 'timeline', label: 'Timeline' }
      ]
    },
    { id: 'equipment', label: 'Equipment', color: '#6366f1',
      subItems: [
        { id: 'conductor-details', label: 'Conductors' },
        { id: 'converter-details', label: 'Converters' }
      ]
    },
    { id: 'routing', label: 'Routing & Terrain', color: '#0891b2',
      subItems: [
        { id: 'terrain-mix', label: 'Terrain Mix' },
        { id: 'rights-of-way', label: 'Rights of Way' }
      ]
    },
    { id: 'benefits', label: 'Benefits', color: '#10b981',
      subItems: [
        { id: 'economic-details', label: 'Economic Details' },
        { id: 'system-constraints', label: 'System Constraints' }
      ]
    },
    { id: 'financial', label: 'Financial', color: '#f59e0b',
      subItems: [
        { id: 'rates', label: 'Rates & Discounting' },
        { id: 'afudc', label: 'AFUDC' }
      ]
    },
    { id: 'capital-costs', label: 'Capital Costs', color: '#ef4444',
      subItems: [
        { id: 'conductor', label: 'Contingencies' },
        { id: 'base-mitigation', label: 'Base Mitigation' },
        { id: 'credits', label: 'Credits' }
      ]
    },
    { id: 'operating', label: 'Operating Costs', color: '#f97316',
      subItems: [
        { id: 'operational-insurance', label: 'Insurance' },
        { id: 'vegetation-management', label: 'Vegetation Mgmt' },
        { id: 'delay-costs', label: 'Delay Costs' }
      ]
    },
    { id: 'risk', label: 'Risk', color: '#a855f7',
      subItems: [
        { id: 'wildfire-risk', label: 'Wildfire' },
        { id: 'outage-risk', label: 'Outage' }
      ]
    },
    { id: 'emissions', label: 'Emissions', color: '#14b8a6',
      subItems: [
        { id: 'energy-emissions-emissions', label: 'Emissions & Intensities' }
      ]
    },
    { id: 'energy-mix', label: 'Energy Mix', color: '#06b6d4',
      subItems: [
        { id: 'energy-emissions-energy', label: 'Energy Source Mix' }
      ]
    }
  ],
  results: [
    { id: 'r-summary', label: 'Summary', color: '#10b981',
      subItems: [
        { id: 'r-overview', label: 'Overview' },
        { id: 'r-bcr', label: 'BCR Analysis' }
      ]
    },
    { id: 'r-costs', label: 'Costs', color: '#ef4444',
      subItems: [
        { id: 'r-capital', label: 'Capital' },
        { id: 'r-operational', label: 'Operational' },
        { id: 'r-risk-costs', label: 'Risk Costs' },
        { id: 'r-emissions-costs', label: 'Emissions' }
      ]
    },
    { id: 'r-benefits', label: 'Benefits', color: '#3b82f6',
      subItems: [
        { id: 'r-congestion', label: 'Congestion' },
        { id: 'r-curtailment', label: 'Curtailment' },
        { id: 'r-loss-comp', label: 'Loss Compensation' },
        { id: 'r-remedial', label: 'Remedial Actions' }
      ]
    }
  ]
};
```

Note: The sub-item `id` values for inputs match the `sub_tab` values in `input_metadata.py`. For Capital Costs, the sub-item IDs are `conductor` (contingencies section), `base-mitigation`, and `credits` — these match the `sub_tab` values in the metadata. Verify against the actual metadata if unsure.

### Field counts
- Computed dynamically from `C.inputMetadata` (if available) by counting fields where `input_tab === section.id`.
- If `C.inputMetadata` is not yet loaded (null/undefined), show no counts.
- Counts display as small grey text on each section header.
- Results sections show no field counts.

### Rendering
- `renderSidebarTree(sections)` — internal function. Builds HTML into `#sidebar-tree`:
  - For each section: a `.sidebar-section` div containing:
    - `.sidebar-section-header` with: `.sidebar-chevron` (▶), `.sidebar-dot` (colored circle, `style="background:${color}"`), label text, `.sidebar-count` (field count)
    - `.sidebar-subitems` div with `.sidebar-subitem` for each sub-item
  - Section header click: toggle `.open` class on the `.sidebar-section` div
  - Sub-item click: set active state, call `onSubItemSelected`

### Active state
- Only one sub-item active at a time.
- Active sub-item: add `.active` class to the `.sidebar-subitem` element.
- Active section: add `.section-active` class to the `.sidebar-section-header` of the parent section.
- On sub-item change: remove `.active` from previous sub-item, remove `.section-active` from previous section header, add to new ones.

### View switching
- `switchSidebarView('inputs')`: render inputs sections, update main-tab-button states (first button active, second not), select first sub-item.
- `switchSidebarView('results')`: render results sections, update main-tab-button states (second button active, first not), select first sub-item.
- Main-tab-button active state: find buttons via `.main-tab-button` class. First button = Inputs, second = Results. Toggle `.active` class. For Results, also add `.results-mode` class to the button.

### Content header
- When a sub-item is selected, update `#content-header` innerHTML:
  ```html
  <span class="sidebar-dot" style="background:${sectionColor};width:10px;height:10px;"></span>
  <h2>${subItemLabel}</h2>
  <span class="breadcrumb">${sectionLabel} → ${subItemLabel}</span>
  ```

## Constraints
- IIFE pattern: `(function() { 'use strict'; ... })();`
- Export via `window.X = X;` at the bottom
- Do NOT access `#demo-form`, `#content-panel`, or any input fields — sidebar.js is pure navigation
- Do NOT import/require anything — all dependencies accessed via `window.CTCC` or `window.X`
- The `identity` sub-tab fields (in project-identity) should NOT appear as a sub-item since scenario naming is handled by the wizard. Only `technology` and `timeline` are sub-items for project-identity.
- Keep the file under 300 lines

## Verification
- Create the file, then load `/app/workspace` in a browser
- Expected: sidebar tree renders with 10 sections (if `C.inputMetadata` is available) or just the section structure (if not)
- Clicking section headers should expand/collapse
- Clicking sub-items should update the content header and call `onSubItemSelected` (which is null initially — no crash, just a no-op check)
- No console errors from sidebar.js itself (workspace.js errors from removed DOM elements are expected until Task 4)

## Commit
`feat(sidebar): add sidebar tree module with navigation and view switching`

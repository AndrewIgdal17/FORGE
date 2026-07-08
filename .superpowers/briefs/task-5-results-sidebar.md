# Task 5: Results Sidebar View

## Files
- Modify: `repos/ctcc/server/static/results-renderer.js` (~1431 lines)
- Modify: `repos/ctcc/server/static/workspace.js`

## Context

Task 5 of 9. Tasks 1-4 built the sidebar navigation for the Inputs view. Now the Results view needs the same treatment — when the user clicks the "Results" main-tab-button, the sidebar should switch to show results sections (Summary, Costs, Benefits) and clicking a results sub-item should render that section's results in the content area.

Currently, results render into `#main-tab-results > #result`. The Results main-tab-button shows/hides `#main-tab-results`. Task 4 already wires `switchMainTab` to call `switchSidebarView()`.

The sidebar.js module (Task 3) already has `SIDEBAR_SECTIONS.results` defined with 3 sections and sub-items. `switchSidebarView('results')` renders those sections in the sidebar.

Read `repos/ctcc/server/static/results-renderer.js` to understand how results are currently rendered — look for the main render functions and how they target `#result` or `#main-tab-results`.

Also read `repos/ctcc/server/static/sidebar.js` to see the results section structure.

## Interfaces

### Consumed
- `window.switchSidebarView('results')` — from sidebar.js
- `window.onSubItemSelected` — callback from sidebar.js (already wired in workspace.js)
- Results data from `C.lastResults` or similar (check workspace.js for how results are stored after API response)

### Produced
- `window.renderResultsSubItem(subItemId)` — renders the selected results section into `#content-panel`

## Behavior Spec

### workspace.js changes

The `onSubItemSelected` callback currently always calls `renderSubItemContent(subItemId)` (for input fields). When the sidebar view is `results`, it should call `renderResultsSubItem(subItemId)` instead.

Update the callback to check the current view:
```
window.onSubItemSelected = function(sectionId, subItemId) {
  if (subItemId.startsWith('r-')) {
    renderResultsSubItem(subItemId);
  } else {
    renderSubItemContent(subItemId);
  }
};
```

The Results main-tab-button click should:
1. Call `switchSidebarView('results')`
2. Show the results content (hide `#main-tab-inputs`, show results in `#content-panel`)

The Inputs main-tab-button click should:
1. Call `switchSidebarView('inputs')`
2. Show the inputs content

Note: Task 4 already wired `switchMainTab` → `switchSidebarView`. Check how the existing Inputs/Results toggle works and whether `#main-tab-inputs` / `#main-tab-results` visibility toggling is still in place. The sidebar approach means BOTH views render into `#content-panel` (which lives inside `#main-tab-inputs`). The old `#main-tab-results` div may no longer be needed.

### results-renderer.js changes

**Add `renderResultsSubItem(subItemId)`** function that maps sub-item IDs to existing render logic:

| Sub-item ID | What to render |
|-------------|---------------|
| `r-overview` | Summary/overview panel — total costs PV, total benefits PV, key metrics |
| `r-bcr` | BCR analysis — all BCR variants, sensitivity exclusions |
| `r-capital` | Capital costs breakdown |
| `r-operational` | Operational costs breakdown |
| `r-risk-costs` | Risk costs (wildfire + outage) |
| `r-emissions-costs` | Emissions costs |
| `r-congestion` | Congestion benefits |
| `r-curtailment` | Curtailment benefits |
| `r-loss-comp` | Loss compensation benefits |
| `r-remedial` | Remedial actions benefits |

The existing `results-renderer.js` already has rendering logic for all these sections — it currently renders them all into `#result` as one long page. The refactor needs to extract each section's rendering into a callable unit.

**Approach:** The simplest approach is:
1. Keep the existing full render function that builds all results HTML
2. `renderResultsSubItem` renders the full results into a hidden container, then extracts and shows only the relevant section
3. OR: refactor the existing renderer to have per-section render functions

Choose whichever is simpler and less risky for a 1400-line file you're modifying.

**Content header:** When rendering a results sub-item, update `#content-header` with the results section's color dot, title, and breadcrumb (same pattern as inputs). The sidebar.js `SIDEBAR_SECTIONS.results` has the color and label for each section.

### Handling "no results yet"

If no results are available (no calculation has been run), `renderResultsSubItem` should show a message: "No results available. Edit inputs and calculate first." with a link or button to switch back to Inputs view.

## Constraints
- Keep existing results rendering logic intact — do not rewrite the renderer
- The existing `#result` pre element and `#main-tab-results` div may become dead code after this task — that's fine, leave cleanup for Task 8
- If the results renderer is too complex to refactor per-section, a simpler approach: render all results into an offscreen container, then query sections by class/ID and move the relevant one into `#content-panel`
- IIFE pattern, window exports

## Verification
1. Load workspace, edit some inputs, trigger auto-calculate
2. Click "Results" main-tab-button → sidebar switches to results sections
3. Click "Overview" → shows summary with total costs/benefits
4. Click "BCR Analysis" → shows BCR cards
5. Click "Capital" under Costs → shows capital cost breakdown
6. Click "Inputs" → switches back to inputs sidebar, fields visible with preserved values

## Commit
`feat(results): add results sidebar view with section-based navigation`

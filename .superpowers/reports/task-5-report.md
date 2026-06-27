---
tags: [project/ctcc]
---

# Task 5 Report: Results Sidebar View

**Status:** DONE  
**Commit:** feat(results): add results sidebar view with section-based navigation  
**Date:** 2026-06-27 16:38

## Changes Made

### `repos/ctcc/server/static/results-renderer.js`

Added 4 new functions and exported 1 via Public API (190 lines added before Public API section):

| Function | Purpose |
|----------|---------|
| `renderCostsBuckets(results, buckets)` | Renders `renderCostsByTaxonomy` filtered to specific cost buckets by temporarily overriding `C.COST_BUCKET_ORDER` |
| `renderBenefitsBucket(results, bucket, subgroup)` | Renders benefits items for a specific bucket, optionally filtered to a subgroup |
| `renderResultsOverview(results)` | Builds the Summary/Overview panel: 4 hero stat cards (Total Costs, Total Benefits, Net Benefit, Societal BCR) + BCR headline cards + Perspectives table |
| `renderResultsBCRPanel(results)` | Renders BCR analysis: headline cards + Societal BCR with Exclusions + Custom Societal BCR |
| `renderResultsSubItem(subItemId)` | Main dispatcher — clears `#content-panel`, checks for `C.latestValidResults`, then routes each `r-*` subItemId to the appropriate render function. Shows a "No results available" message with "Go to Inputs" button when no results exist. |

**Sub-item → render mapping:**

| Sub-item ID | Render call |
|-------------|-------------|
| `r-overview` | `renderResultsOverview(results)` |
| `r-bcr` | `renderResultsBCRPanel(results)` |
| `r-capital` | `renderCostsBuckets(results, ['hard'])` |
| `r-operational` | `renderCostsBuckets(results, ['soft'])` |
| `r-risk-costs` | `renderCostsBuckets(results, ['risk'])` |
| `r-emissions-costs` | `renderCostsBuckets(results, ['emissions'])` |
| `r-remedial` | `renderBenefitsBucket(results, 'remedial')` |
| `r-congestion` | `renderBenefitsBucket(results, 'remedial', 'congestion')` |
| `r-curtailment` | `renderBenefitsBucket(results, 'remedial', 'curtailment')` |
| `r-loss-comp` | `renderBenefitsBucket(results, 'enabling')` |

### `repos/ctcc/server/static/workspace.js`

**`onSubItemSelected` callback** — updated to route `r-*` prefixed sub-items to `renderResultsSubItem` and all others to `renderSubItemContent`:
```javascript
window.onSubItemSelected = function(sectionId, subItemId) {
  if (subItemId && subItemId.startsWith('r-')) {
    window.renderResultsSubItem(subItemId);
  } else {
    window.renderSubItemContent(subItemId);
  }
};
```

**`switchMainTab` function** — updated to always keep `#main-tab-inputs` active. Both inputs and results views render into `#content-panel` which lives inside `#main-tab-inputs`. `#main-tab-results` (the legacy `<pre id="result">` container) is kept hidden. The `switchSidebarView` call (already wired in Task 4) handles switching between inputs and results sections in the sidebar.

## Taxonomy mapping rationale

- `r-loss-comp` maps to the `enabling` bucket (taxonomy item `delivered_energy_benefit`) — not to the cost-side `emissions_comp`. The enabling bucket represents energy delivery benefits that compensate for line losses, which aligns with "Loss Compensation" in the sidebar label.
- `r-congestion` and `r-curtailment` are filtered from the `remedial` bucket by subgroup name, giving users per-category views.
- `r-remedial` shows all remedial benefits (congestion + curtailment) together.

## Constraints honored

- Existing `renderCTCCResults` and all existing render functions are unchanged.
- `#main-tab-results` and `<pre id="result">` are left in the DOM (dead code cleanup deferred to Task 8).
- IIFE pattern preserved; `renderResultsSubItem` added to Public API exports.

## Verification steps

1. Load workspace → sidebar shows Inputs view (unchanged)
2. Edit inputs, trigger auto-calculate
3. Click "Results" button → sidebar switches to results sections (Summary, Costs, Benefits)
4. Click "Overview" → #content-panel shows 4 stat cards + BCR cards + Perspectives table
5. Click "BCR Analysis" → BCR headline + sensitivity tables
6. Click "Capital" (under Costs) → Hard Costs breakdown
7. Click "Operational" → Soft Costs breakdown
8. Click "Congestion" (under Benefits) → Congestion benefits
9. Click "Inputs" → sidebar switches back to inputs, form fields visible

## No concerns

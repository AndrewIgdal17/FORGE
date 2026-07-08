# Task 6: ROW Zones Table

## Files
- Modify: `repos/ctcc/server/static/input-renderer.js`
- Possibly modify: `repos/ctcc/server/static/styles.css` (if extra table styles needed)

## Context

Task 6 of 9. The sidebar navigation is now working for both Inputs and Results views. This task replaces the 15 × 4 = 60 individual ROW (Rights of Way) zone fields with an editable table/grid UI.

Currently, when the user navigates to sidebar sub-item `rights-of-way` (under the `routing` section), the content panel shows 15 zone groups, each with 4 fields (Miles, Acquisition Cost, Rent Cost, Width). This is rendered from `C._renderedSubItems['rights-of-way']` which was built by `renderInputsFromTaxonomy` from the metadata.

The goal is to replace those 60 individual field rows with a compact table where rows = zones and columns = the 4 field types.

Read `repos/ctcc/server/static/input-renderer.js` — specifically search for how the `rights-of-way` sub-item fields are currently rendered. Also check `repos/ctcc/scripts/input_metadata.py` to see the exact field IDs and `field_path` values for ROW zone fields.

## Interfaces

### Produced
- `renderROWZonesTable(container, data)` — function that creates the editable table and replaces the default field rendering for the `rights-of-way` sub-item

## Behavior Spec

### Table structure

```
┌───────┬────────────┬──────────────────┬──────────────┬───────────┐
│ Zone  │ Miles      │ Acquisition $/mi │ Rent $/mi/yr │ Width ft  │
├───────┼────────────┼──────────────────┼──────────────┼───────────┤
│ 1     │ [  120   ] │ [   45,000    ]  │ [  2,500  ]  │ [  150 ]  │
│ 2     │ [   80   ] │ [   62,000    ]  │ [  3,100  ]  │ [  200 ]  │
│ 3     │ [   50   ] │ [   38,000    ]  │ [  1,800  ]  │ [  125 ]  │
├───────┼────────────┼──────────────────┼──────────────┼───────────┤
│ Total │ [  250   ] │                  │              │           │
└───────┴────────────┴──────────────────┴──────────────┴───────────┘
[ + Add Zone ]  [ − Remove Last ]
```

### Field paths

Check the actual `field_path` values in `input_metadata.py` for ROW zone fields. They follow the pattern:
- `rights_of_way.zone_N.miles` (or similar)
- `rights_of_way.zone_N.acquisition_cost_per_mile`
- `rights_of_way.zone_N.rent_per_mile`
- `rights_of_way.zone_N.width_ft`

Where N is 1-15. Verify the exact paths by reading the metadata file.

Each table cell input must have the correct `data-path` attribute matching these paths, so `collectJsonData()` can still gather all values.

### Integration with renderSubItemContent

When `renderSubItemContent('rights-of-way')` is called, instead of showing the default pre-built field groups (60 individual fields), call `renderROWZonesTable` to build the table view.

The simplest approach: add a check in `renderSubItemContent`:
```javascript
if (subItemId === 'rights-of-way') {
  renderROWZonesTable(contentPanel, C.ctccJsonData);
  return;
}
```

Or: modify the build phase in `renderInputsFromTaxonomy` to build the table when processing `rights-of-way` fields instead of individual field rows.

### "Project Uses Existing ROW" toggle

There is 1 field with `sub_tab="rights-of-way"` that is NOT a zone field — it's the "Project Uses Existing ROW" boolean toggle. This should render ABOVE the table as a standalone toggle field. Check its field_path in the metadata.

### Dynamic zone count

- Start with zones that have data in the current scenario (or 3 zones as default for new scenarios)
- "Add Zone" button adds a row (up to 15 max)
- "Remove Last" button removes the last row (minimum 1 row)
- Adding/removing rows should create/destroy the corresponding `data-path` inputs

### Running total

The "Total" row shows the sum of the Miles column. It updates live as the user edits zone miles. Use a readonly input or span for the total.

### Auto-calculate

Table cell inputs should trigger auto-calculate on change, same as regular fields. Attach the same debounced change handler.

## Constraints

- Use existing `.ctcc-table` CSS class for the table (already in styles.css)
- All cell inputs must have `data-path` attributes so `collectJsonData()` works
- Currency inputs should use the same formatting (comma-separated, right-aligned monospace) as other currency fields in the app
- Keep the table compact — monospace font, right-aligned numbers, narrow cells

## Verification

1. Navigate to Routing & Terrain → Rights of Way in the sidebar
2. Should see the toggle + table (not 60 individual fields)
3. Edit a Miles value → Total updates, auto-calculate fires
4. Add Zone → new row appears with empty fields
5. Remove Last → row disappears
6. Switch to another sub-item and back → values preserved

## Commit
`feat(routing): render ROW zones as editable table instead of individual fields`

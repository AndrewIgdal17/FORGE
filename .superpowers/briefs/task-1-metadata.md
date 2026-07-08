# Task 1: Metadata — Split and Merge `input_tab` Values

## Files
- Modify: `repos/ctcc/scripts/input_metadata.py`

## Context
The CTCC web app input form is being redesigned from horizontal tab navigation to a sidebar tree. The server-side metadata file `input_metadata.py` defines 343 input fields, each with an `input_tab` attribute that determines which tab the field appears on. The current 8 tabs need to be reorganized into 10 sidebar sections via 3 splits and 1 merge.

The file uses Python dataclasses. Fields are defined as `InputField` instances in lists `_TAB1` through `_TAB9` (though some TAB numbers may not match the tab count — check the actual variable names). Each field has `input_tab` and `sub_tab` attributes.

## Interfaces
- No new functions or classes needed.
- The existing `INPUT_METADATA` dict (keyed by field ID) and `input_metadata_to_dict()` function remain unchanged in signature.

## Behavior Spec

Apply these transformations to the `input_tab` field on affected entries:

1. **Split `project-technical` into 3 new tabs:**
   - Fields with `input_tab="project-technical"` AND `sub_tab` in `("identity", "technology", "timeline")` → change `input_tab` to `"project-identity"`
   - Fields with `input_tab="project-technical"` AND `sub_tab` in `("conductor-details", "converter-details")` → change `input_tab` to `"equipment"`
   - Fields with `input_tab="project-technical"` AND `sub_tab` in `("terrain-mix", "rights-of-way")` → change `input_tab` to `"routing"`
   - After these 3 splits, **no fields should remain** with `input_tab="project-technical"` — all 98 must be redistributed.

2. **Merge `delay-costs` into `operating`:**
   - Fields with `input_tab="delay-costs"` (8 fields) → change `input_tab` to `"operating"` and set `sub_tab="delay-costs"` (so they group as a sub-item in the sidebar)
   - Fields with `input_tab="operational"` (40 fields) → change `input_tab` to `"operating"` (keep existing `sub_tab` values unchanged)
   - After this merge, both old tab names (`delay-costs` and `operational`) are gone, replaced by `operating`.

3. **Split `emissions` into 2 tabs:**
   - Fields with `input_tab="emissions"` AND `sub_tab="energy-emissions-energy"` (32 fields) → change `input_tab` to `"energy-mix"`
   - Fields with `input_tab="emissions"` AND `sub_tab="energy-emissions-emissions"` (29 fields) → **keep** `input_tab="emissions"` (no change needed)

Also update the comment headers in the file (e.g., `# Tab 1 — Project`) to reflect the new tab names and counts.

## Verification

Run from workspace root:
```
cd repos/ctcc && python scripts/input_metadata.py
```

Expected output should show 10 tabs:
- `benefits`: ~41 fields
- `capital-costs`: ~41 fields
- `emissions`: ~29 fields
- `energy-mix`: ~32 fields
- `equipment`: ~5 fields
- `financial`: ~35 fields
- `operating`: ~48 fields
- `project-identity`: ~13-14 fields
- `risk`: ~19 fields
- `routing`: ~79 fields

Total: 343 fields (same as before). No duplicate IDs. All taxonomy_id references valid.

## Constraints
- Do NOT change any field's `id`, `taxonomy_id`, `field_path`, `yaml_section`, `label`, `help_text`, `input_type`, `validation`, `display_order`, `section_label`, or `tier`.
- Only change `input_tab` (and `sub_tab` for the delay-costs merge).
- The `_TAB1` through `_TAB9` list variable names can be renamed/reorganized to match the new structure, but all fields must still be included in `_ALL_FIELDS`.
- Keep the file's existing code style (dataclass pattern, `_f()` helper, terrain/fuel loops).

## Commit
`refactor(metadata): split project-technical and emissions tabs, merge delay into operating`

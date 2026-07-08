# Task 7 Report — Field Search (sidebar-search.js)

**Status:** DONE_WITH_CONCERNS

## Commits

- `feat(search): add fuzzy + synonym field search to sidebar` — adds `server/static/sidebar-search.js`

## Summary

Created `sidebar-search.js` (193 lines) implementing:

- **Search index** from `window.CTCC.inputMetadata` with `searchText` = label + help + section label
- **Synonym map** (35 entries) with substring ID matching per spec
- **Fuzzy search** — case-insensitive AND logic across words
- **Synonym expansion** — phrase or word match against synonym keys
- **Dropdown UI** — top 10 results grouped by sidebar section order, section headers + bold labels
- **Navigation** — `navigateToSubItem`, scroll + `.field-highlight` (1.5s)
- **Keyboard/mouse** — Escape clears, Arrow Up/Down + Enter, click-outside closes
- **Inputs-only guard** — skips search when Results tab is active
- **Export** — `window.initSidebarSearch()` (Task 8 will wire from `workspace.js`)

## Verification (static / metadata)

| Query | Expected | Result |
|-------|----------|--------|
| `discount` | WACC, Social Discount Rate | Synonym hits `wacc_nominal`, `social_discount_rate` (included in index; fields are `always_hidden` in form) |
| `wire` | Conductor fields | Synonym hits `conductor_type`, `old_conductor_type` |
| `voltage` | Voltage field | **No metadata field** — `voltage_kv` is a read-only derived display in `input-renderer.js`, not in `input_metadata.py` |

## Concerns

1. **`voltage` verification gap** — No searchable metadata entry for voltage; synonym target `voltage_kv` matches zero field IDs. Fuzzy search also finds nothing. Voltage display is read-only DOM in the Technology sub-item, outside the metadata-driven index.
2. **`initSidebarSearch()` not yet called** — Per task constraints, `workspace.js` wiring deferred to Task 8. Script tag already present in `workspace.html`.
3. **Hidden fields searchable** — `wacc_nominal` and `social_discount_rate` are `always_hidden` in metadata but included in search so synonym/fuzzy can find them; highlight may fail if the field is not rendered in the active sub-item DOM.
4. **Some synonym targets have no ID match** — e.g. `utility_discount_rate`, `greenfield_or_reconductoring`, `terrain_forested` (actual IDs use patterns like `terrain_miles_forested`). Substring matching partially compensates; multi-word terrain synonyms may miss unless fuzzy text matches.

## Files

- Created: `server/static/sidebar-search.js`

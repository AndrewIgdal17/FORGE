# Task 2: Sidebar HTML Shell + CSS

## Files
- Modify: `repos/ctcc/server/static/workspace.html`
- Modify: `repos/ctcc/server/static/styles.css`

## Context

This is the second task in a 9-task plan to add sidebar tree navigation to the CTCC workspace. Task 1 (already complete) updated the server-side metadata. This task adds the HTML structure and CSS styles for the sidebar + content area layout. The sidebar tree will be populated dynamically by `sidebar.js` (Task 3) — this task just creates the container elements.

The workspace page currently has:
- A top nav bar (`.app-top-nav`) — KEEP unchanged
- Main tab buttons (Inputs | Results | Save) in `.main-tabs` — KEEP unchanged
- A status bar (`#status-bar`) — KEEP unchanged
- Inside `#main-tab-inputs`: a `<form id="demo-form">` wrapping `#ctcc-section > #ctcc-json-inputs > #tabs-container` with `#tab-buttons` and `#tab-contents` — this is what gets replaced

Read `repos/ctcc/server/static/workspace.html` and `repos/ctcc/server/static/styles.css` before making changes.

## Behavior Spec

### workspace.html changes

**Replace** the region inside `#main-tab-inputs` (from `<form id="demo-form">` through `</form>`) with:

```
<form id="demo-form" novalidate>
  <div class="workspace-layout">
    <div class="sidebar" id="sidebar">
      <div class="sidebar-search">
        <input type="text" id="sidebar-search-input" placeholder="Search fields...">
      </div>
      <div id="sidebar-tree"></div>
    </div>
    <div class="content-area">
      <div class="content-header" id="content-header"></div>
      <div id="content-panel">
        <p id="load-status" style="margin: 0; font-size: 0.9rem; flex-shrink: 0;"></p>
      </div>
    </div>
  </div>
</form>
```

Key points:
- `#demo-form` wraps everything (so `collectJsonData` still finds all inputs within the form)
- `.workspace-layout` is the flex container
- `.sidebar` is the left panel (260px)
- `#sidebar-tree` is where sidebar.js will render the tree
- `.content-area` is the right panel
- `#content-header` is where the breadcrumb/title goes
- `#content-panel` is where field rendering goes
- Keep `#load-status` inside `#content-panel` — it's used during initial data loading

**Remove** the old `#ctcc-section` and `#ctcc-json-inputs` wrapper divs. Remove `#tabs-container`, `#tab-buttons`, `#tab-contents`.

**Add script tags** for the new modules. Insert these two lines after the `scenario-workspace.js` script tag and before `wizard.js`:
```html
<script src="/static/sidebar.js"></script>
<script src="/static/sidebar-search.js"></script>
```

Note: `sidebar.js` and `sidebar-search.js` don't exist yet (Tasks 3 and 7). That's fine — the HTML just references them. The page will work without them (empty sidebar, content area shows load status).

### styles.css changes

**Add** the following CSS rules (add them in a new section, e.g., after the `.save-overlay` styles and before any responsive media queries):

Sidebar layout:
- `.workspace-layout` — `display: flex; height: calc(100vh - 140px);` (140px = nav + main-tabs + status-bar, approximately — verify by checking the actual heights). `overflow: hidden;`
- `.sidebar` — `width: 260px; min-width: 260px; background: white; border-right: 1px solid rgba(0,0,0,0.08); overflow-y: auto; padding-bottom: 1rem;`
- `.content-area` — `flex: 1; overflow-y: auto; padding: 1.5rem 2rem;`

Sidebar search:
- `.sidebar-search` — `padding: 0.75rem; border-bottom: 1px solid rgba(0,0,0,0.06); position: sticky; top: 0; background: white; z-index: 1;`
- `.sidebar-search input` — `width: 100%; padding: 0.4rem 0.6rem; border: 1px solid rgba(0,0,0,0.12); border-radius: 6px; font-size: 0.8rem; font-family: inherit; background: rgba(0,100,200,0.03);` Focus state: `outline: none; border-color: #0066cc;`

Sidebar sections:
- `.sidebar-section` — `border-bottom: 1px solid rgba(0,0,0,0.04);`
- `.sidebar-section-header` — `display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; cursor: pointer; font-weight: 600; font-size: 0.8rem; color: #333; user-select: none;`
- `.sidebar-section-header:hover` — `background: rgba(0,100,200,0.04);`
- `.sidebar-section-header.section-active` — `background: rgba(0,100,200,0.05);`
- `.sidebar-chevron` — `font-size: 0.6rem; color: #999; width: 12px; text-align: center; transition: transform 0.15s;`
- `.sidebar-section.open .sidebar-chevron` — `transform: rotate(90deg);`
- `.sidebar-dot` — `width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;` (background color set inline per section)
- `.sidebar-count` — `margin-left: auto; font-size: 0.7rem; color: #aaa; font-weight: 400;`

Sidebar sub-items:
- `.sidebar-subitems` — `display: none; margin-left: 1.75rem; border-left: 1px solid rgba(0,0,0,0.06);`
- `.sidebar-section.open .sidebar-subitems` — `display: block;`
- `.sidebar-subitem` — `padding: 0.3rem 0.75rem; cursor: pointer; font-size: 0.78rem; color: #666;`
- `.sidebar-subitem:hover` — `background: rgba(0,100,200,0.05); color: #0066cc;`
- `.sidebar-subitem.active` — `color: #0066cc; font-weight: 600; background: rgba(0,100,200,0.08);`

Content area:
- `.content-header` — `display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 2px solid rgba(0,100,200,0.15);`
- `.content-header h2` — `font-size: 1.1rem; color: #333; margin: 0;`
- `.content-header .breadcrumb` — `font-size: 0.75rem; color: #999;`

Search dropdown (for Task 7 — add now for completeness):
- `.search-dropdown` — `position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid rgba(0,0,0,0.12); border-radius: 0 0 6px 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-height: 300px; overflow-y: auto; z-index: 10; display: none;`
- `.search-dropdown.open` — `display: block;`
- `.search-result` — `padding: 0.4rem 0.75rem; cursor: pointer; font-size: 0.8rem;`
- `.search-result:hover` — `background: rgba(0,100,200,0.05);`
- `.search-result .search-result-section` — `font-size: 0.7rem; color: #999;`

Field highlight (for search navigation):
- `.field-highlight` — `background: rgba(250, 204, 21, 0.3); transition: background 1.5s ease;`

**Do NOT remove** the existing `.tab-button`, `.tab-content`, etc. CSS yet — that's Task 8 (dead code removal). The old CSS won't cause problems since the old HTML elements are gone.

## Constraints
- Do NOT modify the top nav bar, main-tabs, status bar, save overlay, or results tab HTML.
- Do NOT modify any JS files in this task.
- The `<form id="demo-form">` MUST wrap the `.workspace-layout` div — `collectJsonData()` finds inputs by querying inside this form.
- Keep the existing `#main-tab-results` div unchanged (the Results tab content area stays as-is for now — Task 5 will integrate it with the sidebar).
- Make `.sidebar-search` position relative (not the input) so the search dropdown positions correctly relative to the search container.

## Verification
- Open `/app/workspace` in a browser
- The page should load without JS errors (sidebar will be empty since sidebar.js doesn't exist yet)
- The layout should show: empty sidebar (260px left) + content area (right) with just the load-status paragraph
- The search input should be visible and styled at the top of the sidebar
- The status bar and main tab buttons should still be visible above the sidebar

## Commit
`feat(workspace): add sidebar + content area HTML shell and CSS`

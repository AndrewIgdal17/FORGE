var TOUR_STEPS = {
  home: [
    {
      target: '.app-top-nav',
      title: 'Top Navigation',
      body: 'This bar stays visible on every page so you can move between Home, Workspace, and Scenarios at any time.',
      position: 'bottom'
    },
    {
      target: '.app-top-nav-logo',
      title: 'CTCC Logo',
      body: 'Click the logo anytime to return to this Home page from anywhere in the app.',
      position: 'bottom'
    },
    {
      target: '.app-top-nav-links',
      title: 'Page Links',
      body: 'Use these links to switch between Home, Workspace, and Scenarios. The active page is highlighted.',
      position: 'bottom'
    },
    {
      target: '.app-top-nav-link[data-nav="home"]',
      title: 'Home Link',
      body: 'You are on Home now \u2014 the starting point for creating scenarios and launching the guided tour.',
      position: 'bottom'
    },
    {
      target: '.app-top-nav-link[data-nav="scenarios"]',
      title: 'Scenarios Link',
      body: 'Jump to Scenarios to upload files, duplicate runs, and compare alternatives side by side.',
      position: 'bottom'
    },
    {
      target: '.ctcc-user-display',
      title: 'Your Account',
      body: 'Your signed-in username appears here so you always know which account your scenarios belong to.',
      position: 'left'
    },
    {
      target: '.app-top-nav-logout',
      title: 'Log Out',
      body: 'Sign out of CTCC when you are done. Your saved scenarios remain in the database for next time.',
      position: 'left'
    },
    {
      target: '.landing-title',
      title: 'Welcome',
      body: 'This is the CTCC landing page \u2014 your hub for starting new transmission cost analyses.',
      position: 'bottom'
    },
    {
      target: '.landing-name',
      title: 'Full Name',
      body: 'CTCC stands for Comprehensive Transmission Cost Calculator, a full-cost benefit-cost tool for transmission projects.',
      position: 'bottom'
    },
    {
      target: '.landing-tagline',
      title: 'What It Does',
      body: 'CTCC helps you evaluate transmission investments with societal benefit-cost ratios and detailed cost breakdowns.',
      position: 'bottom'
    },
    {
      target: '#landing-new-scenario-btn',
      title: 'New Scenario',
      body: 'Start a fresh transmission scenario in the Workspace. A guided wizard walks you through the key project choices first.',
      tip: 'The wizard pre-fills inputs so you can refine details in the sidebar afterward.',
      position: 'bottom'
    },
    {
      target: '#landing-load-file-btn',
      title: 'Load from File',
      body: 'Import an existing scenario JSON file instead of building from scratch. You land in Scenarios with the upload dialog open.',
      position: 'bottom'
    },
    {
      target: '#landing-tour-btn',
      title: 'Guided Tour',
      body: 'Restart this orientation tour anytime. It walks through every major part of the app page by page.',
      position: 'bottom'
    },
    {
      target: '#landing-goto-scenarios-btn',
      title: 'Go to Scenarios',
      body: 'Open your saved scenarios list once you have at least one scenario in the database. This button enables automatically after your first save.',
      position: 'top'
    },
    {
      target: '.app-top-nav-link[data-nav="workspace"]',
      title: 'Continue to Workspace',
      body: 'Click here to continue the tour in the Workspace \u2014 where you build and analyze transmission scenarios.',
      position: 'bottom',
      action: { type: 'navigate', url: '/app/workspace' }
    }
  ],
  workspace: [
    {
      target: '#scenario-bar',
      title: 'Scenario Bar',
      body: 'This bar identifies the active scenario and gives you quick access to save, export, and rename actions.',
      position: 'bottom'
    },
    {
      target: '#scenario-name-display',
      title: 'Scenario Name',
      body: 'Click the scenario name anytime to rename it inline. Changes save to the database when you confirm.',
      tip: 'You can also choose Rename from the save dropdown.',
      position: 'bottom'
    },
    {
      target: '#split-save',
      title: 'Save Controls',
      body: 'The split save button saves your work. The chevron opens a menu with export and duplicate options.',
      position: 'bottom'
    },
    {
      target: '#split-save-main',
      title: 'Quick Save',
      body: 'Click Save when you have unsaved changes. When everything is saved, the button shows Saved \u2713 and the modified dot disappears.',
      tip: 'Press \u2318S (Mac) or Ctrl+S (Windows) to save from anywhere on the page.',
      position: 'bottom'
    },
    {
      target: '#split-save-menu',
      title: 'Save Menu',
      body: 'Open this menu for Save as Copy, Rename, Export .ctcc (portable JSON), and Export .csv (human-readable spreadsheet).',
      position: 'bottom',
      action: { type: 'click', target: '#split-save-drop' }
    },
    {
      target: '.view-toggle',
      title: 'View Switcher',
      body: 'Switch between Inputs, Results, and Sensitivity views. Each view changes the sidebar and main content area.',
      position: 'bottom',
      action: { type: 'click', target: '#split-save-drop' }
    },
    {
      target: '.view-toggle-btn[data-view="inputs"]',
      title: 'Inputs View',
      body: 'Build and edit your transmission scenario here. The sidebar lists every input section organized by topic.',
      position: 'bottom'
    },
    {
      target: '.view-toggle-btn[data-view="results"]',
      title: 'Results View',
      body: 'After calculation, switch here to explore benefit-cost ratios, cost breakdowns, and congestion relief.',
      position: 'bottom'
    },
    {
      target: '.view-toggle-btn[data-view="sensitivity"]',
      title: 'Sensitivity View',
      body: 'Sensitivity analysis tools are coming soon \u2014 tornado diagrams, spider plots, and break-even analysis.',
      position: 'bottom'
    },
    {
      target: '#header-breadcrumb',
      title: 'Context Breadcrumb',
      body: 'This line shows where you are in the current view, complementing the section header below the context bar.',
      position: 'bottom'
    },
    {
      target: '#calc-time',
      title: 'Last Calculated',
      body: 'Shows when results were last computed. It reads Not calculated until you run the model with valid inputs.',
      position: 'left'
    },
    {
      target: '#sidebar',
      title: 'Sidebar Navigation',
      body: 'The sidebar organizes inputs and results into collapsible sections. Field counts and validation badges appear on each sub-item.',
      position: 'right'
    },
    {
      target: '#sidebar-search-input',
      title: 'Search Fields',
      body: 'Filter sidebar items by name to jump directly to a specific input group without scrolling.',
      position: 'right'
    },
    {
      target: '.sidebar-section[data-section-id="project-identity"] .sidebar-section-header',
      title: 'Input Sections',
      body: 'Click a section header to expand or collapse its sub-items. Color dots match the section shown in the content header.',
      position: 'right'
    },
    {
      target: '.sidebar-subitem[data-sub-item-id="technology"]',
      title: 'Sub-Items',
      body: 'Click a sub-item to load its fields in the content panel. The active item is highlighted and drives the header above.',
      tip: 'Missing-field badges on sub-items help you find incomplete inputs before calculating.',
      position: 'right'
    },
    {
      target: '#content-header',
      title: 'Content Header',
      body: 'Displays the active sub-item title and breadcrumb trail so you always know which form you are editing.',
      position: 'bottom'
    },
    {
      target: '#content-panel',
      title: 'Content Panel',
      body: 'Input fields and results render here. Edits auto-save into memory and trigger recalculation when inputs change.',
      position: 'top'
    },
    {
      target: '.sidebar-subitem[data-sub-item-id="r-overview"]',
      title: 'Results Navigation',
      body: 'In Results view the sidebar switches to output sections \u2014 Summary, Costs, and Benefits \u2014 each with its own sub-items.',
      position: 'right',
      action: { type: 'click', target: '.view-toggle-btn[data-view="results"]' }
    },
    {
      target: '#sensitivity-panel',
      title: 'Sensitivity Panel',
      body: 'Selecting Sensitivity replaces the workspace with dedicated analysis tools for exploring parameter uncertainty.',
      position: 'top',
      action: { type: 'click', target: '.view-toggle-btn[data-view="sensitivity"]' }
    },
    {
      target: '.app-top-nav-link[data-nav="scenarios"]',
      title: 'Continue to Scenarios',
      body: 'Click here to continue the tour in Scenario Management \u2014 where you compare and organize saved scenarios.',
      position: 'bottom',
      action: { type: 'navigate', url: '/app/scenarios-manager' }
    }
  ],
  scenarios: [
    {
      target: '#scenarios-manager-main',
      title: 'Scenario Manager',
      body: 'This page is your hub for organizing saved scenarios and comparing alternatives side by side.',
      position: 'bottom'
    },
    {
      target: '#scenario-subtabs',
      title: 'Page Tabs',
      body: 'Switch between Manage (your scenario library), Compare (metrics table), and What-If (design tools in Workspace).',
      position: 'bottom'
    },
    {
      target: '.pill-tab[data-scenario-tab="manage"]',
      title: 'Manage Tab',
      body: 'The Manage tab lists every scenario in your account. Upload files, create new runs, and maintain your library here.',
      position: 'bottom'
    },
    {
      target: '.scenario-toolbar',
      title: 'Manage Toolbar',
      body: 'Quick actions live at the top: start a new scenario or import an existing file from disk.',
      position: 'bottom'
    },
    {
      target: '#new-scenario-btn',
      title: 'New Scenario',
      body: 'Opens the Workspace with a fresh scenario so you can build inputs from scratch or use the creation wizard.',
      tip: 'New scenarios are saved to your account once you calculate and save in the Workspace.',
      position: 'bottom'
    },
    {
      target: '#scenario-upload-btn',
      title: 'Load from File',
      body: 'Browse for one or more scenario files (.ctcc portable JSON or .csv spreadsheet). Imported scenarios appear in the list below.',
      tip: 'You can also land here with the upload dialog open via Load from File on the Home page.',
      position: 'bottom'
    },
    {
      target: '#scenario-list',
      title: 'Scenario List',
      body: 'Each row is a saved scenario with name, key parameters, and source metadata. Click a name to rename; use Open, Duplicate, Remove, or Delete from the action buttons.',
      tip: 'Drag the handle at the right edge to reorder scenarios in your list.',
      position: 'top'
    },
    {
      target: '.pill-tab[data-scenario-tab="compare"]',
      title: 'Compare Tab',
      body: 'Switch here to pick scenarios and view benefit-cost metrics in a side-by-side comparison table.',
      position: 'bottom',
      action: { type: 'click', target: '.pill-tab[data-scenario-tab="compare"]' }
    },
    {
      target: '#compare-scenario-selector',
      title: 'Select Scenarios',
      body: 'Check scenarios to include in the comparison. Use Select All to pick every scenario, or set one row as baseline for delta columns.',
      tip: 'Baseline scenarios show a badge; other selected rows get a Set as baseline button.',
      position: 'bottom'
    },
    {
      target: '#comparison-section',
      title: 'Comparison Table',
      body: 'Selected scenarios appear here with default columns for societal BCR, total PV cost, capital cost, and total benefits. Add or remove metric columns as needed.',
      position: 'top'
    },
    {
      target: '#compare-baseline-btn',
      title: 'Compare to Baseline',
      body: 'Opens delta options: toggle absolute \u0394 (scenario minus baseline) and percent \u0394 on numeric metrics.',
      tip: 'Pick a baseline in the selector above before deltas appear in the table.',
      position: 'bottom'
    },
    {
      target: '.compare-delta-info',
      title: 'Delta Legend',
      body: 'Hover the info icon for the sign convention: positive \u0394 means higher values \u2014 more expensive for costs, better for benefits.',
      position: 'right'
    },
    {
      target: '#comparison-table-container',
      title: 'Metrics Table',
      body: 'When two or more scenarios are selected, metrics render in rows here. Use Add column\u2026 in the table header to open the metric picker.',
      tip: 'Drag column headers to reorder; click remove under a column to drop it from the view.',
      position: 'top'
    },
    {
      target: '.compare-toolbar',
      title: 'Compare Toolbar',
      body: 'Copy the table to your clipboard, export a PNG snapshot, or enable Auto-sort Columns to keep metrics in catalog order.',
      position: 'bottom'
    },
    {
      target: '#copy-table-btn',
      title: 'Copy Table',
      body: 'Copies the visible comparison (including delta rows when enabled) as tab-separated values for pasting into Excel or Sheets.',
      position: 'bottom'
    },
    {
      target: '#export-png-btn',
      title: 'Export to PNG',
      body: 'Downloads the current comparison table as an image file for slides, reports, or email.',
      position: 'bottom'
    },
    {
      target: '#cmp-auto-sort-columns',
      title: 'Auto-sort Columns',
      body: 'When checked, newly added metric columns snap into the standard catalog order instead of appending at the end.',
      position: 'left'
    },
    {
      target: '.pill-tab[data-scenario-tab="what-if"]',
      title: 'What-If Tab',
      body: 'Design-comparison calculators run in the Workspace where inputs and results update live. This tab links you there when you need interactive what-if analysis.',
      position: 'bottom'
    },
    {
      target: '.app-top-nav-logo',
      title: 'Tour Complete!',
      body: 'You\u2019ve seen all the key features of CTCC. Start by creating a new scenario or exploring an existing one.',
      position: 'bottom'
    }
  ]
};

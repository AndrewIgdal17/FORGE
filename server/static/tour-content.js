var TOUR_CONTENT = {
  home: [
    { target: '#landing-new-scenario-btn', content: 'Click here to create a new transmission scenario using the guided wizard.', position: 'bottom' },
    { target: '#landing-goto-scenarios-btn', content: 'Once you have scenarios, come here to manage and compare them.', position: 'bottom' }
  ],
  workspace: [
    { target: '.sidebar-section-header', content: 'The sidebar organizes ~300 input fields into sections. Expand a section and pick a sub-item to edit that group.', position: 'right' },
    { target: '.sidebar-subitem', content: 'Start with Project Identity \u2192 Technology \u2014 your wizard choices are already filled in here.', position: 'right' },
    { target: '.main-tab-button[data-tab="results"]', content: 'Click Results to see your cost-benefit analysis. Results update live as you change inputs.', position: 'bottom' },
    { target: '#content-panel', content: 'Your Societal BCR and other metrics appear here once you have calculated results.', position: 'top' }
  ],
  scenarios: [
    { target: '#scenario-subtab-manage', content: 'Use Duplicate to copy a scenario, change one variable, and compare alternatives side-by-side.', position: 'top' },
    { target: '.tab-button[data-scenario-tab="compare"]', content: 'The Compare tab shows all selected scenarios in a side-by-side table with delta analysis.', position: 'bottom' }
  ]
};

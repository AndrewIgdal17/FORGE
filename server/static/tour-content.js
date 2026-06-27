var TOUR_CONTENT = {
  home: [
    { target: '#landing-new-scenario-btn', content: 'Click here to create a new transmission scenario using the guided wizard.', position: 'bottom' },
    { target: '#landing-goto-scenarios-btn', content: 'Once you have scenarios, come here to manage and compare them.', position: 'bottom' }
  ],
  workspace: [
    { target: '.workspace-tab[data-wtab="inputs"]', content: 'These 9 tabs contain ~300 fields, but you only need to set what the wizard collected. Everything else has researched defaults.', position: 'bottom' },
    { target: '#tab-buttons .tab-button:first-child', content: 'Start here \u2014 Project Details defines your line type, capacity, and route. Your wizard choices are already filled in.', position: 'bottom' },
    { target: '.workspace-tab[data-wtab="results"]', content: 'Click Results to see your cost-benefit analysis. Results update live as you change inputs.', position: 'bottom' },
    { target: '#result', content: 'Your Societal BCR is the headline number \u2014 the ratio of total benefits to total costs from society\'s perspective.', position: 'top' }
  ],
  scenarios: [
    { target: '#scenario-subtab-manage', content: 'Use Duplicate to copy a scenario, change one variable, and compare alternatives side-by-side.', position: 'top' },
    { target: '.tab-button[data-scenario-tab="compare"]', content: 'The Compare tab shows all selected scenarios in a side-by-side table with delta analysis.', position: 'bottom' }
  ]
};

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
      position: 'bottom'
    },
    {
      target: '.app-top-nav-link[data-nav="workspace"]',
      title: 'Continue to Workspace',
      body: 'Click here to continue the tour in the Workspace \u2014 where you build and analyze transmission scenarios.',
      position: 'bottom',
      action: { type: 'navigate', url: '/app/workspace' }
    }
  ],
  workspace: [],
  scenarios: []
};

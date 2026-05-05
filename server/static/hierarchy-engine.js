// TAB_HIERARCHY engine — extracted from index.html
// Loaded after configs.js (which defines TAB_HIERARCHY) and before the inline <script>.

function humanizeKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .replace(/\bAfudc\b/g, 'AFUDC')
    .replace(/\bWacc\b/g, 'WACC')
    .replace(/\bOandm\b/g, 'O&M')
    .replace(/\bOm\b/g, 'O&M')
    .replace(/\bCongestion Curtailment\b/g, 'Congestion & Curtailment')
    .replace(/\bAc Dc\b/g, 'AC/DC')
    .replace(/\bCo2\b/g, 'CO2')
    .replace(/\bSox\b/g, 'SOx')
    .replace(/\bNox\b/g, 'NOx')
    .replace(/\bMwh\b/g, 'MWh')
    .replace(/\bMw\b/g, 'MW')
    .replace(/\bKg\b/g, 'kg')
    .replace(/\bPer\b/g, 'per')
    .replace(/\bBcr\b/g, 'BCR')
    .replace(/\bRow\b/g, 'ROW')
    .replace(/^Right Of Way$/, 'Right-of-Way Zones 1\u201315')
    .replace(/\bRight Of Way\b/g, 'Right-of-Way')
    .replace(/\bOperations And Maintenance\b/g, 'O&M')
    .replace(/^Ignition Rates By Terrain$/, 'Ignition Rates by Terrain (events/mi/yr)')
    .replace(/^Outage Duration By Terrain$/, 'Outage Duration by Terrain (hrs/event)')
    .replace(/^Outage Rates$/, 'Outage Rates (outages/mi/yr)')
    .replace(/^Primary BCR Config$/, 'Benefit Cost Ratio (BCR) Calculation');
}

function applyTabHierarchy() {
  for (const [tabId, config] of Object.entries(TAB_HIERARCHY)) {
    const tab = document.querySelector(`[data-tab-id="${tabId}"]`);
    if (!tab) continue;

    const claimed = new Set();
    const sectionGroups = [];

    // --- Claim phase ---
    for (const section of (config.sections || [])) {
      let elements = [];

      if (section.matchPath) {
        // Find header row by Reset button data-section-path
        let headerRow = null;
        tab.querySelectorAll('.section-header-row').forEach(row => {
          const btn = row.querySelector('.section-reset-btn');
          if (btn && btn.dataset.sectionPath === section.matchPath) {
            headerRow = row;
          }
        });
        // Or find tab-section-header by data-section-key
        if (!headerRow) {
          tab.querySelectorAll('.tab-section-header').forEach(h => {
            if (h.dataset.sectionKey === section.matchPath) {
              headerRow = h;
            }
          });
        }
        if (headerRow && !claimed.has(headerRow)) {
          elements.push(headerRow);
          claimed.add(headerRow);
          if (!section.hidden) {
            const isTabHeader = headerRow.classList.contains('tab-section-header');
            let sibling = headerRow.nextElementSibling;
            while (sibling) {
              if (sibling.classList.contains('tab-section-header')) break;
              if (!isTabHeader && sibling.classList.contains('section-header-row')) {
                const btn = sibling.querySelector('.section-reset-btn');
                const childPath = btn?.dataset?.sectionPath || '';
                if (!childPath.startsWith(section.matchPath + '.')) break;
              }
              if (!claimed.has(sibling)) {
                elements.push(sibling);
                claimed.add(sibling);
              }
              sibling = sibling.nextElementSibling;
            }
          }
        }
      }

      if (section.matchFields) {
        const matched = [];
        tab.querySelectorAll('.form-field').forEach(field => {
          const fp = field.dataset.fieldPath || '';
          for (const suffix of section.matchFields) {
            if (fp.endsWith('.' + suffix) || fp === suffix) {
              if (!claimed.has(field)) {
                matched.push(field);
                claimed.add(field);
              }
              break;
            }
          }
        });

        if (matched.length > 0) {
          const headerRow = document.createElement('div');
          headerRow.className = 'section-header-row';
          const headerEl = document.createElement('div');
          headerEl.className = 'subsection-header';
          headerEl.textContent = section.label || section.id;
          headerRow.appendChild(headerEl);
          const grid = document.createElement('div');
          grid.className = 'form-grid';
          matched.forEach(f => grid.appendChild(f));
          elements = [headerRow, grid];
        }
      }

      sectionGroups.push({ section, elements });
    }

    // --- Reorder phase ---
    const fragment = document.createDocumentFragment();

    for (const { elements } of sectionGroups) {
      for (const el of elements) {
        fragment.appendChild(el);
      }
    }

    // Append unclaimed children (preserve original order)
    const unclaimed = [];
    while (tab.firstChild) {
      const child = tab.firstChild;
      tab.removeChild(child);
      if (!claimed.has(child)) {
        unclaimed.push(child);
      }
    }
    for (const el of unclaimed) {
      fragment.appendChild(el);
    }

    tab.appendChild(fragment);

    // Clean up empty form-grids left by matchFields extraction
    tab.querySelectorAll('.form-grid').forEach(grid => {
      if (grid.children.length === 0) grid.remove();
    });

    // --- Decorate phase ---
    for (const { section, elements } of sectionGroups) {
      if (elements.length === 0) continue;
      const headerRow = elements[0];

      if (section.hidden) {
        elements.forEach(el => el.style.display = 'none');
        continue;
      }

      const headerEl = headerRow.querySelector('.subsection-header, .section-header') || headerRow;

      if (headerEl.classList.contains('subsection-header')) {
        headerEl.classList.remove('subsection-header');
        headerEl.classList.add('section-header');
      }

      if (section.label) {
        headerEl.textContent = section.label;
      }

      headerEl.classList.add('collapsible-header');
      const decorateIsTabHeader = headerRow.classList.contains('tab-section-header');
      const wrapper = document.createElement('div');
      wrapper.className = 'collapsible-content';
      const toWrap = [];
      let sibling = headerRow.nextElementSibling;
      while (sibling) {
        if (sibling.classList.contains('tab-section-header')) break;
        if (!decorateIsTabHeader && sibling.classList.contains('section-header-row')) {
          const btn = sibling.querySelector('.section-reset-btn');
          const childPath = btn?.dataset?.sectionPath || '';
          if (!childPath.startsWith(section.matchPath + '.')) break;
        }
        toWrap.push(sibling);
        sibling = sibling.nextElementSibling;
      }
      if (toWrap.length > 0) {
        headerRow.parentNode.insertBefore(wrapper, toWrap[0]);
        toWrap.forEach(el => wrapper.appendChild(el));
      }
      if (section.tier !== 'advanced') {
        headerEl.classList.add('expanded');
        wrapper.classList.add('expanded');
      }
      headerEl.addEventListener('click', () => {
        headerEl.classList.toggle('expanded');
        wrapper.classList.toggle('expanded');
      });

      if (section.note) {
        const noteEl = document.createElement('div');
        noteEl.className = 'results-note';
        noteEl.style.marginTop = '0.35rem';
        noteEl.style.marginBottom = '0.5rem';
        noteEl.textContent = section.note;
        headerRow.parentNode.insertBefore(noteEl, headerRow.nextElementSibling);
      }

      // --- Children sub-grouping (matchFields or matchPath within parent) ---
      if (section.children && section.children.length > 0 && toWrap.length > 0) {
        for (const child of section.children) {
          if (child.matchFields && child.matchFields.length > 0) {
            const matched = [];
            wrapper.querySelectorAll('.form-field').forEach(field => {
              const fp = field.dataset.fieldPath || '';
              for (const suffix of child.matchFields) {
                if (fp.endsWith('.' + suffix) || fp === suffix) {
                  matched.push(field);
                  break;
                }
              }
            });
            if (matched.length === 0) continue;
            const subHeader = document.createElement('div');
            subHeader.className = 'subsection-header collapsible-header';
            subHeader.textContent = child.label || '';
            const subContent = document.createElement('div');
            subContent.className = 'collapsible-content';
            if (child.collapsed !== true) {
              subHeader.classList.add('expanded');
              subContent.classList.add('expanded');
            }
            const grid = document.createElement('div');
            grid.className = 'form-grid';
            matched.forEach(f => grid.appendChild(f));
            subContent.appendChild(grid);
            wrapper.appendChild(subHeader);
            wrapper.appendChild(subContent);
            subHeader.addEventListener('click', (e) => {
              e.stopPropagation();
              subHeader.classList.toggle('expanded');
              subContent.classList.toggle('expanded');
            });
          } else if (child.matchPath) {
            let childHeaderRow = null;
            wrapper.querySelectorAll('.section-header-row').forEach(row => {
              const btn = row.querySelector('.section-reset-btn');
              if (btn && btn.dataset.sectionPath === child.matchPath) {
                childHeaderRow = row;
              }
            });
            if (!childHeaderRow) continue;
            const childHeaderEl = childHeaderRow.querySelector('.subsection-header, .section-header') || childHeaderRow;
            if (child.label) childHeaderEl.textContent = child.label;
            if (child.collapsed !== undefined) {
              childHeaderEl.classList.add('collapsible-header');
              const subWrapper = document.createElement('div');
              subWrapper.className = 'collapsible-content';
              if (!child.collapsed) {
                childHeaderEl.classList.add('expanded');
                subWrapper.classList.add('expanded');
              }
              const toWrapChild = [];
              let nextSib = childHeaderRow.nextElementSibling;
              while (nextSib) {
                if (nextSib.classList.contains('section-header-row') ||
                    nextSib.classList.contains('tab-section-header') ||
                    nextSib.classList.contains('subsection-header')) break;
                toWrapChild.push(nextSib);
                nextSib = nextSib.nextElementSibling;
              }
              if (toWrapChild.length > 0) {
                childHeaderRow.parentNode.insertBefore(subWrapper, toWrapChild[0]);
                toWrapChild.forEach(el => subWrapper.appendChild(el));
              }
              childHeaderEl.addEventListener('click', (e) => {
                e.stopPropagation();
                childHeaderEl.classList.toggle('expanded');
                subWrapper.classList.toggle('expanded');
              });
            }
          }
        }
        wrapper.querySelectorAll('.form-grid').forEach(grid => {
          if (grid.children.length === 0) grid.remove();
        });
      }
    }

    // --- Reset button consolidation ---
    if (config.resetButton === 'single') {
      const resetButtons = Array.from(tab.querySelectorAll('button')).filter(b =>
        b.textContent.trim().toLowerCase() === 'reset'
      );
      if (resetButtons.length > 1) {
        resetButtons.slice(0, -1).forEach(b => b.remove());
      }
    }
  }
}

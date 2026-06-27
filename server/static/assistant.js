(function() {
'use strict';

let _iconEl = null;
let _bubbleEl = null;

function initAssistant() {
  if (_iconEl) return;
  _iconEl = document.createElement('div');
  _iconEl.className = 'assistant-icon';
  _iconEl.innerHTML = '?';
  _iconEl.title = 'Help & Tour';
  _iconEl.addEventListener('click', toggleAssistantBubble);
  document.body.appendChild(_iconEl);
  _bubbleEl = document.createElement('div');
  _bubbleEl.className = 'assistant-bubble';
  _bubbleEl.style.display = 'none';
  document.body.appendChild(_bubbleEl);
}

function toggleAssistantBubble() {
  if (!_bubbleEl) return;
  if (_bubbleEl.style.display === 'none') {
    showAssistantBubble(getContextualTip());
  } else {
    _bubbleEl.style.display = 'none';
  }
}

function showAssistantBubble(content) {
  if (!_bubbleEl) return;
  _bubbleEl.innerHTML =
    '<div class="assistant-bubble-content">' + content + '</div>' +
    '<div class="assistant-bubble-actions">' +
      '<button type="button" onclick="startQuickTour()">Quick tour of this page</button>' +
      '<button type="button" onclick="startFullTour()">Full guided tour</button>' +
    '</div>' +
    '<button type="button" class="assistant-bubble-close" onclick="hideAssistant()">&times;</button>';
  _bubbleEl.style.display = '';
}

function showAssistantMessage(text) {
  if (!_bubbleEl) return;
  _bubbleEl.innerHTML =
    '<div class="assistant-bubble-content">' + text + '</div>' +
    '<button type="button" class="assistant-bubble-close" onclick="hideAssistant()">&times;</button>';
  _bubbleEl.style.display = '';
}

function hideAssistant() {
  if (_bubbleEl) _bubbleEl.style.display = 'none';
}

function getContextualTip() {
  var activeTab = document.querySelector('.main-tab-button.active');
  var tab = activeTab ? activeTab.dataset.tab : '';
  if (tab === 'inputs') {
    var subTab = document.querySelector('#tab-buttons .tab-button.active');
    if (subTab) return 'You\'re on the <strong>' + subTab.textContent.trim() + '</strong> tab. Fields with a lock icon have researched defaults \u2014 unlock to override.';
    return 'The Inputs tabs contain ~300 fields. Most have researched defaults \u2014 you only need to set project-specific values.';
  }
  if (tab === 'results') return 'Results update live as you change inputs. The <strong>Summary</strong> shows headline BCR and cost/benefit totals.';
  if (tab === 'scenarios') return 'Manage your scenarios here. Use <strong>Compare</strong> for side-by-side metrics. <strong>Duplicate</strong> a scenario to create a variant.';
  return 'Welcome to the CTCC. Click <strong>+ New Scenario</strong> to get started.';
}

function startQuickTour() {
  hideAssistant();
  if (typeof TOUR_CONTENT !== 'undefined' && typeof startTour === 'function') {
    var activeTab = document.querySelector('.main-tab-button.active');
    var tab = activeTab ? activeTab.dataset.tab : '';
    var pageSteps = TOUR_CONTENT.filter(function(s) { return s.page === tab; });
    if (pageSteps.length > 0) startTour(pageSteps);
  }
}

function startFullTour() {
  hideAssistant();
  if (typeof TOUR_CONTENT !== 'undefined' && typeof startTour === 'function') {
    startTour(TOUR_CONTENT, function() {
      localStorage.setItem('ctcc-tour-complete', 'true');
      showAssistantMessage('Tour complete! I\'ll be here if you need me.');
    });
  }
}

function showWelcomeBubble() {
  if (!_bubbleEl) return;
  _bubbleEl.innerHTML =
    '<div class="assistant-bubble-content">' +
      'Looks like you\'re new to the CTCC. We recommend you take a tour with us as we walk through a tutorial!' +
    '</div>' +
    '<div class="assistant-bubble-actions">' +
      '<button type="button" onclick="startFullTour()">Start Tour</button>' +
      '<button type="button" onclick="hideAssistant()">No thanks</button>' +
    '</div>' +
    '<button type="button" class="assistant-bubble-close" onclick="hideAssistant()">&times;</button>';
  _bubbleEl.style.display = '';
}

window.initAssistant = initAssistant;
window.showWelcomeBubble = showWelcomeBubble;
window.showAssistantMessage = showAssistantMessage;
window.showAssistantBubble = showAssistantBubble;
window.hideAssistant = hideAssistant;
window.startQuickTour = startQuickTour;
window.startFullTour = startFullTour;
})();

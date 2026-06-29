(function() {
'use strict';

var STORAGE_KEY = 'ctcc-tour-state';
var _steps = [];
var _currentStepIdx = -1;
var _overlayEl = null;
var _bubbleEl = null;
var _onComplete = null;
var _mode = null;

function startTour(steps, mode, onComplete) {
  _steps = steps;
  _mode = mode || 'full';
  _currentStepIdx = -1;
  _onComplete = onComplete || null;
  _ensureOverlay();
  nextTourStep();
}

function resumeTour(steps, mode, stepIndex) {
  _steps = steps;
  _mode = mode;
  _currentStepIdx = stepIndex - 1;
  _onComplete = null;
  _ensureOverlay();
  nextTourStep();
}

function endTour() {
  _removeOverlay();
  _steps = [];
  _currentStepIdx = -1;
  _mode = null;
  sessionStorage.removeItem(STORAGE_KEY);
  if (_onComplete) _onComplete();
}

function nextTourStep() {
  _currentStepIdx++;
  if (_currentStepIdx >= _steps.length) { endTour(); return; }
  _persistState();
  var step = _steps[_currentStepIdx];
  _executeAction(step, function() {
    _highlightStep(step);
  });
}

function prevTourStep() {
  if (_currentStepIdx > 0) {
    _currentStepIdx--;
    _persistState();
    var step = _steps[_currentStepIdx];
    _highlightStep(step);
  }
}

function _persistState() {
  if (_mode === 'full') {
    var page = window._tourPage || 'home';
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      mode: _mode,
      currentPage: page,
      stepIndex: _currentStepIdx,
      startedAt: new Date().toISOString()
    }));
  }
}

function _executeAction(step, callback) {
  if (!step.action) { callback(); return; }
  var action = step.action;
  if (action.type === 'click') {
    var el = document.querySelector(action.target);
    if (el) el.click();
    setTimeout(callback, action.delay || 300);
  } else if (action.type === 'navigate') {
    _persistState();
    window.location.href = action.url;
  } else if (action.type === 'wait') {
    setTimeout(callback, action.ms || 500);
  } else {
    callback();
  }
}

function _ensureOverlay() {
  if (_overlayEl) return;
  _overlayEl = document.createElement('div');
  _overlayEl.className = 'tour-overlay';
  document.body.appendChild(_overlayEl);
  _bubbleEl = document.createElement('div');
  _bubbleEl.className = 'tour-bubble';
  document.body.appendChild(_bubbleEl);
}

function _removeOverlay() {
  if (_overlayEl) { _overlayEl.remove(); _overlayEl = null; }
  if (_bubbleEl) { _bubbleEl.remove(); _bubbleEl = null; }
  document.querySelectorAll('.tour-highlighted').forEach(function(el) { el.classList.remove('tour-highlighted'); });
}

function _highlightStep(step) {
  console.log('[TOUR DEBUG] _highlightStep called. target =', step.target);
  document.querySelectorAll('.tour-highlighted').forEach(function(el) { el.classList.remove('tour-highlighted'); });
  var target = document.querySelector(step.target);
  console.log('[TOUR DEBUG] querySelector result =', target ? 'FOUND' : 'NOT FOUND');
  if (!target) { console.log('[TOUR DEBUG] Skipping step — target missing'); nextTourStep(); return; }
  target.classList.add('tour-highlighted');
  target.scrollIntoView({ behavior: 'smooth', block: 'center' });

  setTimeout(function() {
    console.log('[TOUR DEBUG] 350ms timeout fired. Positioning bubble.');
    var rect = target.getBoundingClientRect();
    console.log('[TOUR DEBUG] rect =', JSON.stringify({top: rect.top, left: rect.left, width: rect.width, height: rect.height}));    var pad = 8;
    if (_overlayEl) {
      var l = rect.left - pad, t = rect.top - pad;
      var r = rect.right + pad, b = rect.bottom + pad;
      _overlayEl.style.clipPath =
        'polygon(0% 0%, 0% 100%, ' + l + 'px 100%, ' + l + 'px ' + t + 'px, ' +
        r + 'px ' + t + 'px, ' + r + 'px ' + b + 'px, ' +
        l + 'px ' + b + 'px, ' + l + 'px 100%, 100% 100%, 100% 0%)';
    }
    if (_bubbleEl) {
      var stepNum = _currentStepIdx + 1;
      var totalSteps = _steps.length;
      var html = '<div class="tour-bubble-header">' +
        '<span class="tour-bubble-title">' + (step.title || '') + '</span>' +
        '<span class="tour-bubble-counter">' + stepNum + ' / ' + totalSteps + '</span>' +
        '</div>';
      if (step.body) html += '<div class="tour-bubble-body">' + step.body + '</div>';
      if (step.tip) html += '<div class="tour-bubble-tip">\uD83D\uDCA1 ' + step.tip + '</div>';
      html += '<div class="tour-bubble-nav">' +
        '<button type="button" class="tour-btn-skip" onclick="endTour()">Skip tour</button>' +
        '<div class="tour-bubble-buttons">' +
          (_currentStepIdx > 0 ? '<button type="button" class="tour-btn-back" onclick="prevTourStep()">\u2190 Back</button>' : '') +
          '<button type="button" class="tour-btn-next" onclick="nextTourStep()">Next \u2192</button>' +
        '</div></div>';

      _bubbleEl.innerHTML = html;

      var pos = step.position || 'bottom';
      _bubbleEl.style.position = 'fixed';
      _bubbleEl.style.display = 'block';
      _bubbleEl.style.top = '';
      _bubbleEl.style.left = '';
      _bubbleEl.style.right = '';
      _bubbleEl.style.bottom = '';

      if (pos === 'bottom') {
        _bubbleEl.style.top = (rect.bottom + pad + 12) + 'px';
        _bubbleEl.style.left = Math.max(16, Math.min(rect.left, window.innerWidth - 360)) + 'px';
      } else if (pos === 'top') {
        _bubbleEl.style.top = Math.max(16, rect.top - pad - 12 - _bubbleEl.offsetHeight) + 'px';
        _bubbleEl.style.left = Math.max(16, Math.min(rect.left, window.innerWidth - 360)) + 'px';
      } else if (pos === 'right') {
        _bubbleEl.style.top = rect.top + 'px';
        _bubbleEl.style.left = (rect.right + pad + 12) + 'px';
      } else if (pos === 'left') {
        _bubbleEl.style.top = rect.top + 'px';
        _bubbleEl.style.right = (window.innerWidth - rect.left + pad + 12) + 'px';
      }
    }
  }, 350);
}

function checkTourResume() {
  var raw = sessionStorage.getItem(STORAGE_KEY);
  console.log('[TOUR DEBUG] checkTourResume fired. raw =', raw);
  if (!raw) { console.log('[TOUR DEBUG] No sessionStorage state — exiting'); return; }
  try {
    var state = JSON.parse(raw);
    var startedAt = new Date(state.startedAt);
    if (Date.now() - startedAt.getTime() > 24 * 60 * 60 * 1000) {
      console.log('[TOUR DEBUG] Expired (>24h) — clearing');
      sessionStorage.removeItem(STORAGE_KEY);
      return;
    }
    var page = window._tourPage || 'home';
    console.log('[TOUR DEBUG] state =', JSON.stringify(state), 'page =', page);
    if (typeof TOUR_STEPS === 'undefined') { console.log('[TOUR DEBUG] TOUR_STEPS undefined — exiting'); return; }

    var steps = TOUR_STEPS[page] || [];
    console.log('[TOUR DEBUG] TOUR_STEPS[page] length =', steps.length);
    if (state.currentPage !== page && page === 'scenarios') {
      var params = new URLSearchParams(window.location.search);
      console.log('[TOUR DEBUG] Scenarios re-entry. tour param =', params.get('tour'));
      if (params.get('tour') === 'compare' && TOUR_STEPS.scenarios_compare) {
        steps = TOUR_STEPS.scenarios_compare;
      } else if (TOUR_STEPS.scenarios_manage) {
        steps = TOUR_STEPS.scenarios_manage;
      }
      console.log('[TOUR DEBUG] Using steps array length =', steps.length);
      if (params.has('tour')) {
        params.delete('tour');
        var clean = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        history.replaceState(null, '', clean);
      }
    }
    if (!steps.length) { console.log('[TOUR DEBUG] steps empty — exiting'); return; }

    if (state.currentPage !== page) {
      console.log('[TOUR DEBUG] Cross-page resume from', state.currentPage, 'to', page, '— starting at 0');
      resumeTour(steps, 'full', 0);
    } else if (state.stepIndex < steps.length) {
      console.log('[TOUR DEBUG] Same-page resume at step', state.stepIndex);
      resumeTour(steps, 'full', state.stepIndex);
    } else {
      console.log('[TOUR DEBUG] stepIndex >= steps.length — no resume');
    }
  } catch (e) {
    console.log('[TOUR DEBUG] Error in checkTourResume:', e);
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

window.startTour = startTour;
window.resumeTour = resumeTour;
window.endTour = endTour;
window.nextTourStep = nextTourStep;
window.prevTourStep = prevTourStep;
window.checkTourResume = checkTourResume;

document.addEventListener('DOMContentLoaded', function() {
  setTimeout(checkTourResume, 1000);
});

})();

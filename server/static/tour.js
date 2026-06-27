(function() {
'use strict';

let _steps = [];
let _currentStepIdx = -1;
let _overlayEl = null;
let _bubbleEl = null;
let _onComplete = null;

function startTour(steps, onComplete) {
  _steps = steps;
  _currentStepIdx = -1;
  _onComplete = onComplete || null;
  _ensureOverlay();
  nextTourStep();
}

function endTour() {
  _removeOverlay();
  _steps = [];
  _currentStepIdx = -1;
  if (_onComplete) _onComplete();
}

function nextTourStep() {
  _currentStepIdx++;
  if (_currentStepIdx >= _steps.length) { endTour(); return; }
  _highlightStep(_steps[_currentStepIdx]);
}

function prevTourStep() {
  if (_currentStepIdx > 0) {
    _currentStepIdx--;
    _highlightStep(_steps[_currentStepIdx]);
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
  document.querySelectorAll('.tour-highlighted').forEach(el => el.classList.remove('tour-highlighted'));
}

function _highlightStep(step) {
  document.querySelectorAll('.tour-highlighted').forEach(el => el.classList.remove('tour-highlighted'));
  const target = document.querySelector(step.target);
  if (!target) { nextTourStep(); return; }
  target.classList.add('tour-highlighted');
  target.scrollIntoView({ behavior: 'smooth', block: 'center' });

  setTimeout(() => {
    const rect = target.getBoundingClientRect();
    const pad = 8;
    if (_overlayEl) {
      const l = rect.left - pad, t = rect.top - pad;
      const r = rect.right + pad, b = rect.bottom + pad;
      _overlayEl.style.clipPath =
        'polygon(0% 0%, 0% 100%, ' + l + 'px 100%, ' + l + 'px ' + t + 'px, ' +
        r + 'px ' + t + 'px, ' + r + 'px ' + b + 'px, ' +
        l + 'px ' + b + 'px, ' + l + 'px 100%, 100% 100%, 100% 0%)';
    }
    if (_bubbleEl) {
      const stepNum = _currentStepIdx + 1;
      const totalSteps = _steps.length;
      _bubbleEl.innerHTML =
        '<div class="tour-bubble-content">' + step.content + '</div>' +
        '<div class="tour-bubble-nav">' +
          '<span class="tour-bubble-progress">' + stepNum + ' / ' + totalSteps + '</span>' +
          '<div class="tour-bubble-buttons">' +
            '<button type="button" class="tour-btn-skip" onclick="endTour()">Skip tour</button>' +
            (_currentStepIdx > 0 ? '<button type="button" class="tour-btn-back" onclick="prevTourStep()">\u2190</button>' : '') +
            '<button type="button" class="tour-btn-next" onclick="nextTourStep()">Next \u2192</button>' +
          '</div>' +
        '</div>';

      const pos = step.position || 'bottom';
      _bubbleEl.style.position = 'fixed';
      if (pos === 'bottom') {
        _bubbleEl.style.top = (rect.bottom + pad + 12) + 'px';
        _bubbleEl.style.left = Math.max(16, rect.left) + 'px';
      } else if (pos === 'top') {
        _bubbleEl.style.top = Math.max(16, rect.top - pad - 12 - 150) + 'px';
        _bubbleEl.style.left = Math.max(16, rect.left) + 'px';
      } else if (pos === 'right') {
        _bubbleEl.style.top = rect.top + 'px';
        _bubbleEl.style.left = (rect.right + pad + 12) + 'px';
      }
      _bubbleEl.style.display = '';
    }
  }, 350);
}

window.startTour = startTour;
window.endTour = endTour;
window.nextTourStep = nextTourStep;
window.prevTourStep = prevTourStep;
})();

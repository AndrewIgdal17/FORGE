(function() {
'use strict';

var SIZE = 64;
var IMG_W = 764;
var IMG_H = 1024;
var ROWS = 5;
var ROW_H = IMG_H / ROWS;
var FRAMES_PER_ROW = [4, 6, 6, 8, 8];
var FRAME_W_PER_ROW = FRAMES_PER_ROW.map(function(n) { return IMG_W / n; });
var SPEEDS = [600, 400, 150, 120, 500];
var STATE_MAP = { idle: 0, hop: 1, run: 2, run2: 3, emote: 4 };

var enabled = localStorage.getItem('ctcc-mascot') !== 'off';
var el = null;
var targetX = window.innerWidth / 2;
var targetY = window.innerHeight / 2;
var currentX = targetX;
var currentY = targetY;
var stateIdx = 0;
var frameIdx = 0;
var lastFrameTime = 0;
var lastMoveTime = 0;
var animId = null;
var facingLeft = false;

function createMascot() {
  el = document.createElement('div');
  el.id = 'cursor-mascot';
  document.body.appendChild(el);
  applyFrame();
}

function applyFrame() {
  if (!el) return;
  var row = stateIdx;
  var cols = FRAMES_PER_ROW[row];
  var srcFrameW = FRAME_W_PER_ROW[row];
  var srcRowH = ROW_H;
  var scaleX = SIZE / srcFrameW;
  var scaleY = SIZE / srcRowH;
  var bgW = IMG_W * scaleX;
  var bgH = IMG_H * scaleY;
  var bgX = -(frameIdx * SIZE);
  var bgY = -(row * SIZE);

  el.style.cssText = 'position:fixed;width:' + SIZE + 'px;height:' + SIZE + 'px;' +
    'pointer-events:none;z-index:9999;image-rendering:pixelated;' +
    'background-image:url(/static/mascot-pixel.png);' +
    'background-size:' + bgW + 'px ' + bgH + 'px;' +
    'background-position:' + bgX + 'px ' + bgY + 'px;' +
    'transform:' + (facingLeft ? 'scaleX(-1)' : 'scaleX(1)') + ';' +
    'left:' + (currentX - SIZE / 2) + 'px;' +
    'top:' + (currentY - SIZE / 2) + 'px;';
}

function setState(idx) {
  if (idx === stateIdx) return;
  stateIdx = idx;
  frameIdx = 0;
}

function animate(now) {
  if (!el) return;

  var dx = targetX - currentX;
  var dy = targetY - currentY;
  var dist = Math.sqrt(dx * dx + dy * dy);

  currentX += dx * 0.08;
  currentY += dy * 0.08;

  if (dx > 2) facingLeft = false;
  else if (dx < -2) facingLeft = true;

  var timeSinceMove = now - lastMoveTime;

  if (dist > 100) setState(STATE_MAP.run);
  else if (dist > 40) setState(STATE_MAP.hop);
  else if (timeSinceMove > 5000) setState(STATE_MAP.emote);
  else setState(STATE_MAP.idle);

  if (now - lastFrameTime > SPEEDS[stateIdx]) {
    frameIdx = (frameIdx + 1) % FRAMES_PER_ROW[stateIdx];
    lastFrameTime = now;
  }

  applyFrame();
  animId = requestAnimationFrame(animate);
}

function onMouseMove(e) {
  targetX = e.clientX;
  targetY = e.clientY;
  lastMoveTime = performance.now();
}

function start() {
  if (el) return;
  createMascot();
  document.addEventListener('mousemove', onMouseMove);
  lastMoveTime = performance.now();
  animId = requestAnimationFrame(animate);
}

function stop() {
  if (el) { el.remove(); el = null; }
  document.removeEventListener('mousemove', onMouseMove);
  if (animId) { cancelAnimationFrame(animId); animId = null; }
}

function toggle() {
  enabled = !enabled;
  localStorage.setItem('ctcc-mascot', enabled ? 'on' : 'off');
  if (enabled) start(); else stop();
  updateToggleBtn();
}

function updateToggleBtn() {
  var btn = document.getElementById('mascot-toggle-btn');
  if (btn) {
    btn.style.opacity = enabled ? '1' : '0.4';
    btn.title = enabled ? 'Disable mascot' : 'Enable mascot';
  }
}

function init() {
  var nav = document.querySelector('.app-top-nav-user');
  if (nav) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.id = 'mascot-toggle-btn';
    btn.textContent = '\u{1F5FC}';
    btn.style.cssText = 'font-size:1.1rem;padding:0.2rem 0.4rem;background:none;border:1px solid rgba(0,0,0,0.12);border-radius:4px;cursor:pointer;';
    btn.addEventListener('click', toggle);
    nav.insertBefore(btn, nav.firstChild);
    updateToggleBtn();
  }
  if (enabled) start();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

})();

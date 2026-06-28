(function() {
'use strict';

var MASCOT_SIZE = 64;
var SPRITE_ROWS = {
  idle:  { y: 0,   frames: 4, speed: 600 },
  hop:   { y: 205, frames: 6, speed: 400 },
  run:   { y: 410, frames: 6, speed: 150 },
  run2:  { y: 615, frames: 8, speed: 120 },
  emote: { y: 820, frames: 8, speed: 500 }
};

var enabled = localStorage.getItem('ctcc-mascot') !== 'off';
var el = null;
var targetX = window.innerWidth / 2;
var targetY = window.innerHeight / 2;
var currentX = targetX;
var currentY = targetY;
var currentState = 'idle';
var frameIndex = 0;
var lastFrameTime = 0;
var lastMoveTime = 0;
var speed = 0;
var animId = null;
var facingLeft = false;

function createMascot() {
  el = document.createElement('div');
  el.id = 'cursor-mascot';
  el.style.cssText = 'position:fixed;width:' + MASCOT_SIZE + 'px;height:' + MASCOT_SIZE + 'px;' +
    'pointer-events:none;z-index:9999;image-rendering:pixelated;' +
    'background-image:url(/static/mascot-pixel.png);' +
    'background-size:' + (MASCOT_SIZE * 8) + 'px auto;' +
    'transition:transform 0.1s;';
  document.body.appendChild(el);
  setState('idle');
}

function setState(state) {
  if (state === currentState) return;
  currentState = state;
  frameIndex = 0;
}

function updateFrame(now) {
  var row = SPRITE_ROWS[currentState];
  if (!row) return;
  if (now - lastFrameTime > row.speed) {
    frameIndex = (frameIndex + 1) % row.frames;
    lastFrameTime = now;
  }
  var bgX = -(frameIndex * MASCOT_SIZE);
  var bgY = -(row.y / (1024 / MASCOT_SIZE));
  var scaledRowY = (row.y / 1024) * (MASCOT_SIZE * 5);
  el.style.backgroundPosition = bgX + 'px -' + scaledRowY + 'px';
  el.style.transform = facingLeft ? 'scaleX(-1)' : 'scaleX(1)';
}

function animate(now) {
  if (!el) return;

  var dx = targetX - currentX;
  var dy = targetY - currentY;
  var dist = Math.sqrt(dx * dx + dy * dy);

  var lerp = 0.08;
  currentX += dx * lerp;
  currentY += dy * lerp;

  el.style.left = (currentX - MASCOT_SIZE / 2) + 'px';
  el.style.top = (currentY - MASCOT_SIZE / 2) + 'px';

  if (dx > 2) facingLeft = false;
  else if (dx < -2) facingLeft = true;

  var timeSinceMove = now - lastMoveTime;

  if (dist > 100) {
    setState('run');
  } else if (dist > 40) {
    setState('hop');
  } else if (timeSinceMove > 5000) {
    setState('emote');
  } else {
    setState('idle');
  }

  updateFrame(now);
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
    btn.textContent = enabled ? '🗼' : '🗼';
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
    btn.className = 'btn btn-ghost btn-sm';
    btn.style.cssText = 'font-size:1.1rem;padding:0.2rem 0.4rem;';
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

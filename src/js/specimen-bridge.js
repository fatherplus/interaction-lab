/* ============================================================================
   Interaction Lab v3 — Specimen Bridge (injected into every standalone specimen)
   Syncs theme, WAAPI slow-motion playbackRate, reduced-motion, live knobs,
   and forwards real user interactions back to parent workbench for SQLite telemetry.
   ============================================================================ */
(function () {
  'use strict';

  var currentSpeed = 1;
  var interactSent = false;

  function applySpeedToAnimations() {
    if (!document.getAnimations) return;
    try {
      var anims = document.getAnimations();
      for (var i = 0; i < anims.length; i++) {
        try { anims[i].playbackRate = currentSpeed; } catch (_) {}
      }
    } catch (_) {}
  }

  function setSpeed(speed) {
    var s = Number(speed);
    if (!isFinite(s) || s <= 0) s = 1;
    currentSpeed = s;
    document.documentElement.style.setProperty('--il-speed', String(s));
    applySpeedToAnimations();
  }

  function setTheme(theme) {
    var t = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = t;
    var nodes = document.querySelectorAll('.ep26, .ep27, .ep28, .ep29, .ep30, .ep31 .stage');
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].setAttribute('data-theme', t);
    }
    // Keep ep31 internal theme buttons in sync if present
    var segBtns = document.querySelectorAll('.ep31 .seg button[data-t]');
    for (var j = 0; j < segBtns.length; j++) {
      segBtns[j].setAttribute('aria-pressed', String(segBtns[j].dataset.t === t));
    }
  }

  function setReduced(reduced) {
    var r = Boolean(reduced);
    document.documentElement.dataset.reduced = r ? 'true' : 'false';
    if (r) {
      applySpeedToAnimations();
    }
  }

  function setKnobs(vars) {
    if (!vars || typeof vars !== 'object') return;
    var rootStyle = document.documentElement.style;
    var keys = Object.keys(vars);
    for (var i = 0; i < keys.length; i++) {
      rootStyle.setProperty(keys[i], String(vars[keys[i]]));
    }
  }

  // Apply current speed to any newly triggered CSS transitions or keyframe animations
  document.addEventListener('transitionrun', applySpeedToAnimations, true);
  document.addEventListener('animationstart', applySpeedToAnimations, true);

  // Forward first real user interaction to parent workbench for telemetry
  function notifyInteract() {
    if (interactSent) return;
    interactSent = true;
    try {
      if (window.parent && window.parent !== window) {
        window.parent.postMessage({
          type: 'il-interact',
          id: window.__IL_SPECIMEN_ID__ || '',
        }, '*');
      }
    } catch (_) {}
  }

  document.addEventListener('pointerdown', notifyInteract, { capture: true, passive: true });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab' && e.key !== 'Shift' && e.key !== 'Meta' && e.key !== 'Control') {
      notifyInteract();
    }
  }, true);

  window.addEventListener('message', function (e) {
    var msg = e.data;
    if (!msg || typeof msg !== 'object') return;
    if (msg.type === 'set-theme') setTheme(msg.theme);
    else if (msg.type === 'set-speed') setSpeed(msg.speed);
    else if (msg.type === 'set-reduced') setReduced(msg.reduced);
    else if (msg.type === 'set-knobs') setKnobs(msg.vars);
    else if (msg.type === 'replay') {
      window.dispatchEvent(new CustomEvent('il-replay'));
    }
  });

  // Apply initial state from query params if provided (?theme=dark&speed=1)
  try {
    var sp = new URLSearchParams(window.location.search);
    if (sp.has('theme')) setTheme(sp.get('theme'));
    if (sp.has('speed')) setSpeed(sp.get('speed'));
    if (sp.get('reduced') === 'true') setReduced(true);
  } catch (_) {}

  // Notify parent that specimen is ready
  try {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({
        type: 'il-ready',
        id: window.__IL_SPECIMEN_ID__ || '',
      }, '*');
    }
  } catch (_) {}
})();

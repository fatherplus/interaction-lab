/* ============================================================================
   Interaction Lab v2 — Zero-Dependency Privacy-Friendly Telemetry SDK
   Batched sendBeacon -> POST /api/t -> SQLite (WAL)
   ============================================================================ */
(function (global) {
  'use strict';

  const ENDPOINT = '/api/t';
  const MAX_BATCH = 20;
  const FLUSH_MS = 3200;

  function uuid() {
    if (global.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'id-' + Math.random().toString(36).slice(2, 11) + Date.now().toString(36);
  }

  function getClientId() {
    try {
      let id = localStorage.getItem('il_cid');
      if (!id) { id = uuid(); localStorage.setItem('il_cid', id); }
      return id;
    } catch (_) {
      return uuid();
    }
  }

  function getSessionId() {
    try {
      let id = sessionStorage.getItem('il_sid');
      if (!id) { id = uuid(); sessionStorage.setItem('il_sid', id); }
      return id;
    } catch (_) {
      return uuid();
    }
  }

  const clientId = getClientId();
  const sessionId = getSessionId();
  const queue = [];
  const interactOnce = new Set();
  let timer = null;

  function referrerHost() {
    try {
      if (!document.referrer) return 'direct';
      return new URL(document.referrer).hostname || 'direct';
    } catch (_) {
      return 'direct';
    }
  }

  function flush() {
    if (!queue.length) return;
    if (location.protocol === 'file:') { queue.length = 0; return; }
    const batch = queue.splice(0, MAX_BATCH);
    const body = JSON.stringify({
      client_id: clientId,
      session_id: sessionId,
      referrer_host: referrerHost(),
      events: batch,
    });
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        if (navigator.sendBeacon(ENDPOINT, blob)) return;
      }
      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {});
    } catch (_) {}
  }

  function schedule() {
    if (timer) return;
    timer = setTimeout(() => {
      timer = null;
      flush();
    }, FLUSH_MS);
  }

  function track(eventType, opts) {
    const o = opts || {};
    queue.push({
      ts: Date.now(),
      event_type: eventType,
      pattern_id: o.pattern_id || null,
      category: o.category || null,
      props: o.props || {},
    });
    if (queue.length >= MAX_BATCH) flush();
    else schedule();
  }

  function trackInteract(patternId, category, surface) {
    const key = surface + ':' + patternId;
    if (interactOnce.has(key)) return;
    interactOnce.add(key);
    track('specimen_interact', {
      pattern_id: patternId,
      category: category,
      props: { surface },
    });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
  global.addEventListener('pagehide', flush);

  global.ILTelemetry = { track, trackInteract, flush, clientId, sessionId };
})(window);

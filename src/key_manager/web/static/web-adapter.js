// Dev-Toolbox web mode bridge: emulates the pywebview JS API on top of
// fetch(), so app.js/beta3.js run unmodified in a plain browser served by
// key_manager.web.server. Injected into index.html by the server; the
// pywebview desktop app never loads this file.
(() => {
  'use strict';

  // 深淺色與 data-embedded 由 tb-theme.js 處理；這裡只補嵌入用樣式與 API 橋接
  const embedded = document.documentElement.dataset.embedded === '1';
  if (embedded) {
    // Hub already provides the window chrome; hide the tool's own topbar.
    // (External stylesheet: CSP style-src 'self' rejects inline <style>.)
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'web-embedded.css';
    document.head.appendChild(link);
  }

  async function callApi(name, args) {
    let resp;
    try {
      resp = await fetch('/api/' + encodeURIComponent(name), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Toolbox-Request': '1' },
        body: JSON.stringify({ args: args || [] })
      });
    } catch (networkError) {
      throw new Error('無法連線到本機服務：' + networkError.message);
    }
    let data = null;
    try { data = await resp.json(); } catch (_) { /* non-JSON reply */ }
    if (!resp.ok || !data) {
      const msg = (data && data.error && (data.error.message || data.error.code)) || ('HTTP ' + resp.status);
      throw new Error(msg);
    }
    return data;
  }

  function showServerStatus() {
    const status = document.querySelector('#server-status');
    const port = document.querySelector('#server-port');
    const badge = document.querySelector('#server-state');
    status.hidden = false;

    async function poll() {
      let connected = false;
      try {
        const response = await fetch('/api/health', {cache: 'no-store', signal: AbortSignal.timeout(3000)});
        if (response.ok) {
          const health = await response.json();
          connected = health.ok === true && Number.isInteger(health.port);
          if (connected) port.textContent = '本機服務 port ' + health.port;
        }
      } catch (_) { /* Retry after a connection error or timeout. */ }
      const label = connected ? '連線正常' : '伺服器未回應';
      if (badge.textContent !== label) badge.textContent = label;
      badge.classList.toggle('tb-badge--ok', connected);
      badge.classList.toggle('tb-badge--danger', !connected);
      window.setTimeout(poll, 3000);
    }

    poll();
  }

  // 告訴 app.js/beta3.js：沒有桌面視窗，資料夾/存檔對話框要改用瀏覽器版本
  window.KM_WEB_MODE = true;

  window.pywebview = {
    api: new Proxy({}, {
      get: (_target, name) => {
        if (typeof name !== 'string') return undefined;
        return (...args) => callApi(name, args);
      }
    })
  };

  // app.js/beta3.js register their pywebviewready listeners during script evaluation.
  document.addEventListener('DOMContentLoaded', () => {
    if (!embedded) showServerStatus();
    window.setTimeout(() => {
      window.dispatchEvent(new Event('pywebviewready'));
    }, 0);
  });
})();

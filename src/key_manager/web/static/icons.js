/*
 * Vendored SVG bodies from Iconify's Tabler collection.
 * Source: @iconify-json/tabler@1.2.10
 * Icons remain real browser-rendered SVG; no Qt rasterization step exists.
 */
(() => {
  const ICONIFY_SOURCE = '@iconify-json/tabler@1.2.10';
  const bodies = {
    'tabler:layout-dashboard': '<path d="M5 4h4a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1m0 12h4a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1m10-4h4a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1m0-8h4a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1"/>',
    'tabler:key': '<path d="m16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1-4.069 0l-.301-.301l-6.558 6.558a2 2 0 0 1-1.239.578L5.172 21H4a1 1 0 0 1-.993-.883L3 20v-1.172a2 2 0 0 1 .467-1.284l.119-.13L4 17h2v-2h2v-2l2.144-2.144l-.301-.301a2.877 2.877 0 0 1 0-4.069l2.643-2.643a2.877 2.877 0 0 1 4.069 0M15 9h.01"/>',
    'tabler:shield-lock': '<path d="M12 3a12 12 0 0 0 8.5 3A12 12 0 0 1 12 21A12 12 0 0 1 3.5 6A12 12 0 0 0 12 3"/><path d="M11 11a1 1 0 1 0 2 0a1 1 0 1 0-2 0m1 1v2.5"/>',
    'tabler:brand-git': '<path d="M15 12a1 1 0 1 0 2 0a1 1 0 1 0-2 0m-4-4a1 1 0 1 0 2 0a1 1 0 1 0-2 0m0 8a1 1 0 1 0 2 0a1 1 0 1 0-2 0m1-1V9m3 2l-2-2m-2-2L9.1 5.1"/><path d="m13.446 2.6l7.955 7.954a2.045 2.045 0 0 1 0 2.892l-7.955 7.955a2.045 2.045 0 0 1-2.892 0l-7.955-7.955a2.045 2.045 0 0 1 0-2.892l7.955-7.955a2.045 2.045 0 0 1 2.892 0z"/>',
    'tabler:refresh': '<path d="M20 11A8.1 8.1 0 0 0 4.5 9M4 5v4h4m-4 4a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"/>',
    'tabler:moon': '<path d="M12 3h.393a7.5 7.5 0 0 0 7.92 12.446A9 9 0 1 1 12 2.992z"/>',
    'tabler:sun': '<path d="M8 12a4 4 0 1 0 8 0a4 4 0 1 0-8 0m-5 0h1m8-9v1m8 8h1m-9 8v1M5.6 5.6l.7.7m12.1-.7l-.7.7m0 11.4l.7.7m-12.1-.7l-.7.7"/>',
    'tabler:plus': '<path d="M12 5v14M5 12h14"/>',
    'tabler:copy': '<path d="M7 9.667A2.667 2.667 0 0 1 9.667 7h8.666A2.667 2.667 0 0 1 21 9.667v8.666A2.667 2.667 0 0 1 18.333 21H9.667A2.667 2.667 0 0 1 7 18.333z"/><path d="M4.012 16.737A2 2 0 0 1 3 15V5c0-1.1.9-2 2-2h10c.75 0 1.158.385 1.5 1"/>',
    'tabler:download': '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M7 11l5 5l5-5m-5-7v12"/>',
    'tabler:trash': '<path d="M4 7h16m-10 4v6m4-6v6M5 7l1 14h12l1-14M9 7V4h6v3"/>',
    'tabler:folder-open': '<path d="m5 19l2.757-7.351A1 1 0 0 1 8.693 11H21a1 1 0 0 1 .986 1.164l-.996 5.211A2 2 0 0 1 19.026 19H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h4l3 3h7a2 2 0 0 1 2 2v2"/>',
    'tabler:device-floppy': '<path d="M6 4h10l4 4v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2"/><path d="M10 14a2 2 0 1 0 4 0a2 2 0 1 0-4 0m4-10v4H8V4"/>',
    'tabler:signature': '<path d="M3 17q5-5 5-8c0-3-1-3-2-3S3.968 7.085 4 9c.034 2.048 1.658 4.877 2.5 6C8 17 9 17.5 10 16l2-3q.5 4 3 4c.53 0 2.639-2 3-2q.776 0 3 2"/>',
    'tabler:x': '<path d="M18 6L6 18M6 6l12 12"/>',
    'tabler:info-circle': '<path d="M12 9h.01M11 12h1v4h1"/><circle cx="12" cy="12" r="9"/>',
    'tabler:terminal-2': '<path d="m8 9l3 3l-3 3m5 0h3"/><path d="M3 4h18v16H3z"/>',
    'tabler:check': '<path d="m5 12l5 5L20 7"/>',
    'tabler:alert-circle': '<path d="M12 8v4m0 4h.01"/><circle cx="12" cy="12" r="9"/>',
    'tabler:user': '<path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0-8 0m-2 14v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>'
  };

  function svgFor(name) {
    const body = bodies[name] || bodies['tabler:alert-circle'];
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
  }

  function renderIcons(root = document) {
    root.querySelectorAll('[data-icon]').forEach(node => {
      const name = node.getAttribute('data-icon');
      if (node.dataset.renderedIcon !== name) {
        node.innerHTML = svgFor(name);
        node.dataset.renderedIcon = name;
      }
    });
  }

  window.IconifyLocal = { source: ICONIFY_SOURCE, svgFor, renderIcons };
  renderIcons();
})();

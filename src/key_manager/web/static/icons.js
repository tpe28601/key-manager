/*
 * 圖標：沿用 data-icon="tabler:*" 的名稱，實際畫的是 ui-kit 的 Lucide 圖標（tb-icons.js，ISC 授權），
 * 讓 Key Manager 與 Hub、其他工具用同一套圖標。必須在 tb-icons.js 之後載入。
 * API 與舊版相同：IconifyLocal.svgFor(name)、IconifyLocal.renderIcons(root)。
 */
(() => {
  const MAP = {
    'tabler:layout-dashboard': 'layout-dashboard',
    'tabler:key': 'key',
    'tabler:shield-lock': 'shield',
    'tabler:brand-git': 'git-branch',
    'tabler:refresh': 'refresh-cw',
    'tabler:moon': 'moon',
    'tabler:sun': 'sun',
    'tabler:device-desktop': 'monitor',
    'tabler:plus': 'plus',
    'tabler:copy': 'copy',
    'tabler:download': 'download',
    'tabler:trash': 'trash-2',
    'tabler:folder-open': 'folder-open',
    'tabler:device-floppy': 'save',
    'tabler:signature': 'signature',
    'tabler:x': 'x',
    'tabler:info-circle': 'info',
    'tabler:terminal-2': 'terminal',
    'tabler:check': 'circle-check',
    'tabler:alert-circle': 'triangle-alert',
    'tabler:user': 'user',
    'tabler:arrow-up': 'chevron-up',
    'tabler:folder': 'folder',
    'tabler:hard-drive': 'hard-drive'
  };

  function svgFor(name) {
    const lucide = MAP[name] || String(name || '').replace(/^tabler:/, '');
    if (window.TbIcons) return window.TbIcons.svg(lucide);
    return '';
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

  window.IconifyLocal = { source: 'lucide (ui-kit tb-icons.js)', svgFor, renderIcons };
  renderIcons();
})();

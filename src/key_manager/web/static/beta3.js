(() => {
  'use strict';

  const $ = selector => document.querySelector(selector);

  function icon(name) {
    const span = document.createElement('span');
    span.className = 'icon';
    span.dataset.icon = name;
    if (window.IconifyLocal) {
      span.innerHTML = window.IconifyLocal.svgFor(name);
      span.dataset.renderedIcon = name;
    }
    return span;
  }

  function button(id, label, iconName, extraClass = '') {
    const el = document.createElement('button');
    el.id = id;
    el.type = 'button';
    el.className = `button ${extraClass}`.trim();
    el.append(icon(iconName), document.createTextNode(label));
    return el;
  }

  function installSshPathControls() {
    const page = $('#page-ssh');
    const table = page?.querySelector('.table-wrap');
    if (!page || !table || $('#ssh-local-path')) return;

    const panel = document.createElement('div');
    panel.className = 'path-setting';

    const label = document.createElement('div');
    label.className = 'path-setting-label';
    label.append(icon('tabler:folder-open'));
    const copy = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = '本機 Key 路徑';
    const hint = document.createElement('span');
    hint.textContent = 'SSH 掃描、建立、刪除與 Agent 都使用此資料夾';
    copy.append(title, hint);
    label.append(copy);

    const controls = document.createElement('div');
    controls.className = 'path-setting-controls';
    const input = document.createElement('input');
    input.id = 'ssh-local-path';
    input.readOnly = true;
    input.setAttribute('aria-label', 'SSH Local Key 路徑');
    controls.append(
      input,
      button('ssh-path-browse', '選擇資料夾', 'tabler:folder-open'),
      button('ssh-path-reset', '恢復預設', 'tabler:refresh', 'ghost'),
    );

    panel.append(label, controls);
    table.before(panel);

    $('#ssh-path-browse').addEventListener('click', selectDirectory);
    $('#ssh-path-reset').addEventListener('click', resetDirectory);
  }

  function bridge() {
    return window.pywebview?.api || null;
  }

  function notify(message, type = 'success') {
    const stack = $('#toasts');
    if (!stack) return;
    // Keep in sync with app.js's toastHost(): a showModal() dialog paints in
    // the top layer above normal elements, so the toast stack must live
    // inside it (if one is open) or it will render hidden behind the backdrop.
    const dialogs = [...document.querySelectorAll('dialog[open]')];
    const host = dialogs.length ? dialogs[dialogs.length - 1] : document.body;
    if (stack.parentElement !== host) host.append(stack);
    const item = document.createElement('div');
    item.className = `toast ${type}`;
    item.append(icon(type === 'error' ? 'tabler:alert-circle' : 'tabler:check'));
    const text = document.createElement('div');
    text.textContent = message;
    item.append(text);
    stack.append(item);
    window.setTimeout(() => item.remove(), type === 'error' ? 5200 : 3300);
  }

  async function refreshPath() {
    installSshPathControls();
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'C:\\Users\\Mike\\.ssh';
      return;
    }
    try {
      const result = await api.get_ssh_directory();
      if (result?.ok) $('#ssh-local-path').value = result.ssh_dir || '';
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  async function selectDirectory() {
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'D:\\Keys\\SSH';
      return;
    }
    if (window.KM_WEB_MODE) return openDirBrowser(api);
    try {
      const result = await api.select_ssh_directory();
      if (!result?.ok) return notify(result?.error || '選擇資料夾失敗', 'error');
      if (result.cancelled) return;
      $('#ssh-local-path').value = result.ssh_dir || '';
      notify('SSH Local Key 路徑已更新');
      $('#refresh-btn')?.click();
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  // ---- Web 模式：瀏覽器內的資料夾挑選（ui-kit tb-dirpicker 共用元件；桌面版用 pywebview 原生對話框） ----
  // options: { startPath, title, subtitle, onPick }。subtitle 為舊介面欄位，統一後由元件標題承載。
  const DIR_DEFAULT_TITLE = '選擇 SSH Key 資料夾';
  async function openDirBrowser(api, options = {}) {
    const fetchDir = async (path, opts) => {
      if (opts && opts.scan) {
        return api.browse_directories(path || '', true, opts.depth || 2, opts.limit || 50);
      }
      return api.browse_directories(path || '');
    };
    let picked;
    try {
      picked = await TbDirPicker.open({
        title: options.title || DIR_DEFAULT_TITLE,
        start: options.startPath || $('#ssh-local-path')?.value || '',
        dirsOnly: true,
        fetchDir,
      });
    } catch (error) {
      return notify(error?.message || String(error), 'error');
    }
    if (!picked) return;
    if (typeof options.onPick === 'function') {
      try { await options.onPick(picked); } catch (error) { notify(error?.message || String(error), 'error'); }
      return;
    }
    try {
      const result = await api.set_ssh_directory(picked);
      if (!result?.ok) return notify(result?.error || '設定資料夾失敗', 'error');
      $('#ssh-local-path').value = result.ssh_dir || '';
      notify('SSH Local Key 路徑已更新');
      $('#refresh-btn')?.click();
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  async function resetDirectory() {
    const api = bridge();
    if (!api) {
      $('#ssh-local-path').value = 'C:\\Users\\Mike\\.ssh';
      return;
    }
    try {
      const result = await api.reset_ssh_directory();
      if (!result?.ok) return notify(result?.error || '恢復預設失敗', 'error');
      $('#ssh-local-path').value = result.ssh_dir || '';
      notify('已恢復預設 SSH Key 路徑');
      $('#refresh-btn')?.click();
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  // 主題由 tb-theme.js 套用；按鈕外觀由 app.js 的 tb-theme-change 監聽更新
  const THEME_MODES = ['light', 'dark', 'system'];
  function applyTheme(theme) {
    if (!THEME_MODES.includes(theme)) return;
    if (window.TbTheme) window.TbTheme.set(theme);
    else document.documentElement.dataset.theme = theme === 'dark' ? 'dark' : 'light';
  }
  function currentMode() {
    return window.TbTheme ? window.TbTheme.get().mode : (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
  }

  async function restoreTheme() {
    const api = bridge();
    if (!api?.get_theme) return;
    try {
      const result = await api.get_theme();
      if (result?.ok) {
        // settings.json 是主題的正本；Hub 嵌入時網址指定的主題優先，不覆蓋
        if (!new URLSearchParams(location.search).get('theme')) applyTheme(result.theme);
      }
    } catch (_) {}
  }

  async function persistCurrentTheme() {
    const api = bridge();
    if (!api?.set_theme) return;
    const value = currentMode();
    try {
      const result = await api.set_theme(value);
      if (!result?.ok) notify(result?.error || '主題設定儲存失敗', 'error');
    } catch (error) {
      notify(error?.message || String(error), 'error');
    }
  }

  window.KmDirBrowser = { open: openDirBrowser };

  document.addEventListener('DOMContentLoaded', () => {
    installSshPathControls();
    $('#theme-btn')?.addEventListener('click', () => window.setTimeout(persistCurrentTheme, 0));
    window.setTimeout(refreshPath, 420);
  });
  window.addEventListener('pywebviewready', () => {
    void refreshPath();
    void restoreTheme();
  });
})();

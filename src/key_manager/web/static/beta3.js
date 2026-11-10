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

  // ---- Web 模式：瀏覽器內的資料夾選擇器（桌面版用 pywebview 原生對話框） ----
  let dirApi = null;
  let dirCurrent = '';

  function iconSpan(name) {
    const span = document.createElement('span');
    span.className = 'icon';
    span.setAttribute('data-icon', name);
    return span;
  }

  async function loadDir(path) {
    const result = await dirApi.browse_directories(path || '');
    if (!result?.ok) {
      notify(result?.error || '讀取資料夾失敗', 'error');
      return;
    }
    dirCurrent = result.path || '';
    $('#dir-path').value = dirCurrent;
    $('#dir-up').disabled = !result.parent && !dirCurrent;
    $('#dir-up').dataset.parent = result.parent || '';
    $('#dir-ok').disabled = !dirCurrent;

    const roots = $('#dir-roots');
    roots.replaceChildren();
    (result.roots || []).forEach(root => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip-button';
      btn.append(iconSpan('tabler:hard-drive'), document.createTextNode(root.name));
      btn.addEventListener('click', () => loadDir(root.path));
      roots.append(btn);
    });

    const list = $('#dir-list');
    list.replaceChildren();
    (result.dirs || []).forEach(dir => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'dir-item';
      btn.title = dir.path;
      btn.append(iconSpan(dirCurrent ? 'tabler:folder' : 'tabler:hard-drive'), document.createTextNode(dir.name));
      btn.addEventListener('click', () => loadDir(dir.path));
      li.append(btn);
      list.append(li);
    });
    $('#dir-empty').hidden = (result.dirs || []).length > 0;
    window.IconifyLocal?.renderIcons($('#dir-dialog'));
    list.scrollTop = 0;
  }

  async function openDirBrowser(api) {
    dirApi = api;
    const dialog = $('#dir-dialog');
    if (!dialog) return notify('找不到資料夾選擇視窗', 'error');
    if (!dialog.dataset.bound) {
      dialog.dataset.bound = '1';
      const close = () => dialog.close();
      $('#dir-cancel').addEventListener('click', close);
      $('#dir-cancel-x').addEventListener('click', close);
      $('#dir-up').addEventListener('click', () => loadDir($('#dir-up').dataset.parent || ''));
      $('#dir-go').addEventListener('click', () => loadDir($('#dir-path').value.trim()));
      $('#dir-path').addEventListener('keydown', event => {
        if (event.key === 'Enter') { event.preventDefault(); loadDir($('#dir-path').value.trim()); }
      });
      $('#dir-ok').addEventListener('click', async () => {
        if (!dirCurrent) return;
        try {
          const result = await dirApi.set_ssh_directory(dirCurrent);
          if (!result?.ok) return notify(result?.error || '設定資料夾失敗', 'error');
          dialog.close();
          $('#ssh-local-path').value = result.ssh_dir || '';
          notify('SSH Local Key 路徑已更新');
          $('#refresh-btn')?.click();
        } catch (error) {
          notify(error?.message || String(error), 'error');
        }
      });
    }
    dialog.showModal();
    try {
      await loadDir($('#ssh-local-path').value || '');
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
